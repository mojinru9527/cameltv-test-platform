# QA 验收报告 — Batch 11 · RAG/知识执行 M0+M1（治理基座 + 知识源入库）

- **审查角色**：QA 部门（独立验收，未参与开发）
- **审查日期**：2026-07-09
- **被审交付**：M0（治理基座）+ M1（知识源入库，无 embedding）
- **审查方式**：跑测试（真实执行）+ 逐行读源码 + 经验性绕过验证 + 端到端 HTTP 复现
- **结论**：**NEEDS WORK**（置信度 ~90%）—— 核心治理/事务/迁移机制扎实通过，但脱敏（验收标准 #7）存在可轻易绕过的真实缺口，须在放开真实/生产数据入库前修复。

---

## 1. 测试执行汇总（真实计数）

| 套件 | 命令 | 结果 | 说明 |
|------|------|------|------|
| 知识中心 | `pytest tests/test_knowledge.py -v` | **13 passed / 13**（3.02s） | Dev 声称 13/13，属实 |
| 回归子集 | `pytest tests/test_apitest_assets.py tests/test_apitest_generation.py tests/test_swagger_doc_discovery.py -q` | **53 passed / 53**（0.59s） | 无回归 |
| 基线（对照） | `pytest tests/test_auth.py -q` | **4 failed + 1 error**（PRE-EXISTING） | 见下 |
| QA 附加 E2E | 内联 TestClient 复现治理守卫 + 全局开关 + 脱敏绕过 | 见下 | 非交付测试，QA 自证 |

**基线失败已确认为 PRE-EXISTING（非本次交付引入）**：
- `tests/test_auth.py` 报 `no such table: sys_user`（in-memory SQLite 无 StaticPool 跨线程）与 `AttributeError: NoneType.status`（登录响应 shape 漂移）。
- 证据：`git status` 显示 `tests/conftest.py` 与 `tests/test_auth.py` 工作树**未修改**（仅新增未跟踪的 knowledge 文件 `??`）。知识测试文件 `test_knowledge.py:12-17` 显式注释该 conftest 破损并用自带 StaticPool 夹具规避。→ 与本交付无关。

**QA 端到端复现（自证，源码未改）**：
- 治理守卫 HTTP 层：`POST /knowledge/ai-artifacts/{id}/import-to-test-cases`，pending → **HTTP 403** `{code:403,data:null}`；approved → **HTTP 200** `{artifact_id,case_id}`。✅
- 全局开关：`knowledge_ingest_enabled=False` → `ingest_requirement_in_new_session` 直接返回 None（未开 Session）。✅
- 脱敏绕过：`sanitize()` 内联跑 15 组输入，确认多组敏感数据**未遮蔽**（见缺陷 #1）。

---

## 2. 缺陷清单

| # | 严重度 | NEW/PRE | 描述 | 证据（file:line） | 状态 |
|---|--------|---------|------|-------------------|------|
| 1 | **P2** | NEW | 脱敏正则可被轻易绕过：`?access_token=xxx` 查询串 token、非 JSON 的 `token=xxx`、无 `Bearer` 前缀的裸 JWT、行内（非行首）`Cookie: …`、带分隔符手机号 `138-1234-5678`/`138 1234 5678`、单引号 JSON `{'token':'x'}` 全部**明文入库**。违反验收标准 #7「不可被轻易绕过」。 | `app/services/knowledge/sanitize.py:17-32`（`_HEADER_RE` 用 `^` 行首锚 + MULTILINE；`_BEARER_RE` 强制 `bearer` 前缀；`_PHONE_RE` 要求 11 位连续数字；`_JSON_SECRET_RE` 仅匹配双引号）。QA 内联 `sanitize()` 运行已复现全部绕过。 | OPEN |
| 2 | **P2** | NEW | `source_ref` 与 `title` 入库前**未脱敏**（仅 `raw_content`/chunk `content` 过了 `sanitize()`）。若接口路径含 token 查询参数（如 `/login?token=secret`），会以明文落入 `source_ref` 并被 `/knowledge/sources` 列表/详情 API 原样返回。 | `ingest_service.py:44-54`（req 只 sanitize `raw`，`source_ref=doc.source_ref` 直传）、`:154-163`（`source_ref=f"{case.api_method} {case.api_endpoint}"` 未脱敏） | OPEN |
| 3 | **P3** | NEW | 配置开关 `ai_artifact_allow_batch_import` 定义后**全代码零引用**（grep 仅命中定义行），批量导入治理门未实际接线。当前仅单条导入，属占位；若后续加批量导入路径而忘接此开关，治理可被绕过。 | `app/core/config.py:102`；`grep -rn ai_artifact_allow_batch_import app/` 无其它命中 | OPEN |
| 4 | **P3** | NEW | 脱敏单测仅覆盖连续happy-path（Auth头/连续手机号/邮箱/身份证），**未覆盖任何绕过用例**，给出「遮蔽完整」的虚假信心。 | `tests/test_knowledge.py:98-110` | OPEN |
| 5 | **P3** | NEW | 编辑重入库累积僵尸 KnowledgeSource：`record_source` 去重键含 `content_hash`，实体被编辑（内容变→新 hash）时新建一条 source，**旧 source 不置 deprecated**，全部停留 `parsed`（默认视为活跃）。`test_case` PUT 每次触发（`test_case.py:127`），长期膨胀且无 supersede 逻辑。 | `source_service.py:34-62`；`api/v1/test_case.py:113-130` | OPEN |
| — | info | NEW | `_ingest_one_test_case` 未校验 `case.project_id == project_id`（用调用方传入 project_id）。低风险：project_id 与创建该行的请求同源。 | `ingest_service.py:136-171` | 观察 |
| — | info | NEW | `knowledge.py` 路由 `_audit` 后二次 `db.commit()`（如 `:167-169,:220-222`）为无害冗余。 | `api/v1/knowledge.py` | 观察 |

**无 NEW P0 / P1。** 核心机制（迁移/模型/权限/治理守卫/事务安全/去重/生产门控/全局开关/分层与 envelope）全部带证据通过。

---

## 3. 验收标准合规（逐条）

| # | 验收标准 | 结论 | 证据 |
|---|----------|------|------|
| 1 | 迁移 0013 单步 DDL，`down_revision=20260707_0012`，6 表 + content_hash 索引 | ✅ | `20260708_0013_knowledge_base.py:21`（down_revision 正确）；6× `create_table`；`content_hash` 在 source(`:36`)、chunk(`:56`) 均建索引；downgrade 逆序 drop(`:141-147`) |
| 2 | 6 模型对齐文档；JSON 存 Text；content_hash 建索引 | ✅ | `models/knowledge.py` 6 类，`raw_content/metadata_json/content/tags/*_json` 均 `Text`；`content_hash index=True`（`:29,:49`） |
| 3 | 权限幂等 seed；无 `knowledge:view` → 403；tester 只读 | ✅ | `seed.py:139-144` 6 权限 + `_get_or_create` 幂等(`:161-168`)；`_TESTER_ACTIONS` 仅含 `knowledge:view`(`:148-152`)；E2E `test_missing_permission_403` + QA 复现均 403 |
| 4 | 治理守卫：非 approved 抛 403，仅 approved 可入正式库 | ✅ | `artifact_service.py:92-93`（`!= approved` → `forbidden`）；QA E2E HTTP：pending→403 / approved→200 |
| 5 | 入库事务安全：各钩子自带 SessionLocal、try/except、BackgroundTasks 于主 commit 之后调度、绝不复用请求 db | ✅ | `ingest_service.py` 5 函数均 `SessionLocal()`+try/except+commit+close，不接收 request db；4 钩子 `add_task` 在 service/route commit 之后（`create_requirement` commit@`requirement_service.py:61`、`create_case` 内部 commit、`defect.py:95` 显式 commit）；`get_db` 不自动 commit(`core/db.py:47-53`)，FastAPI BackgroundTasks 于响应后运行→读到已提交数据 |
| 6 | 去重：(project_id,source_type,source_id,content_hash)；chunk 按 content_hash | ✅ | `source_service.py:35-45`；`chunk_service.py:59-67`；`test_record_source_dedup`/`test_make_chunks_dedup` 通过 |
| 7 | 脱敏覆盖 Auth/Bearer/Cookie/token/手机/邮箱/身份证/JSON secret，且不可轻易绕过 | ❌ **部分** | 连续 happy-path 已遮蔽（单测通过），但查询串 token、裸 JWT、行内 Cookie、带分隔符手机号、单引号 JSON 均**可绕过**（缺陷 #1）；`source_ref/title` 未脱敏（缺陷 #2）。「不可轻易绕过」不满足 |
| 8 | 生产数据门控（仅 flag=True 才入库执行结果） | ✅ | `ingest_service.py:275-279`（`env.env_type=="prod" and not settings.knowledge_ingest_production_data` → skip）；flag 默认 False 已验证 |
| 9 | 全局开关 False 短路所有入库 | ✅ | 每函数首行 `if not settings.knowledge_ingest_enabled: return`；QA 经验性验证短路 |
| 10 | Router→Service→Model 分层；R[T]/Page[T] envelope | ✅ | `knowledge.py`/`agent.py` 全路由 `require_permission` + `R.ok/Page`；`APIException` 全局处理器 `main.py:152` 保证 403 到达客户端 |

**合规率：9/10 ✅，1 ❌（部分）。**

---

## 4. 发布建议

**NEEDS WORK — 置信度 ~90%**

理由：治理闭环、事务隔离、迁移、权限、去重、生产门控、全局开关这套“骨架”实现质量高、带证据全绿；但脱敏是验收标准明确列出的安全相关能力（#7 要求“不可被轻易绕过”），实测存在多处可轻易绕过的真实缺口，且 `source_ref/title` 完全未脱敏——在放开 `knowledge_ingest_enabled` 对真实/生产数据入库前，这是必须收口的门。按团队门槛「NEW P0/P1/P2 阻断发布」，本批含 2 个 NEW P2，故判 NEEDS WORK。

### Must-fix（阻断）
1. **缺陷 #1** — 加固 `sanitize.py`：覆盖查询串/非 JSON 形式的 `token=/access_token=`、裸 JWT（`eyJ[A-Za-z0-9_-]+\.…`）、行内 Cookie（去掉 `^` 行首硬锚或补行内规则）、带分隔符手机号、单引号 JSON secret。
2. **缺陷 #2** — 对 `source_ref`、`title` 也过 `sanitize()` 后再入库。

### Nice-to-fix（不阻断）
3. **缺陷 #4** — 补脱敏绕过用例单测（防回归）。
4. **缺陷 #3** — 接线或移除 `ai_artifact_allow_batch_import`，避免未来批量导入绕过治理。
5. **缺陷 #5** — 编辑重入库时将旧 source 置 `deprecated`（supersede），避免 KB 膨胀。

### 未阻断的通过项
迁移 0013、6 模型、RBAC 权限（含 tester 只读）、治理守卫 403、入库事务隔离、去重、生产门控、全局开关、分层/envelope —— 全部通过，可保留。

---

## 5. Dev 修复回执 + 复测（2026-07-09，同会话）

Dev 部门已针对上述缺陷全部收口，复测通过：

| # | 严重度 | 修复内容 | 证据 | 状态 |
|---|--------|----------|------|------|
| 1 | P2 | 加固 `sanitize.py`：新增裸 JWT（`eyJ....`）、行内 Cookie/鉴权头（去 `^` 硬锚）、查询串/表单 `token=/access_token=`（`_KV_SECRET_RE`）、带 `-`/空格 分隔手机号、单双引号 JSON secret（`_JSON_SECRET_RE` 支持单引号 + 反引用配对）。 | `sanitize.py:23-73`；单测 `test_masks_bypass_variants` 覆盖全部 6 类绕过 | ✅ FIXED |
| 2 | P2 | 在单一收口点 `record_source` 对 `title`/`source_ref` 也 `sanitize()` 后入库（防御纵深，调用方漏脱敏也不泄露）。 | `source_service.py:57-60`；单测 `test_record_source_sanitizes_title_and_ref` | ✅ FIXED |
| 3 | P3 | 新增受治理的批量导入唯一入口 `import_artifacts_to_test_cases`，`>1` 条且 `ai_artifact_allow_batch_import=False` 时拒绝（403），开关不再是死配置。 | `artifact_service.py:129-143`；单测 `test_batch_import_blocked/allowed_when_flag` | ✅ FIXED |
| 4 | P3 | 补脱敏绕过用例 + 误伤保护单测（`test_masks_bypass_variants` / `test_sanitize_keeps_ordinary_text`）。 | `test_knowledge.py` | ✅ FIXED |
| 5 | P3 | `record_source` 内容变更时把同实体旧活跃源置 `superseded`，仅保留一条活跃源，杜绝僵尸累积。 | `source_service.py:46-56`；单测 `test_record_source_supersedes_old_version` | ✅ FIXED |

**复测执行（真实计数）**：
- `pytest tests/test_knowledge.py -v` → **19 passed / 19**（原 13 + 新增 6 回归用例，2.60s）。
- 回归 `pytest tests/test_apitest_assets.py tests/test_apitest_generation.py tests/test_swagger_doc_discovery.py -q` → **53 passed / 53**（0.53s），无回归。

**QA 复测结论**：验收标准 #7（脱敏「不可被轻易绕过」）由 ❌部分 → ✅，2 个 NEW P2 已清零，3 个 P3 一并收口。**发布建议由 NEEDS WORK → READY（待 Leader 终审）**，置信度 ~92%。仍存的 info 级观察项（路由内 `_audit` 后冗余 commit、`_ingest_one_test_case` 未强校 project_id 同源）为低风险，可留后续迭代。
