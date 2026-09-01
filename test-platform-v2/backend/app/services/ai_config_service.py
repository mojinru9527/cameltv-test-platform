"""AI 提供方配置服务（项目级）—— Batch A。

所有 AI 消费点统一经 `resolve(project_id)` 获取运行时配置；项目无配置抛
`AIProviderUnconfiguredError`（前端据此引导配置，AI 功能按项目禁用）。
"""

from __future__ import annotations

import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import APIException
from app.models.ai_provider import AiProvider
from app.services import ai_errors
from app.services.ai_errors import ai_health_registry

_DEEPSEEK_OFFICIAL_URL = "https://api.deepseek.com"


class AIProviderUnconfiguredError(APIException):
    def __init__(self, msg: str | None = None) -> None:
        super().__init__(
            code=400,
            msg=msg or "当前项目未配置 AI 提供方，请在「AI 配置」中添加提供方后重试",
            http_status=400,
        )


class EffectiveAiConfig:
    """一次 resolve 的结果：解密后的运行时 AI 配置。"""

    def __init__(self, row: AiProvider) -> None:
        self.provider_id = row.id
        self.provider_name = row.name
        self.provider_type = row.provider_type
        self.api_base_url = (row.api_base_url or _DEEPSEEK_OFFICIAL_URL).rstrip("/")
        self.api_key = _decrypt_key(row.api_key_encrypted)
        self.model = row.default_model or _first_model(row.models)


def mask_api_key(key: str) -> str:
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:2]}****{key[-4:]}"


def _first_model(models_json: str) -> str:
    try:
        models = json.loads(models_json or "[]")
        return models[0] if isinstance(models, list) and models else ""
    except (json.JSONDecodeError, IndexError, TypeError):
        return ""


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_key(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def _decrypt_key(stored: str) -> str:
    if not stored:
        return ""
    try:
        return _fernet().decrypt(stored.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # SECRET_KEY 轮换后存量密文无法解密——转业务错误引导重新录入，避免裸 500。
        raise AIProviderUnconfiguredError(
            "AI 配置密钥已失效（可能 SECRET_KEY 已轮换），请在「AI 配置」中重新输入该提供方的 API Key"
        )


class AiConfigService:
    @staticmethod
    def _encrypt_key(plain: str) -> str:
        """实例级封装（测试/调用方直接经单例加密 key）。"""
        return _encrypt_key(plain)

    # ── 读取 ──

    def resolve(self, db: Session, project_id: int) -> EffectiveAiConfig:
        """返回项目默认（或首个启用）提供方；无配置抛 AIProviderUnconfiguredError。"""
        row = db.scalar(
            select(AiProvider)
            .where(AiProvider.project_id == project_id, AiProvider.enabled.is_(True))
            .order_by(AiProvider.is_default.desc(), AiProvider.id.asc())
        )
        if row is None:
            raise AIProviderUnconfiguredError()
        return EffectiveAiConfig(row)

    def list_providers(self, db: Session, project_id: int) -> list[dict]:
        rows = db.scalars(
            select(AiProvider)
            .where(AiProvider.project_id == project_id)
            .order_by(AiProvider.id.asc())
        ).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "provider_type": r.provider_type,
                "api_base_url": r.api_base_url,
                "api_key": mask_api_key(_decrypt_key(r.api_key_encrypted)),
                "models": _models_list(r.models),
                "default_model": r.default_model,
                "is_default": r.is_default,
                "enabled": r.enabled,
            }
            for r in rows
        ]

    def resolve_out(self, db: Session, project_id: int) -> dict:
        """当前项目生效 AI 配置 + **真实健康态**。

        P0-2/P2-6：`configured` 只表示「填过提供方」，不代表 Key 可用。
        生产曾出现 Key 401 但全平台仍显示「已配置 / AI 可用」的误导状态。
        这里额外返回 `health`（来自最近一次真实调用或连通性测试）：
          - status=ok       最近一次调用成功
          - status=error    最近一次调用失败（含可执行 message 与 kind）
          - status=unknown  本进程尚未验证过（前端应显示"未验证"而非"可用"）
        """
        health = ai_health_registry.get(project_id).to_dict()
        try:
            cfg = self.resolve(db, project_id)
        except AIProviderUnconfiguredError:
            return {"configured": False, "provider": None, "health": health}
        return {
            "configured": True,
            "provider": {
                "id": cfg.provider_id,
                "name": cfg.provider_name,
                "model": cfg.model,
            },
            "health": health,
        }

    # ── 写 ──

    def create_provider(self, db: Session, project_id: int, data: dict) -> AiProvider:
        models = data.get("models") or []
        if not models:
            raise APIException(code=400, msg="至少填写一个模型", http_status=400)
        default_model = (data.get("default_model") or "").strip() or models[0]
        row = AiProvider(
            project_id=project_id,
            name=(data.get("name") or "").strip(),
            provider_type=data.get("provider_type") or "openai_compatible",
            api_base_url=(data.get("api_base_url") or "").strip(),
            api_key_encrypted=_encrypt_key(data.get("api_key") or ""),
            models=json.dumps(models, ensure_ascii=False),
            default_model=default_model,
            is_default=bool(data.get("is_default")),
            enabled=bool(data.get("enabled", True)),
        )
        db.add(row)
        db.flush()
        self._ensure_single_default(db, project_id, row.id)
        db.commit()
        db.refresh(row)
        return row

    def update_provider(
        self, db: Session, project_id: int, provider_id: int, data: dict
    ) -> AiProvider:
        row = self._get(db, project_id, provider_id)
        if "name" in data:
            row.name = (data["name"] or "").strip()
        if "provider_type" in data:
            row.provider_type = data["provider_type"]
        if "api_base_url" in data:
            row.api_base_url = (data["api_base_url"] or "").strip()
        if "api_key" in data and data["api_key"]:  # key 留空 = 不变
            row.api_key_encrypted = _encrypt_key(data["api_key"])
        if "models" in data:
            row.models = json.dumps(data["models"] or [], ensure_ascii=False)
        if "default_model" in data:
            row.default_model = (data["default_model"] or "").strip()
        if "is_default" in data and data["is_default"]:
            row.is_default = True
            self._ensure_single_default(db, project_id, row.id)
        if "enabled" in data:
            row.enabled = bool(data["enabled"])
        db.commit()
        db.refresh(row)
        return row

    def delete_provider(self, db: Session, project_id: int, provider_id: int) -> None:
        row = self._get(db, project_id, provider_id)
        if row.is_default:
            raise APIException(
                code=400, msg="默认提供方不可删除，请先转移默认", http_status=400
            )
        db.delete(row)
        db.commit()

    def _get(self, db: Session, project_id: int, provider_id: int) -> AiProvider:
        row = db.get(AiProvider, provider_id)
        if row is None or row.project_id != project_id:
            raise APIException(code=404, msg="AI 提供方不存在", http_status=404)
        return row

    def _ensure_single_default(
        self, db: Session, project_id: int, keep_id: int
    ) -> None:
        rows = db.scalars(
            select(AiProvider).where(
                AiProvider.project_id == project_id, AiProvider.is_default.is_(True)
            )
        ).all()
        for r in rows:
            if r.id != keep_id:
                r.is_default = False

    # ── 连通测试 ──

    def test_connection(self, db: Session, project_id: int, provider_id: int) -> dict:
        row = self._get(db, project_id, provider_id)
        cfg = EffectiveAiConfig(row)
        import time

        import httpx

        t0 = time.perf_counter()
        try:
            resp = httpx.post(
                f"{cfg.api_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {cfg.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": cfg.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            ai_health_registry.record_success(project_id, row.id)
            return {
                "ok": True,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "model": cfg.model,
            }
        except Exception as exc:  # noqa: BLE001 - 连通性测试需吞掉具体异常转为可读信息
            # P2-7：不再把 `HTTPStatusError: ... https://developer.mozilla.org/...`
            # 原样回给前端 toast，改为可执行的中文提示 + 可展开的原始摘要。
            health = ai_health_registry.record_failure(
                project_id, exc, row.id, cfg.provider_name
            )
            return {
                "ok": False,
                "kind": health.kind,
                "error": ai_errors.humanize_ai_error(exc, cfg.provider_name),
                "detail": ai_errors.humanize_ai_error(
                    exc, cfg.provider_name, include_detail=True
                ),
            }

    def discover_models(self, api_base_url: str = "", api_key: str = "") -> dict:
        """调用提供方公开的 GET /models 发现可用模型清单（OpenAI 兼容）。

        新增提供方时替代手填模型清单：返回 data[].id 列表；未实现 /models 的
        提供方返回可读错误，用户仍可手动填写。
        """
        import httpx

        base = (api_base_url or _DEEPSEEK_OFFICIAL_URL).strip().rstrip("/")
        if not api_key:
            return {"ok": False, "error": "请先填写 API Key 再获取模型列表"}
        try:
            resp = httpx.get(
                f"{base}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15.0,
            )
            if resp.status_code == 401:
                return {
                    "ok": False,
                    "kind": ai_errors.UNAUTHORIZED,
                    "error": ai_errors.humanize_ai_error("401 Unauthorized"),
                }
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data") if isinstance(data, dict) else None
            if not isinstance(items, list):
                return {"ok": False, "error": "提供方返回格式不含模型清单（/models），请手动填写"}
            ids = [m.get("id") for m in items if isinstance(m, dict) and m.get("id")]
            ids = [i for i in ids if i]
            # 去重并保持返回顺序（不同提供方 /models 可能重复返回同 id）。
            ids = list(dict.fromkeys(ids))
            if not ids:
                return {"ok": False, "error": "提供方 /models 未返回模型，请手动填写"}
            return {"ok": True, "models": ids, "count": len(ids)}
        except Exception as exc:  # noqa: BLE001 - 发现失败转为可读提示
            return {
                "ok": False,
                "kind": ai_errors.classify_ai_error(exc),
                "error": ai_errors.humanize_ai_error(exc),
            }


def _models_list(models_json: str) -> list[str]:
    try:
        data = json.loads(models_json or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


ai_config_service = AiConfigService()
