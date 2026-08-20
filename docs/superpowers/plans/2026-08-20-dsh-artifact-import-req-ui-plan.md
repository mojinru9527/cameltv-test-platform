# DSH 产物导入补齐（requirement/ui_case）+ Fernet 解密失败友好化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 B2 明确延后的两类 AI 产物导入——`requirement`（导入需求库 RequirementDocument）与 `ui_case`（导入 UI 用例库 TestCase case_type="ui"）；前端审核台解禁对应导入按钮。附带 Fernet 方案 A：SECRET_KEY 轮换后存量加密 key 解密失败由裸 500 转为业务错误引导重录。

**依据：** 已批准设计 `docs/superpowers/plans/2026-08-18-dsh-test-entry-and-ai-config-design.md` §5.4「approve → 按产物类型导入正式库（需求/功能用例/接口用例/UI 用例）」；v2.10.0 release notes 已知风险表「requirement/ui_case 产物暂不支持导入｜后续批次支持」。

**Architecture:** `artifact_service` 新增分发入口 `import_artifact`（按 artifact_type 路由到用例导入/需求导入），路由层与批量入口改走分发；治理守卫（仅 approved、imported 防重、项目隔离、批量门控）全部保持。

**Tech Stack:** FastAPI / SQLAlchemy 2.0 / pytest / React 19 / Vitest

---

### Task 1: 后端 artifact_service —— import_artifact 分发 + ui_case 导入

**Files:**
- Modify: `test-platform-v2/backend/app/services/knowledge/artifact_service.py`

- [ ] **Step 1: 新增分发入口 `import_artifact(db, artifact_id, project_id, operator_id=0) -> dict`**

守卫与现有 `import_to_test_case` 完全一致（存在性/项目隔离 404、imported 拒绝重复、非 approved 403），之后按 `row.artifact_type` 分发：

| artifact_type | 分发 | ref_type |
|---------------|------|----------|
| `test_case` / `api_case` | 现有逻辑（case_type="api"） | `test_case` |
| `functional_case` | 现有逻辑（case_type="manual"） | `test_case` |
| `ui_case` | 新增 UI 用例导入（case_type="ui"） | `test_case` |
| `requirement` | 新增需求文档导入（Task 2） | `requirement_document` |
| 其他 | `APIException(code=1, msg=f"artifact_type={...} 暂不支持导入")` | — |

返回统一 `{"artifact_id", "ref_type", "ref_id"}`；ref_type 为 `test_case` 时附带 `"case_id"`（旧键兼容）。

- [ ] **Step 2: ui_case 导入映射**

复用 `test_case_service.create_case(db, data)`（与现有导入一致，内部 commit）：

```python
title = (payload.get("title") or row.title).strip()
if not title.startswith("[UI]"):
    title = f"[UI] {title}"[:220]
data = {
    "project_id": project_id,
    "title": title,
    "domain": payload.get("domain") or "用户端",
    "module": payload.get("module", ""),
    "case_type": "ui",
    "priority": payload.get("priority", "P2"),
    "preconditions": payload.get("preconditions", ""),
    "steps": json.dumps(payload.get("steps", []), ensure_ascii=False),
    "expected_result": payload.get("expected_result", ""),
    "tags": json.dumps(payload.get("tags") or ["UI自动化", "auto:dsh"], ensure_ascii=False),
    "case_design_method": payload.get("case_design_method", "场景法"),
    "positive_negative": payload.get("positive_negative", ""),
    "test_data_note": payload.get("test_data_note", ""),
    "status": "draft",
    "source": "ai_generated",
}
```

- [ ] **Step 3: `import_to_test_case` 改为薄封装**

保持旧签名（仅允许三类用例类型）委托 `import_artifact`；批量 `import_artifacts_to_test_cases` 保留治理门（>1 条须 `ai_artifact_allow_batch_import=True`），逐条改走 `import_artifact` 分发（批量可混入 ui_case/requirement）。

### Task 2: 后端 artifact_service —— requirement 导入需求库

**Files:**
- Modify: `test-platform-v2/backend/app/services/knowledge/artifact_service.py`

- [ ] **Step 1: 需求导入实现（走 requirement_service.create_requirement）**

```python
from app.services import requirement_service

payload = json.loads(row.content_json or "{}")  # 非 dict/解析失败 → APIException（与用例导入同口径）
content = payload.get("content") or payload.get("markdown") or ""
if not isinstance(content, str):
    content = json.dumps(content, ensure_ascii=False, indent=2)
if not content.strip():
    content = json.dumps(payload, ensure_ascii=False, indent=2)  # 兜底：整 payload 留痕
doc = requirement_service.create_requirement(
    db,
    project_id=project_id,
    creator_id=operator_id,
    title=(payload.get("title") or row.title).strip(),
    file_type="md",
    source_ref=f"dsh_artifact:{row.id}",
    source_url=payload.get("source_url") if isinstance(payload.get("source_url"), str) else "",
    content=content,
    commit=True,  # 与用例导入同风格（内部 commit）
)
# row.review_status="imported"; row.imported_ref_type="requirement_document"; row.imported_ref_id=doc["id"]
```

先置 artifact imported（flush）→ create_requirement → 回填 ref_id（flush），与用例导入同一占位模式。

### Task 3: 路由审计消息泛化

**Files:**
- Modify: `test-platform-v2/backend/app/api/v1/knowledge_artifacts.py`

- [ ] **Step 1: 单条导入端点改走分发并传 operator_id**

`import_to_test_case(...)` → `import_artifact(db, artifact_id, current.project_id or 0, operator_id=current.user.id)`；审计消息改为 `f"artifact#{artifact_id} → {result['ref_type']}#{result['ref_id']}"`。批量端点审计消息保持 `artifacts#{n}`。

### Task 4: Fernet 方案 A —— 解密失败业务错误

**Files:**
- Modify: `test-platform-v2/backend/app/services/ai_config_service.py`
- Modify: `test-platform-v2/backend/CLAUDE.md`（AI 模型配置中心小节补轮换注意）

- [ ] **Step 1: `AIProviderUnconfiguredError` 支持自定义 msg**（`__init__(self, msg: str | None = None)`，缺省沿用现文案，向后兼容）

- [ ] **Step 2: `_decrypt_key` 捕获 `cryptography.fernet.InvalidToken` → 抛 `AIProviderUnconfiguredError("AI 配置密钥已失效（可能 SECRET_KEY 已轮换），请在「AI 配置」中重新输入该提供方的 API Key")`**

8 处消费点本已捕获 `AIProviderUnconfiguredError`，无需改动即获得友好报错。

- [ ] **Step 3: 文档**——backend/CLAUDE.md「AI 模型配置中心」小节补一条：轮换 SECRET_KEY 会使存量加密 key 失效（解密失败已转业务错误提示）；轮换后须各项目在 AI 配置页重新录入 key。

### Task 5: 后端测试 `test_artifact_import_req_ui.py`

**Files:**
- Create: `test-platform-v2/backend/tests/test_artifact_import_req_ui.py`

- [ ] **用例清单**（沿用 test_ai_artifact_batch.py 的 client/auth_headers/db_session fixture 与 `_make_artifact` 模式）：

1. ui_case approved → 导入成功：TestCase 行 `case_type="ui"`、title 带 `[UI] ` 前缀、tags 含 `UI自动化`、artifact → imported + ref_type=test_case + ref_id=case.id
2. ui_case title 已带 `[UI]` 前缀 → 不重复加前缀
3. requirement approved → 导入成功：RequirementDocument 行 title/content 落库、file_type="md"、source_ref=`dsh_artifact:{id}`、creator_id=操作人、artifact ref_type=requirement_document；content 为结构化 dict 时序列化为 JSON 文本留痕
4. requirement 未审核（pending）→ 403 守卫
5. ui_case 已导入（imported）→ 重复导入拒绝
6. 跨项目产物 → 404
7. 未知 artifact_type → 业务错误拒绝
8. 批量导入混入 ui_case+requirement（>1 条，治理开关开启）→ 全部成功且各归其库；开关关闭仍 403

### Task 6: 前端审核台解禁

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx`
- Create/Modify: `test-platform-v2/frontend/src/pages/knowledge/components/__tests__/ArtifactReviewTab.test.tsx`（若已有则改）

- [ ] **Step 1: 删除 `IMPORT_UNSUPPORTED_TYPES` 集合及全部引用**（禁用逻辑 + `title` 提示），5 类产物 approved 后导入按钮全部可用
- [ ] **Step 2: 导入成功 toast 带目标库**（按 artifact_type 映射：功能/接口/UI→用例库，requirement→需求库），如「已导入用例库」「已导入需求库」
- [ ] **Step 3: vitest 用例**：ui_case / requirement 类型行 approved 时导入按钮 enabled（点击触发 importArtifact mock）；全量 vitest 无新增失败

### Task 7: 全量自检 + 提交

- [ ] **Step 1: 后端门禁**

Run: `cd test-platform-v2/backend && <主仓 venv python> -m ruff check app/ --select F821`
Expected: 0 错误。

Run: `<主仓 venv python> -m pytest tests/test_artifact_import_req_ui.py tests/test_ai_artifact_batch.py tests/test_dsh_artifact_service.py tests/test_ai_config_service.py -v --tb=short`（worktree 目录下执行，用主仓 venv 解释器）
Expected: 全 PASS。

Run: 后端全量 `<主仓 venv python> -m pytest tests/ --tb=short -q`，记录基线（既有基线：5 个 lanhu-mcp 子模块环境失败）；确认无新增失败。

- [ ] **Step 2: 前端门禁**

Run: `cd test-platform-v2/frontend && npm ci && npx eslint src/pages/knowledge/components/ArtifactReviewTab.tsx && npm run typecheck && npm run build && npx vitest run`
Expected: eslint 0 错误（CI Lint 为 required）；typecheck/build 过；vitest 全绿（基线 501/501）。

- [ ] **Step 3: 提交**（2~3 个 commit：后端导入扩展+测试 / Fernet 友好化+文档 / 前端解禁+测试）

---

**Self-review 记录**：设计 §5.4 四类导入目标全部覆盖（functional/api 已在 B2 交付，本批补 requirement/ui_case）；治理守卫不变更（沿用 approved/imported/项目隔离/批量门控）；无占位符；返回结构向后兼容（保留 case_id 旧键）；Fernet 方案 A 不改加密协议，仅错误路径转换 + 文档。风险：DSH 产物 content 结构由 persona 契约约束、字段可能缺失——全部字段带默认值兜底（title 回退 row.title，content 空时整 payload 序列化留痕）。
