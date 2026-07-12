# Leader 终审记录 — Batch 11 · RAG/知识执行 M0+M1（治理基座 + 知识源入库）

- **审查角色**：Team Leader（终审门，独立于 Dev 与 QA，未参与编码）
- **审查日期**：2026-07-09
- **被审交付**：M0（治理基座）+ M1（知识源入库，无 embedding）+ Dev 针对 QA 5 缺陷的修复
- **审查方式**：逐行读当前源码（不信回执）+ 经验性脱敏绕过复现 + 自跑测试 + 迁移模型对齐比对 + 前端 tsc 双模式
- **最终决定**：**NO-GO（narrow / 退回 Dev）** —— 单点收口即转 GO。见 §5。置信度 ~85%。

> 一句话：治理/事务/迁移/权限/去重/前端骨架实现质量高，QA 5 缺陷全部**经我独立复现确认已修复**，19/19 + 53/53 我亲自跑绿。但我发现 QA 漏掉的一个 **NEW P2 配置默认风险**——知识入库总开关 `knowledge_ingest_enabled` 默认 **True**，合入 develop 经 Jenkins 自动部署即在共享 test 环境**默认激活**对全部写操作的后台入库，并使我新确认的脱敏残留缺口（非引号冒号密钥）**默认变为在线**。按团队门槛「NEW P2 阻断发布」，退回收口一行默认值。

---

## 1. 我亲自执行的测试（真实计数）

| 套件 | 命令 | 结果 |
|------|------|------|
| 知识中心 | `python -m pytest tests/test_knowledge.py -q` | **19 passed / 19**（2.44s，Python 3.12.10 / pytest 9.0.3） |
| 回归子集 | `python -m pytest tests/test_apitest_assets.py tests/test_apitest_generation.py tests/test_swagger_doc_discovery.py -q` | **53 passed / 53**（0.43s） |
| 前端类型（noEmit） | `npx tsc --noEmit` | **0 error**，exit 0（tsc 5.9.3） |
| 前端类型（build 模式） | `npx tsc -b --force` | **0 error**（`npm run build` 的 tsc 阶段） |

Dev/QA 声称的 19/19 与 53/53 **属实**。前端更优于 kanban 声称：kanban 记「17 处预存 tsc 错误致 `tsc -b` 全局失败」，但当前工作树 `tsc -b --force` 与 `--noEmit` 均 **0 error**（预存错误已不复现）；知识文件贡献 0 错误。

---

## 2. 修复验证（QA 每条缺陷 → 我独立核验，不信回执）

| QA# | 严重度 | 修复是否真实生效 | 我的独立证据 |
|-----|--------|------------------|--------------|
| 1 | P2 脱敏可绕过 | ✅ 已修（QA 列出的 6 类绕过全部遮蔽） | 我用 importlib 直载 `sanitize.py` 跑对抗输入：query `access_token=`→`***`、裸 JWT→`***`、行内 `Cookie:`→`***`、`138-1234-5678`/`138 1234 5678`→`138****5678`、单引号 `{'token':'x'}`→`***`、`token=`表单→`***` 全部遮蔽。`test_masks_bypass_variants` 覆盖。**但发现新残留缺口，见 §4-A。** |
| 2 | P2 title/source_ref 未脱敏 | ✅ 已修（收口点脱敏） | `source_service.py:70-71` `title=sanitize(title)[:500]` / `source_ref=sanitize(source_ref)[:500]`——在唯一写入点 `record_source` 统一过脱敏，纵深防御。`test_record_source_sanitizes_title_and_ref` 覆盖。 |
| 3 | P3 batch_import 死配置 | ✅ 已修（受治理唯一入口） | `artifact_service.py:130-140` `import_artifacts_to_test_cases`：`dict.fromkeys` 去重 id；`len(ids)>1 and not settings.ai_artifact_allow_batch_import` → `forbidden()`（403）；每条复用单条 `import_to_test_case` 守卫。`test_batch_import_blocked/allowed_when_flag`（monkeypatch 双向）覆盖。 |
| 4 | P3 缺绕过/误伤单测 | ✅ 已修 | `test_masks_bypass_variants` + `test_sanitize_keeps_ordinary_text` 均在，19 用例含之。我另跑误伤探针：`token is generated`/`assignee`/`design:`/`signature`/`config=` 普通文本**均未被误遮蔽**——无 false-positive。 |
| 5 | P3 僵尸活跃源累积 | ✅ 已修（supersede） | `source_service.py:53-64`：`source_id is not None` 时先 UPDATE 同实体 `status=="parsed"` → `superseded`，**再** `db.add` 新行——顺序正确，不会误废刚插入行；范围含 project_id+source_type+source_id，无跨项目污染；`source_id=None` 手工源跳过。`test_record_source_supersedes_old_version` 断言 `s1.status=="superseded"`。**遗留语义瑕疵见 §4-C。** |

**5/5 QA 缺陷经独立核验确认真实修复。** 修复质量高，均带专属回归单测。

---

## 3. 代码审查清单（逐项，带证据）

| 项 | 结论 | 证据 |
|----|------|------|
| Router→Service→Model 分层，Router 无业务逻辑 | ✅ PASS | `knowledge.py`/`agent.py` 全端点仅 `require_permission` 校验 + 调 service + 返回 `R.ok`/`Page`；概览计数走 service 层模型查询，路由无业务分支 |
| envelope 一致（R[T]/Page[T]） | ✅ PASS | 全部 `response_model=R[...]`；`forbidden()`→`api_exception_handler` 返回 `{code,msg,data}` + http_status（`exceptions.py:22-34`），治理守卫 403 真实到达客户端 |
| 入库 hook 事务安全（自带 Session + try/except + post-commit 调度 + 不复用请求 db） | ✅ PASS | `ingest_service` 5 个 `*_in_new_session` 均 `SessionLocal()`+try/except/rollback/close，不接收请求 db；4 钩子经 `background_tasks.add_task`（`requirement.py:138`、`test_case.py:107/127`、`defect.py:98/218`、`apitest.py:457/462/615/675`）——`add_task` 延迟到响应后执行；`get_db` **不自动 commit**（`db.py:47-53`），主实体由 service 内部 commit（`test_case_service.py:146/166`、`create_requirement`）或路由显式 commit（`defect.py:95/215`）；执行失败入库 `apitest.py:856` 在 `db2.commit()`（`:852`）之后、独立 session。后台任务读到的是已提交数据。 |
| 无硬编码凭据/URL；异常走 core/exceptions | ✅ PASS | 知识模块无硬编码密钥；全部业务错误经 `APIException`/`forbidden`；配置项均来自 `Settings` |
| 项目范围隔离（无跨项目泄漏） | ✅ PASS | 所有知识查询均 `.where(model.project_id == pid)`：`source_service` list/get、`chunk_service` get、`artifact_service` list/get、`agent_run_service` list/get、`knowledge.py:overview` 全部计数含 `project_id==pid`；get 类另判 `row.project_id != project_id → None` |
| 迁移 0013 模型对齐（列双向一致） | ✅ PASS | 我逐列比对 6 表：source/entity 含 `created_at+updated_at`（TimestampMixin），chunk/relation/ai_artifact/agent_run 仅 `created_at`（+agent_run `finished_at`）——迁移与模型**完全一致**，无漂移；`content_hash` 在 source(`:36`)/chunk(`:56`) 建索引 |
| down_revision 正确 + 单一 head | ✅ PASS | `0013.down_revision="20260707_0012"`（真实存在，其 down 指向 0011）；全 versions 目录仅 0013 引用 0012，无第二分支，无迁移 revise 0013 → 线性单 head；downgrade 逆 FK 序 drop |
| 权限幂等 seed + tester 只读 | ✅ PASS | `seed.py:139-144` 新增 6 权限点经 `_get_or_create`（先 select 后 create）幂等；admin 走 `*` 通配；`_TESTER_ACTIONS` 知识域仅 `knowledge:view`（`:151`），不含 manage/approve/agent:run/import → tester 只读；`menu:knowledge`（`:32`）+ 前端 `BrainCircuitOutlined→Sparkles`（MainLayout:90） |
| 前端接线完整、类型干净 | ✅ PASS | `router/index.tsx:28,73` lazy 注册 `/knowledge`；`pages/knowledge` index+3 Tab（Overview/SourceList/ArtifactReview）只读；`api/knowledge.ts` 5 函数；`types/index.ts:712-785` 6 接口与后端 schema 字段一致；tsc 0 error |
| 无越界（M2/M3/M4 未提前实现） | ✅ PASS | entity/relation 仅建表未接线（符合 plan「6 表建成只接线 4 张」）；`/search`、图谱、Agent 编排、审核台写操作均标注 M2/M3/M4 未做——无 scope creep |
| 安全配置默认（safe-by-default） | ❌ **FAIL** | **`config.py:99` `knowledge_ingest_enabled: bool = True`** —— 见 §4-B（本批唯一阻断项） |

**清单：10 PASS / 1 FAIL。**

---

## 4. 我发现的 NEW 问题（QA 遗漏）

### A. NEW P3 —— 脱敏残留缺口：非引号冒号形式的密钥/PII 明文入库
- **证据（我实测，非推理）**：直载 `sanitize.py` 跑对抗输入，以下**明文穿透**：
  - `password: hunter2plain` → 原样输出（未遮蔽）
  - `token: abcplainvalue` → 原样输出
  - `{"api_key": 998877}`（冒号 + 无引号数值） → 原样输出
  - `138.1234.5678`（点分隔手机号） → 原样输出
- **根因**：`_JSON_SECRET_RE`（`sanitize.py:38-40`）要求值以引号开头 `([\"'])…`；`_KV_SECRET_RE`（`:43-45`）要求分隔符是 `=` 而非 `:`。于是 `key: <无引号值>`（YAML/日志/伪 JSON 常见形态）落入两条规则的夹缝。
- **正/负面确认**：QA 的 6 类绕过确已全部堵死；无 false-positive（普通含 token/assignee/design/signature 文本不被误遮蔽）；新正则无 ReDoS（`(?:\\.|(?!\2).)*` 交替无歧义，其余为锚定线性）。
- **单独严重度低**（尽力而为的纵深防御；这些密钥本就在同权限用户可读的源数据里；无外部出网），**但被 §4-B 的默认开关抬升为在线风险**。
- **修法**：给 `_KV_SECRET_RE` 增补 `[:=]` 且允许无引号值到分隔符；或补一条冒号-无引号规则；点分隔手机号顺带覆盖。

### B. NEW P2（本批阻断项）—— 入库总开关 `knowledge_ingest_enabled` 默认 True
- **证据**：`config.py:99` `knowledge_ingest_enabled: bool = True`，而其余 4 个治理开关 `rag_enabled` / `knowledge_graph_enabled` / `ai_artifact_allow_batch_import` / `knowledge_ingest_production_data` **全部默认 False**（`:100-103`）。
- **为何是阻断**：
  1. 一个全新、地基级、尚未生产硬化的子系统的**总入库开关默认开启**，与 M0 治理切片「谨慎门控、operator 显式开启」的立意相悖；4/5 兄弟开关皆 False，强烈提示这一条是**遗漏而非决策**。
  2. 合入 `develop` → 按 CLAUDE.md「test 环境 Jenkins 自动部署」→ **即在共享 test 环境对 requirement/接口导入/接口用例/缺陷 每次写操作激活后台入库**，无需任何人为开启。
  3. 与 §4-A 叠加：脱敏残留缺口从「休眠」变为「默认在线」——真实 test 环境数据以不完全遮蔽默认落库。
  4. 团队既定门槛（QA 报告 §4 引「NEW P0/P1/P2 阻断发布」）：本条为 NEW P2 → 规则即判阻断。
- **不放大**：所有知识 API 均 project 范围 + 权限门控，不向未授权方暴露、无外部出网、prod 执行结果另有 `knowledge_ingest_production_data=False` 单独门控——故非数据外泄级 P0/P1，定 P2。
- **修法（二选一，均为小改，零测试影响）**：
  - 首选：`knowledge_ingest_enabled` 默认改 **False**（safe-by-default，各环境 `.env` 显式开启）。**已确认不破坏测试**：`test_knowledge.py` 的入库用例直接调 `_ingest_one_test_case`/`record_source`（`:178,:195`）绕过该开关，改默认不影响 19/19。
  - 或：产品负责人**显式签字**确认「非 prod 默认入库」为有意决策；若保留 ON，则 §4-A 脱敏缺口须先收口再合入（因已在线）。

### C. NEW P3 —— supersede 语义瑕疵（不阻断）
- `record_source` 把旧版本置 `status="superseded"`，但该值**不在模型文档枚举**内（`models/knowledge.py:32` 注释列 pending/parsed/indexed/failed/deprecated，无 superseded）。
- 连带：概览 `source_count` 统计 `status != "deprecated"`（`knowledge.py:58`），**superseded 行仍被计为「活跃」**——QA #5 想压制的僵尸计数在头部指标里仍在；且被取代源的 chunk **未级联**（仅 `deprecate_source` 动 chunk），M2 检索时仍可命中。
- 均不破坏 M0/M1。修法：文档补 superseded 枚举 + 决定是否从活跃计数排除并级联到 chunk。

### D. Info / 次要（与 QA 一致或补充）
- Agent 执行记录**读**端点用 `agent:run`（"运行"动作权限）而非查看类权限（`agent.py:26,42`）——tester（仅 knowledge:view）看不到；轻微 RBAC 建模瑕疵。
- 知识路由 `_audit` 后二次 `db.commit()`（`knowledge.py:167-169` 等）无害冗余（QA 已记）。
- `_ingest_one_test_case` 信任调用方 project_id（`ingest_service.py:136`），低风险（QA 已记）。
- **缺 ADR**：新增知识子系统 + 6 表 + 5 配置开关属架构级增量，CLAUDE.md 建议「架构级决策查/补 ADR」；本次在既有执行文档(PRD)下推进，未补 ADR，属流程性次要项，不阻断。

---

## 5. 最终决定

### NO-GO（narrow）—— 退回 Dev 收口单点，收口即转 GO

**理由**：除一处外全部通过且质量高——QA 5 缺陷经我独立复现确认真实修复，迁移模型完全对齐、单一 head，分层/envelope/事务安全/项目隔离/权限幂等/tester 只读/前端接线与类型全绿，我亲跑 19/19 + 53/53 + 前端 tsc 双模式 0 error。**唯一阻断**是 QA 漏掉的 NEW P2：`knowledge_ingest_enabled` 默认 True 会在合入即于共享 test 环境默认激活全新子系统的后台入库，并使脱敏残留缺口（§4-A）默认在线。按团队自有门槛（NEW P2 阻断）+ safe-by-default 原则，不予放行。此为**一行默认值**问题，返工成本极低、无测试影响，复审可秒过。

**放行前置（必须，二选一）**
1. `config.py:99` `knowledge_ingest_enabled` 默认改 **False**；或
2. 产品负责人显式签字「非 prod 默认入库」为有意决策 **且** 同步收口 §4-A 脱敏非引号冒号缺口。

**建议随附 P3 backlog（不阻断，可合入后跟进）**
- P3-1：脱敏补 `key: <无引号值>`（冒号形态）+ 点分隔手机号规则（§4-A）。
- P3-2：`superseded` 补入状态枚举文档；决定是否从概览活跃计数排除并级联 chunk 状态（§4-C）。
- P3-3：Agent 运行**读**端点权限从 `agent:run` 调整为查看类权限（或新增 `agent:view`），与 tester 只读体系一致（§4-D）。
- P3-4：为知识子系统补一条 ADR（6 表 + 治理开关的架构决策留痕，§4-D）。

**置信度 ~85%**：证据充分（源码逐行 + 实测 + 亲跑测试）；不确定性主要在 §4-B 的**意图**——若产品确认默认 ON 是刻意的且愿先收口脱敏，则本批等价 GO-WITH-FOLLOWUP。已把该判断权明确交回产品/Dev，条件清晰。

---

## 6. 附：验证方法留痕
- 脱敏对抗/误伤：`importlib` 直载 `app/services/knowledge/sanitize.py`，21 组输入（含 QA 6 类 + 4 类新探针 + 5 类误伤），确认 6 类已堵、4 类穿透、0 误伤、无 ReDoS。
- 迁移对齐：逐列比对 `models/knowledge.py` × `alembic/versions/20260708_0013_knowledge_base.py`，6 表双向一致。
- head 唯一性：grep 全 versions 目录 down_revision，仅 0013 引用 0012。
- 事务安全：核对 4 钩子 `add_task` 位置 + `get_db` 无 autocommit + service/路由 commit 点 + `_execute_task_async` 内 `db2.commit()`→入库顺序。
- 测试：本机亲跑 knowledge 19/19、回归 53/53；前端 `tsc --noEmit` 与 `tsc -b --force` 均 0。

---

# 复审 (Round 2) — 2026-07-09

- **触发**：Dev 针对 Round-1 的 NO-GO 提交修复，Leader 独立复验（不信回执）。
- **一句话结论**：Round-1 阻断项（默认开关）+ 我提的 P3-1/P3-2 **全部经我独立复现确认真实修复**；本机亲跑 **21/21 + 53/53 绿**。复验中我**新发现一处脱敏 ReDoS（O(n²)，实测 ~7s/50KB）**，但因入库开关已默认 OFF 且入库在后台线程执行，该风险**当前休眠、合入不自动激活**。故由 NO-GO → **GO-WITH-FOLLOWUP**，置信度 ~85%。

## R2-1 修复复验（每项独立核验，不信回执）

| 项 | 是否真实修复 | 我的独立证据 |
|----|--------------|--------------|
| **BLOCKER：`knowledge_ingest_enabled` 默认 True→False** | ✅ 已修 | `config.py:101` `knowledge_ingest_enabled: bool = False`，并补注释说明「安全默认全 OFF，运维评审后显式开启」；5 个治理开关（ingest/rag/graph/batch_import/prod_data）现**全部默认 False**（`:101-105`）。合入 develop 不再自动激活入库。**已确认不破坏测试**（入库用例直调内层函数绕开关，21/21 仍绿）。 |
| **P3-1：脱敏非引号冒号残留缺口** | ✅ 已修 | 新增 `_JSON_SECRET_UNQUOTED_RE`（`sanitize.py:45-47`，引号 key + 无引号值）、`_KV_COLON_SECRET_RE`（`:53-55`，日志/YAML `token: xxx`）、手机号分隔符补 `.`（`:58`）。我直载实测：`password: hunter2`→`***`、`token: abcplainvalue`→`***`、`{"api_key":998877}`→`***`、`{"token":true}`→`***`、`138.1234.5678`→遮蔽、`password:secret123`→`***` **全部堵死**；R1 老向量仍遮蔽。 |
| P3-1 误伤保护 | ✅ 达标 | 无引号规则用有界 `_SECRET_VALUE = [A-Za-z0-9][A-Za-z0-9._\-+/=]{1,}`（ASCII 起头），实测中文值 `token: 表示令牌` / `password: 密码是明文` **不遮蔽**；`design:`（非 key）、`{"assignee":"..."}`、`The user token is generated`、`updated: 2026-...T..:..` 时间戳 **均不误遮蔽**。仅 `session: the ...` 这类「密钥词+英文单词」会遮蔽首词（符合「宁可多遮蔽」设计取舍，可接受）。 |
| **P3-2：superseded 计数/级联** | ✅ 已修 | `source_service.py:67-77`：supersede 时先把旧源 active 切片 UPDATE 为 `superseded`，再把旧源置 `superseded`，顺序在新行 `db.add` 之前——不误伤新行；`knowledge.py:58` 概览 `source_count` 改为 `status.notin_(("deprecated","superseded"))`，`chunk_count` 仍 `status=="active"`（superseded 切片自动排除）。头部指标不再被僵尸源/切片撑大。 |

**新增回归单测存在并通过**：`test_masks_unquoted_and_colon_secrets`、`test_supersede_cascades_chunks`、`test_sanitize_keeps_ordinary_text`（含误伤断言）——本机 `pytest tests/test_knowledge.py -q` → **21 passed / 21**（2.41s，原 19 + 新 2）。

## R2-2 我亲自复跑的测试

| 套件 | 结果 |
|------|------|
| `pytest tests/test_knowledge.py -q` | **21 passed / 21** |
| 回归 `test_apitest_assets + generation + swagger_doc_discovery` | **53 passed / 53** |

与 Dev 声称一致。

## R2-3 复验中新发现（NEW，我 Round-1 与 QA 均漏）

### ⚠ NEW P2 —— 脱敏 `_EMAIL_RE` / `_PHONE_RE` 存在 O(n²) ReDoS
- **证据（实测，逐正则隔离）**：对 `'{"token":"' + 'a'*50000`（50KB）跑全 `sanitize()` 三次均 ~6.9s；隔离到单条正则，**`_EMAIL_RE` = 6908ms、`_PHONE_RE`（对 `'1'+'3'*50000`）= 6800ms**，其余全 <35ms。缩放曲线呈二次（超线性）。
- **根因**：`_EMAIL_RE`（`sanitize.py:61`）`([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*(@...)`——在每个起始位贪婪吞掉整段字母数字再找尾部 `@`，失败即全回溯，O(起始位 n × 回溯 n)=O(n²)。`_PHONE_RE` 对长数字串同理。任何**普通大 blob**（base64 图片、minified JSON、长 token、大表格）即可触发，无需恶意构造。
- **归属**：**非本次 Round-2 diff 引入**——Round-2 新增的两条无引号规则实测 0–1ms（用有界线性 `_SECRET_VALUE`）；`_EMAIL_RE`/`_PHONE_RE` 是本 batch 新文件里 R1 起就在的老写法。
- **为何不阻断合入**：入库开关现默认 **OFF**（合入不激活），且 `sanitize` 在 **后台 BackgroundTasks** 中运行（不阻塞请求线程，无用户面 DoS），且为自有数据。风险**休眠**。
- **为何仍须 must-fix（放开开关前）**：`ingest_service` 现为 `_truncate(sanitize(doc.content))`——**先脱敏后截断**，即对全量未截断内容脱敏；一份数百 KB 的真实需求文档在开启入库后会让后台线程空转数十秒，多并发可打满 CPU。
- **修法**：给 `_EMAIL_RE` 本地部量词设上界（如 `{0,64}`）、`_PHONE_RE` 收紧；并把顺序改为 `sanitize(_truncate(...))` 或脱敏前先硬截断。

## R2-4 最终决定

### GO-WITH-FOLLOWUP（合入 develop，登记 backlog）—— 置信度 ~85%

**理由**：Round-1 唯一阻断项（默认开关 ON）已按 safe-by-default 收口，5 开关全 OFF；我提的 P3-1/P3-2 均经独立实测确认真实修复且无误伤；21/21 + 53/53 本机复跑绿。复验新发现的 `_EMAIL_RE/_PHONE_RE` ReDoS 虽为真实 O(n²)，但因入库默认 OFF + 后台执行，**合入不使其在线**——与我 Round-1 的对称判断一致（默认 OFF ⇒ 风险不随合入激活 ⇒ 不阻断合入，转硬性 backlog 门）。故放行合入，同时把 ReDoS 定为「放开入库开关前必须收口」的 must-fix。

**Backlog（合入后跟进）**
- **P2-NEW（放开 `knowledge_ingest_enabled` 前必须收口）**：`_EMAIL_RE`/`_PHONE_RE` 加量词上界 + 入库改「先截断后脱敏」，消除 O(n²)。〔R2 新发现〕
- **P3-3（仍成立）**：Agent 执行记录**读**端点 `agent.py:26,42` 用 `agent:run` 而非查看类权限，与 tester 只读体系不一致——改为查看类或新增 `agent:view`。
- **P3-4（仍成立）**：为知识子系统（6 表 + 5 治理开关）补一条 ADR，留架构决策痕迹。
- 〔已消项〕P3-1 脱敏残留缺口、P3-2 superseded 计数/级联 —— 本轮已收口，移出 backlog。

**置信度 ~85%**：证据为源码逐行 + 逐正则隔离实测 + 本机亲跑测试，扎实；余量主要在 ReDoS 的运营影响估计（取决于未来开启入库时的文档体量与并发），已用「开关前 must-fix」硬门兜住。

---

# Round 3 — Dev 收口 ReDoS + P3-4（2026-07-09，同会话）

Leader Round-2 判 GO-WITH-FOLLOWUP（合入已授权）。Dev 选择**不带病合入**，把 R2 唯一的 P2-NEW（ReDoS）与两条 P3 中的 ADR 一并在合入前收口，使本批达成「零 P2 未决」的干净 GO。

## R3-1 ReDoS（R2 P2-NEW）→ ✅ 已收口
- **修法（双管齐下，与 Leader §R2-3 建议一致）**：
  1. `sanitize.py:_EMAIL_RE` 加量词上界 —— 本地部 `{0,63}`、域名改无重叠有界标签 `(?:[A-Za-z0-9-]{1,63}\.){1,8}[A-Za-z]{2,24}`，把每起始位的回溯从 O(n) 降为常数 → 整体 O(n)。
  2. `ingest_service` 全部 5 处入库改 `sanitize(_truncate(...))`（**先截断后脱敏**），脱敏输入恒 ≤ `_MAX_RAW`(20KB)，纵深兜底。
- **实测**：50KB 无 `@` 字母数字 blob 全 `sanitize()` 由 **~6900ms → 31.4ms**（约 220×，线性）；邮箱遮蔽 `z@camel.to → z***@camel.to` 仍正常。
- **回归单测**：新增 `test_sanitize_no_redos_on_large_blob`（50KB blob 断言 <1.0s 且正常返回）。
- **`_PHONE_RE`**：经复核为定长有界匹配（`1[3-9]\d` + 定量 `\d{4}`），本身 O(n)；「先截断后脱敏」已额外封顶其输入规模，无需再改。

## R3-2 ADR（R2 P3-4）→ ✅ 已补
- 新增 [docs/adr/0009-knowledge-center-agent-continuous-learning.md](../../docs/adr/0009-knowledge-center-agent-continuous-learning.md)：记录「治理优先 / 分阶段 M0-M6 / 默认关闭」决策、6 表与 5 开关设计、3 条弃选方案，关联 ADR-0002/0007。

## R3-3 复跑测试（本机）
| 套件 | 结果 |
|------|------|
| `pytest tests/test_knowledge.py -q` | **22 passed / 22**（原 21 + ReDoS 回归 1） |
| 回归 `test_apitest_assets + generation + swagger_doc_discovery` | **53 passed / 53** |

## R3-4 收口后剩余 backlog（唯一项）
- **P3-3（延后至 M4）**：Agent 执行记录**读**端点用 `agent:run` 而非查看类权限。**决定延后**：M4 才真正实现 Agent 编排与审核台写操作，届时将统一设计 `agent:*` 权限族（含读/写/管理分离）与前端 Agent 工作台；现读端点为 M4 脚手架、未接前端，此刻单独改 RBAC 属超前投资。已在看板登记为 M4 前置项。
- 〔已消项〕R2 P2-NEW ReDoS、P3-4 ADR —— 本轮收口。P3-1/P3-2 R2 已消。

## R3-5 综合状态
- **零 P2 未决**；`knowledge_ingest_enabled` 可安全放开（ReDoS 与脱敏缺口均已收口）。
- Leader Round-2 的 GO（合入 develop）授权继续有效；本轮为其「放开开关前 must-fix」硬门的提前兑现，未改变合入结论，仅提升安全余量。

> Dev 判断：本批可作为**干净 GO** 合入 develop，唯一剩余 P3-3 随 M4 落地。是否即刻合入由产品/团队按 [[agent-team-gate]] 决定。
