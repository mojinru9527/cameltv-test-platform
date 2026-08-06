# Batch 108 — Design Spec（capture 去重误判修复 + 规范导入闭环）

> **Design (🎨)** | Date: 2026-08-06 | Status: Review

## 1. ingest 结果类型化（`backend/app/services/knowledge/ingest_service.py`）

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CaptureIngestResult:
    """capture 入库结果：reason ∈ created/disabled/duplicate/error。"""
    reason: str
    source_id: int | None = None
```

`ingest_capture_in_new_session(...) -> CaptureIngestResult`：

- 开关关闭 → `CaptureIngestResult("disabled")`（不再直接 return None）。
- `record_source` 返回 None（同内容已存在）→ `CaptureIngestResult("duplicate")`。
- `chunk_service.make_chunks` 前异常 → `CaptureIngestResult("error")`（记录日志）。
- 成功 commit → `CaptureIngestResult("created", src.id)`；`_post_ingest_hooks` 包 try/except
  仅记录日志，**不翻转成功结果**（修复 hooks 失败误报）。

> 兼容性：本函数仅 `knowledge.py::capture_insight` 调用；无其他调用方（rg 确认），
> 返回类型变更不破坏外部契约。

## 2. 路由错误映射（`backend/app/api/v1/knowledge.py`）

```python
result = ingest_capture_in_new_session(...)
if result.reason == "disabled":
    raise APIException(code=503, msg="知识入库未启用（KNOWLEDGE_INGEST_ENABLED=false），请联系管理员", http_status=503)
if result.reason == "duplicate":
    return R(code=409, msg="内容重复，已存在相同知识源")
if result.reason == "error":
    raise APIException(code=500, msg="知识入库失败，请查看服务日志", http_status=500)
_audit(...); db.commit()
return R.ok({"id": result.source_id, "title": body.title, "status": "captured"})
```

## 3. 配置对齐（`config/runtime/production.env`）

- 增加 `KNOWLEDGE_INGEST_ENABLED=true`（注释：M1 知识源入库总开关，与 docker-compose 默认一致）。
- Railway 部署环境变量作为人工步骤登记到交付清单与 Leader 条件（部署后复验 API）。

## 4. 单测（`backend/tests/test_knowledge_capture_outcomes.py`）

- `disabled`：monkeypatch `settings.knowledge_ingest_enabled=False` → 结果 reason="disabled"。
- `duplicate`：同标题同内容二次入库 → reason="duplicate"。
- `created`：唯一内容 → reason="created" 且 source_id 非空；sources 列表可见。
- `error`：monkeypatch `chunk_service.make_chunks` 抛异常 → reason="error"。
- hooks 容错：monkeypatch `_post_ingest_hooks` 抛异常 → 结果仍为 "created"。
- 路由：用 TestClient 断言 503/409/200 三类响应（disabled/duplicate/created）。

## 5. 导入闭环（C107-1）

1. 代码合入前本地以生产 `DATABASE_URL` + `KNOWLEDGE_INGEST_ENABLED=true` 调用
   `ingest_capture_in_new_session` 导入规范文档（Batch 102/103 已授权直连通道）。
2. 经 `GET /api/v1/knowledge/sources`（sportsadmin + X-Project-Id=1）验证文档可见。
3. 部署 + Railway env 开启后复验 API capture 路径（登记 C108 复验项）。

## 6. 环境与执行

- 无数据库 Schema 变更 → 无需 Alembic 迁移。
- 验证使用 worktree 本地 pytest + 生产库只读核查 + 直连导入。
