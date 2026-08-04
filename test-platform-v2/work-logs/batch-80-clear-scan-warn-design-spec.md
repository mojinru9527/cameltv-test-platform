# Batch 80 — Design Spec（C79-1 WARN 高价值项）

> **Design (🎨)** | Date: 2026-08-04 | Status: 就绪

## 0. 技术体系确认

后端 Python 3.12 + cryptography Fernet + logging；无 API/契约变更。

## 1. 变更设计

| 文件 | 改动 | 说明 |
|------|------|------|
| `app/core/cipher.py` | `_get_fernet()` 移除固定回退 | 用 `effective_secret_key`；缺失即 RuntimeError |
| `tests/test_cipher.py` | 新增 4 条单测 | 注入隔离 Settings，不污染全局单例 |
| `scripts/git/scan-common-bugs.ps1` | 404 规则消息 + 同行 envelope 跳过 | 双约定语义 |
| `.claude/skills/cameltv-bug-guard/SKILL.md` | 新增"404 双约定"铁律 | 判别方法 + 反例 |

## 2. cipher 密钥派生契约

```text
key = settings.effective_secret_key
未配置时: development → 自动生成会话密钥（WARNING 提示）；production → RuntimeError
派生: sha256(key) → base64url → Fernet
```

## 3. 404 双约定判别表

| 场景 | 正确契约 | 测试断言 |
|------|---------|---------|
| 隔离/权限/存在性守卫（跨项目、越权、不存在项目） | HTTP 404（不泄露存在性） | `status_code == 404` |
| 业务资源查不到（用例/环境/报告） | HTTP 200 + body `code==404` | `status_code == 200 and json()["code"] == 404` |

## 4. 测试隔离设计

```python
def _inject_settings(monkeypatch, *, environment, secret_key):
    s = Settings(_env_file=None, environment=environment, secret_key=secret_key)
    monkeypatch.setattr(cipher, "settings", s)   # 注入 cipher 模块的引用，monkeypatch 自动还原
```

禁止直接 `monkeypatch.setattr(全局 settings, ...)` —— pydantic 单例 + cached_property 会污染后续测试（本批首轮教训）。

## 5. 设计 QA 走查发现

### ⚪ P3-01 全局 settings 单例污染
首轮测试改全局单例导致 146 个 ERROR → **建议**：注入隔离实例并写入测试规范。

## 6. 设计签核

结论：通过（P3-01 已解决）。
