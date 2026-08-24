"""DSH 场景任务产物解析服务 — B2 产物闭环。

DSH 场景任务（scene=functional/api/ui/import_requirement）执行成功后，
`dsh_task_service.execute_task` 调用本服务的 `ingest_artifacts`，从任务的
output_text 中解析「## 产物清单」后的 ```json ...``` 块，按条写入
AiArtifact（review_status=pending），进入知识中心「AI 审核台」，
审核通过后再按产物类型导入正式库（见 artifact_service.import_to_test_case）。

容错约定：解析/落库全程 try/except，任何失败只返回已写入数量，
绝不抛异常——产物解析失败不改变任务状态（任务仍 success）。
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dsh_task import DshTask
from app.models.knowledge import AiArtifact

logger = logging.getLogger(__name__)

# 产物清单的 fenced code block 边界（「## 产物清单」标题后的 ```json ... ``` 块）
_MANIFEST_HEADER_RE = re.compile(r"##\s*产物清单")
_FENCE_JSON_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)

# scene → artifact_type 兜底映射（清单条目缺失 type 时用；general 不落产物）
_SCENE_TYPE_MAP = {
    "functional": "functional_case",
    "api": "api_case",
    "ui": "ui_case",
    "import_requirement": "requirement",
}

# 合法产物类型（校验清单条目 type）
_VALID_TYPES = frozenset({"functional_case", "api_case", "ui_case", "requirement"})


def parse_artifact_list(output_text: str) -> list[dict]:
    """从任务输出提取「## 产物清单」后的 ```json ... ``` 块，解析失败返回 []。

    提取策略：
    1. 定位「## 产物清单」标题行，只在其后的文本里找 json fence 块；
    2. 若无该标题，退回全文扫描 json fence 块；
    3. json 解析须为 list，逐条保留 dict 条目（跳过非 dict）。
    """
    if not output_text or not isinstance(output_text, str):
        return []
    segment = output_text
    m = _MANIFEST_HEADER_RE.search(output_text)
    if m:
        segment = output_text[m.end():]
    fm = _FENCE_JSON_RE.search(segment)
    if not fm:
        return []
    try:
        data = json.loads(fm.group(1))
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def list_task_artifacts(db: Session, task_id: int, project_id: int) -> list[AiArtifact]:
    """查询某 DSH 任务落库的产物（按 source_refs 含 dsh_task:{task_id} 过滤）。

    source_refs 为 JSON 数组字符串（如 `["dsh_task:12"]`）；用 SQLite LIKE 语义的
    `contains` 匹配精确 token（含引号），避免 `dsh_task:1` 误匹配 `dsh_task:12`。
    """
    ref_token = f'"dsh_task:{task_id}"'
    rows = db.scalars(
        select(AiArtifact)
        .where(
            AiArtifact.project_id == project_id,
            AiArtifact.source_refs.contains(ref_token),
        )
        .order_by(AiArtifact.id)
    ).all()
    return list(rows)


def _scene_from_params(task: DshTask) -> str:
    """从 task.params_json 提取 scene（缺省 general）。"""
    try:
        params = json.loads(task.params_json or "{}")
    except (json.JSONDecodeError, TypeError):
        params = {}
    if not isinstance(params, dict):
        return "general"
    return params.get("scene") or "general"


def ingest_artifacts(db: Session, task: DshTask) -> tuple[int, str | None]:
    """解析 task.output_text 的产物清单，按条写 AiArtifact（review_status=pending）。

    - artifact_type 按 task.params_json 的 scene 映射；清单条目自带 type 时以清单为准；
      缺失 type 用 scene 兜底；scene=general 或无清单 → 不写。
    - title/summary → title；content → content_json；source_refs=[f"dsh_task:{task.id}"]。
    - 幂等：同 task 已写过（source_refs contains dsh_task:{id}）则整体跳过。
    - 全程 try/except 容错：任何失败返回已写入数量，不抛异常。

    返回 (写入数, 解析失败原因或 None)。
    """
    # 幂等：同 task 已有产物（source_refs JSON 数组含 dsh_task:{id}）则跳过
    ref_token = f"dsh_task:{task.id}"
    try:
        already = db.scalar(
            select(AiArtifact).where(
                AiArtifact.project_id == task.project_id,
                AiArtifact.source_refs.contains(ref_token),
            )
        )
        if already is not None:
            return 0, None
    except Exception:  # noqa: BLE001 - 容错：查询异常不阻断任务状态
        logger.exception("dsh artifact idempotency check failed for task %s", task.id)
        return 0, None

    items = parse_artifact_list(task.output_text or "")
    scene = _scene_from_params(task)
    scene_type = _SCENE_TYPE_MAP.get(scene)
    if not items:
        if scene_type is None:
            # scene=general（或未知 scene）→ 不落产物是正常（空产物场景）
            return 0, None
        # B4：生产场景任务 0 产物——诚实上报原因，供调用方不再标 success
        return 0, (
            f"scene={scene} 场景任务未解析到产物清单（0 产物）："
            "任务输出缺少「## 产物清单」或 JSON 解析失败"
        )

    if scene_type is None:
        # scene=general（或未知 scene）→ 不落产物（保持现行为）
        return 0, None

    written = 0
    for item in items:
        try:
            artifact_type = item.get("type") or scene_type
            if artifact_type not in _VALID_TYPES:
                continue
            title = str(item.get("title") or item.get("summary") or "").strip()
            if not title:
                continue
            content = item.get("content")
            if content is None:
                content = {}
            if not isinstance(content, dict):
                # 非 dict 内容仍然原样序列化（避免丢失），但规范建议 dict
                content = {"raw": content}
            db.add(
                AiArtifact(
                    project_id=task.project_id,
                    artifact_type=artifact_type,
                    title=title,
                    content_json=json.dumps(content, ensure_ascii=False),
                    source_refs=json.dumps([ref_token], ensure_ascii=False),
                    review_status="pending",
                )
            )
            written += 1
        except Exception:  # noqa: BLE001 - 单条失败跳过，不影响其余与任务状态
            logger.warning("dsh artifact ingest item failed for task %s", task.id)
    try:
        db.commit()
    except Exception:  # noqa: BLE001 - 落库异常不抛，交由调用方决定（通常已 commit 任务状态）
        logger.exception("dsh artifact commit failed for task %s", task.id)
        db.rollback()
        return 0, None
    return written, None
