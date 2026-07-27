---
title: "Batch 48 测试平台需求服务生产级复测用例"
owner: "qa-team"
created: "2026-07-27"
status: "executed"
tags: ["batch-48", "test-platform-v2", "requirement-service", "retest", "production-readiness"]
related:
  - "BATCH47-测试平台需求服务-生产级验收.md"
  - "../../test-case-standards/生产级模块验收规则.md"
  - "../../../work-logs/batch-47-需求服务生产级验收报告-2026-07-27.md"
  - "../../../docs/superpowers/plans/2026-07-27-batch-48-acceptance-fixes.md"
---

# Batch 48 测试平台需求服务生产级复测用例

> 来源基线：Batch 47 在 `origin/main@a68e492` 执行的 48 条验收用例与 21 个缺陷。
> 目标分支：`feature/batch-48-acceptance-fixes`；实际执行前必须记录完整提交 SHA、隔离环境和数据库版本。
> 执行标准：[生产级模块验收规则](../../test-case-standards/生产级模块验收规则.md)。
> 执行状态：48 条通过、0 失败、0 阻塞；`lanhu-mcp` 提交已发布到根仓配置的可访问 fork，并通过独立克隆验证；A01～A12 全部通过，最终结论为 `READY`。

## 1. 复测范围与放行规则

Batch 48 必须完整重跑 Batch 47 的 48 条用例，不得只验证 21 个缺陷点。每个历史失败必须关联修复提交和行为级自动化；原通过项用于发现修复引入的回归；原阻塞/未执行项在条件具备后执行。

放行结论按统一规则判定：

- `READY`：P0/P1 全部通过，无致命/严重未关闭问题，无影响生产的阻塞/未执行项。
- `CONDITIONAL`：只剩有责任人、到期日和批准证据的 P2/P3 风险。
- `NEEDS WORK`：任一 P0/P1 失败，或存在跨项目泄露、部分提交/数据丢失、旧库升级失败、未接受 high/critical 漏洞、外部关键流程阻塞。

真实 AI、旧版 PostgreSQL 升级、PostgreSQL 多连接并发和真实蓝湖三条关键链路均已取得可复核执行证据。行为验收已全部解除阻塞：

| 已解除条件 | 受影响用例 | 复测结果 |
| --- | --- | --- |
| 蓝湖有界下载、附件失败转人工、截图/OCR | B47-MOD-004、B47-MOD-006、B47-MOD-010 | 三条均通过；见 `lanhu-three-regression-audit.md` |

已解除条件的真实环境证据：

- B47-REQ-013：真实 AI 完成拆分→确认→生成，得到 2 个模块、15 个功能点和 13 条功能用例；专项 27/27 通过。
- B47-NFR-005/006：从 `codex-cameltv-pg-staging-20260714-data` 的隔离克隆，将 revision `20260714_lanhu_pg_reconcile` 升级至 `20260727_batch48_pg_parity`；重复升级通过，数据计数不变，`alembic check` 零漂移。
- B47-REQ-022/B47-MOD-007：真实 PostgreSQL 多连接并发分别得到“4 路 1 导入、3 跳过”和“6 路 1×200、5×409”，最终各保留 1 条记录且计数无漂移。
- B47-MOD-004/006/010：真实蓝湖目标页有界下载、4 路模块提取幂等、附件失败转人工、截图与中文 OCR 闭环通过；证据不含 URL、Cookie 或 OCR 正文。

交付可追溯已复核：`lanhu-mcp@74bfa7b463ef505008ea25466bc950ad9ed67324` 已发布到 `mojinru9527/lanhu-mcp` 的 `feature/batch-48-bounded-download` 分支，根仓 `.gitmodules` 已指向该 fork；全新临时目录独立克隆得到相同 SHA 且工作区干净，A12 通过。

## 2. Batch 47 缺陷到 Batch 48 修复/自动化映射

> 初始实现提交：`d1f7e52be70757c14d4acc153dee17571773b931`。真实外部复测产生的兼容与 PostgreSQL 修复提交：`4dc307ed481fdb9ba01f5b8f949aeed7aef24503`。

| 历史缺陷 | 计划修复提交 | 行为级自动化/复核 |
| --- | --- | --- |
| B47-DEF-001 导入部分提交 | `fix(batch-48): make requirement review and import durable` | `test_batch48_requirement_acceptance.py`：第二条失败整批回滚；DB/计数/审计均无残留 |
| B47-DEF-002 超限上传 500 | `fix(batch-48): harden requirement document behavior` | `test_batch48_requirement_acceptance.py`：20 MB-1、20 MB、20 MB+1、空/损坏文件及无副作用 |
| B47-DEF-003 正文预览为空 | `fix(batch-48): harden requirement document behavior` + `fix(batch-48): complete requirement frontend acceptance` | `test_batch48_requirement_acceptance.py` 详情/跨项目；`RequirementPage.test.tsx` 与 Playwright 预览 |
| B47-DEF-004 审查能力缺失 | `fix(batch-48): make requirement review and import durable` + `fix(batch-48): complete requirement frontend acceptance` | `test_batch48_requirement_acceptance.py`；`ReviewPage.test.tsx`；Playwright 审查路由 |
| B47-DEF-005 编辑值丢失 | `fix(batch-48): make requirement review and import durable` + `fix(batch-48): complete requirement frontend acceptance` | `test_batch48_requirement_acceptance.py`；`AiResultModal.test.tsx`；`ReviewPage.test.tsx` |
| B47-DEF-006 重复导入/计数失真 | `fix(batch-48): make requirement review and import durable` | `test_batch48_requirement_acceptance.py`：混合索引、顺序幂等、唯一约束与计数；`test_batch48_postgresql_concurrency.py`：真实 PG 4 路并发最终仅导入 1 条 |
| B47-DEF-007 审计不落库 | `fix(batch-48): make requirement review and import durable` | `test_batch48_requirement_acceptance.py`：业务/审计同事务 |
| B47-DEF-008 跨页不可见/创建人缺失 | `fix(batch-48): harden requirement document behavior` + `fix(batch-48): complete requirement frontend acceptance` | `test_batch48_requirement_acceptance.py` 101 条、keyword、creator；`RequirementPage.test.tsx` |
| B47-DEF-009 抽取恢复/评估污染 | `fix(batch-48): harden requirement document behavior` + `fix(batch-48): complete requirement frontend acceptance` | `test_batch48_requirement_acceptance.py`；`requirement.test.ts` |
| B47-DEF-010 两个动作语义错误 | `fix(batch-48): complete requirement frontend acceptance` | `RequirementPage.test.tsx`：`use_extraction=true` 与重新拆分调用 |
| B47-DEF-011 版本继承丢失 | `fix(batch-48): make requirement review and import durable` | `test_batch48_requirement_acceptance.py`：继承字段、稳定索引、读取与导入 |
| B47-DEF-012 覆盖率/API 关联不持久 | `fix(batch-48): harden requirement document behavior` + `fix(batch-48): enforce requirement module isolation` + `fix(batch-48): complete requirement frontend acceptance` | `test_batch48_requirement_acceptance.py`；`RequirementPage.test.tsx` |
| B47-DEF-013 跨项目子节点泄露 | `fix(batch-48): enforce requirement module isolation` | `test_batch48_requirement_modules.py`：跨项目/跨 bundle 不泄露 |
| B47-DEF-014 懒加载丢孙节点 | `fix(batch-48): enforce requirement module isolation` | `test_batch48_requirement_modules.py`：完整树与三层懒加载一致 |
| B47-DEF-015 模块/API 关联缺校验 | `fix(batch-48): enforce requirement module isolation` | `test_batch48_requirement_modules.py`：方向、平台、枚举、重复、归属与持久化 |
| B47-DEF-016 截图地址/OCR 错误 | `fix(batch-48): complete requirement frontend acceptance` | `lanhuEvidence.test.ts` + `PrototypePreview.test.tsx`；真实截图与中文 OCR 浏览器闭环见 `lanhu-three-regression-audit.md` |
| B47-DEF-017 重叠轮询/重复 GET | `fix(batch-48): complete requirement frontend acceptance` | `EvidenceTaskPanel.test.tsx`、`useApi.test.ts`、Playwright 网络记录 |
| B47-DEF-018 移动端/a11y 不可用 | `fix(batch-48): complete requirement frontend acceptance` | `RequirementPage.test.tsx`；Playwright 桌面/平板/390 px 与键盘 |
| B47-DEF-019 旧库迁移/metadata 漂移 | `fix(batch-48): reconcile requirement database upgrades` | `test_batch48_requirement_migration.py`、`test_postgresql_migration_defaults.py`、`test_migration_revision_ids.py`、真实 PostgreSQL 旧卷隔离克隆与 metadata 检查 |
| B47-DEF-020 行为覆盖不足 | Batch 48 Tasks 1～6 的全部测试提交 | 四组后端验收测试、前端行为测试、Playwright；核对断言与缺陷一一对应 |
| B47-DEF-021 依赖漏洞 | `fix(batch-48): remediate frontend dependency risk` | `npm audit --omit=dev`、`npm audit`；记录完整结果和批准的残余风险 |

## 3. 48 条生产级复测用例

### 3.1 文档上传、列表、预览与删除

| 用例编号 | 模块 | 用例标题 | 重要程度 | 类型 | 前提条件 | 操作步骤/输入 | 可观察预期结果 | Batch 47 基线/缺陷 | 修复/自动化映射 | 执行前预置结果 | 执行前状态 | 执行前证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B47-REQ-001 | 登录/路由 | 管理员进入需求文档页 | P0 | UI/正面 | 开发服务正常 | 登录后访问 `/requirement` | 页面可见；列表请求成功；控制台无错误 | 通过 | 前端行为回归 + `requirement.acceptance.spec.ts` | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-002 | 上传 | 上传合法 Markdown | P0 | UI+API/正面 | 当前项目有效 | 上传含唯一正文标记的 `.md` | HTTP 200/code 0；创建一条文档并刷新列表；DB 与审计一致 | 通过 | `test_batch48_requirement_acceptance.py` + Playwright 上传链路 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-003 | 预览 | 上传后展示完整正文 | P0 | UI/正面 | 已上传合法 MD | 选中文档并查看“内容预览” | 展示完整上传正文；刷新后可恢复；他项目详情不可读 | 失败 / B47-DEF-003 | DEF-003 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-004 | 上传 | 拒绝不支持扩展名 | P1 | API/负面 | 已登录 | 上传 `.txt` | 明确拒绝；不创建文档、审计或后台任务 | 通过 | `test_batch48_requirement_acceptance.py` 上传负面回归 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-005 | 上传 | 20 MB+1 字节超限保护 | P0 | API/边界 | 已登录 | 上传 20 MB+1 字节 MD | HTTP/业务 413；无 DB、任务、审计副作用 | 失败 / B47-DEF-002 | DEF-002 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-006 | 上传 | 20 MB-1、20 MB、伪造长度边界 | P1 | API/边界 | 可构造流式请求 | 分别上传 20 MB-1、20 MB、实际超限但长度头伪造的数据 | 前两组按契约成功；实际字节超限始终 413；无半成品 | 阻塞 / B47-DEF-002 | DEF-002 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-007 | 上传 | 损坏 DOCX/XLSX 与空文件 | P1 | API/负面 | 已登录 | 上传空文件、损坏 Office 文件 | 返回可识别 400；DB、审计和任务无半成品 | 未执行 | DEF-002 映射 / `test_batch48_requirement_acceptance.py` | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-008 | 列表 | API 101 条分页契约 | P0 | API/边界 | 项目内预置 101 条文档 | 请求 page=1,page_size=100；再请求 page=2 | total=101；两页合计 101；无重复/遗漏；排序稳定 | 通过（仅首屏契约） | DEF-008 映射 / `test_batch48_requirement_acceptance.py` | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-009 | 列表/搜索 | UI 可访问第 101 条并服务端搜索 | P0 | UI/大数据 | 预置 101 条；目标只在服务端第 2 页 | UI 翻页并搜索目标标题，记录请求参数 | UI 使用服务端分页/搜索；目标可见；total 与结果一致 | 失败 / B47-DEF-008 | DEF-008 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-010 | 列表 | 列表创建人准确展示 | P1 | UI+API/正面 | 文档 creator_id 有效 | 查看 API 与列表创建人 | API 返回且 UI 显示真实创建人，无逐条 N+1 请求 | 失败 / B47-DEF-008 | DEF-008 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-011 | 列表 | 列表不返回大正文 | P1 | API/性能 | 存在大文档 | 请求列表，再按需请求详情 | Brief 不含 content；详情按需返回完整正文；列表负载受控 | 失败 / B47-DEF-003 | DEF-003 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-012 | 删除 | 删除文档并清理关联状态 | P0 | UI+API/正面 | 存在验收文档及关联状态 | 删除文档并刷新列表，关闭 Session 后查 DB/审计 | 文档消失；关联状态无孤儿；业务与审计同事务成功 | 通过（未验证审计持久化） | DEF-007 映射 / `test_batch48_requirement_acceptance.py` | 尚未执行 | 未执行 | 无（尚未执行） |

### 3.2 功能拆分、生成、审查与导入

| 用例编号 | 模块 | 用例标题 | 重要程度 | 类型 | 前提条件 | 操作步骤/输入 | 可观察预期结果 | Batch 47 基线/缺陷 | 修复/自动化映射 | 执行前预置结果 | 执行前状态 | 执行前证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B47-REQ-013 | 功能拆分 | 首次拆分并恢复待审核状态 | P0 | UI+API/主流程 | 配置真实 AI Key | 上传→拆分→GET extraction→刷新 | 模块/功能点持久化；刷新恢复；请求、响应和状态一致 | 阻塞 / ENV-001 | 真实 AI E2E + `test_batch48_requirement_acceptance.py` | 已完成真实 AI 拆分→确认→生成闭环 | 通过 | QA 报告：2 模块、15 功能点、13 功能用例；专项 27/27 |
| B47-REQ-014 | 功能拆分 | 仅 404 才触发重新拆分 | P1 | UI/异常 | 已有抽取结果 | 模拟无结果、403、500、超时 | 仅成功响应且无结果时允许发起拆分；403/500/超时保留旧结果并提示 | 失败 / B47-DEF-009 | DEF-009 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-015 | 功能拆分 | 确认/驳回后状态与评估一致 | P0 | API/状态迁移 | 有待确认抽取结果 | 分别确认、驳回、再次读取 | 状态正确；`overall_assessment` 保留评估文本；审计同事务持久化 | 失败 / B47-DEF-009 | DEF-009、DEF-007 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-016 | 用例生成 | “基于拆分生成”传递确认结果 | P0 | UI+API/主流程 | extraction_status=confirmed | 点击“生成用例（基于拆分）”并检查请求 | 请求包含 `use_extraction=true`；生成结果来源可追溯 | 失败 / B47-DEF-010 | DEF-010 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-017 | 用例生成 | “重新拆分”执行拆分而非生成 | P1 | UI/回归 | 已确认拆分 | 点击“重新拆分”并检查请求/页面状态 | 调用拆分 API，进入重新确认流程，不调用生成接口 | 失败 / B47-DEF-010 | DEF-010 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-018 | 审查 | 读取持久化审查队列 | P0 | UI+API/主流程 | 文档有 AI 用例 | 打开 `/requirement/{id}/review`；调用 review-state | 路由可访问；HTTP 200；展示功能/API 用例、状态与计数 | 失败 / B47-DEF-004 | DEF-004 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-019 | 审查 | 批准、驳回、刷新恢复 | P0 | UI+API/状态迁移 | 审查队列存在 | 批准、驳回、编辑后刷新；提交非法 index | 状态持久化；刷新恢复；非法 index 404；计数准确 | 失败 / B47-DEF-004 | DEF-004 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-020 | 编辑/导入 | 编辑后的用例内容真实入库 | P0 | UI+API/数据一致性 | AI 结果可编辑 | 修改标题/步骤→导入→查询 DB/审查状态 | 入库值等于用户最终确认值；编辑和导入状态可恢复 | 失败 / B47-DEF-005 | DEF-005 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-021 | 导入 | 精确选择功能/API 用例 | P0 | API/正面 | AI 结果含两类用例 | 分批选择功能/API 索引导入 | 仅选中项入库；分类计数、总数和 indices 准确累计 | 失败 / B47-DEF-006 | DEF-006 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-022 | 导入 | 相同索引重复/并发幂等 | P0 | API/并发 | 同一文档已有可导入用例 | 同索引顺序调用两次并并发两次 | 最多一份用例；重复返回幂等结果或冲突；计数不漂移 | 失败 / B47-DEF-006 | DEF-006 映射 + `test_batch48_postgresql_concurrency.py` | 已完成真实 PostgreSQL 4 路并发 | 通过 | `postgresql-concurrency-audit.md` |
| B47-REQ-023 | 导入 | 第 N 条失败时整批回滚 | P0 | API/事务 | 两条用例；第二条注入失败 | 执行批量导入并核对响应、DB、计数、审计 | TestCase=0；状态/计数不变；审计无残留；返回明确失败 | 失败 / B47-DEF-001 | DEF-001 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-024 | 版本继承 | 未变化功能点保留继承标记 | P1 | API/版本 | 父子版本和已确认抽取 | 对子版本执行拆分/序列化/再次读取 | `inherited/from_version` 正常字段持久化且可序列化 | 失败 / B47-DEF-011 | DEF-011 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-025 | 版本继承 | 继承用例可查询、选择和导入 | P0 | API/版本 | 父版本已有用例 | 子版本生成→GET cases→选择导入继承项 | `ai_raw` 可读继承项；索引稳定；导入正确历史用例且幂等 | 失败 / B47-DEF-011 | DEF-011 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-026 | 审计 | 成功业务与审计日志同时提交 | P0 | API/审计 | 可执行上传/抽取/导入/删除 | 分别执行写操作，关闭 Session 后查询业务与 audit | 两者均存在且用户/项目/IP/动作准确；失败时同时回滚 | 失败 / B47-DEF-007 | DEF-007 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-REQ-027 | 覆盖率 | 展示真实需求覆盖率 | P1 | UI+API/追溯 | 文档关联用例/计划/执行/缺陷 | 查看 coverage API 与页面覆盖卡片 | 页面使用真实 `coverage_rate`；刷新一致；关联数据可追溯 | 失败 / B47-DEF-012 | DEF-012 映射 | 尚未执行 | 未执行 | 无（尚未执行） |

### 3.3 需求模块、证据与 API 关联

| 用例编号 | 模块 | 用例标题 | 重要程度 | 类型 | 前提条件 | 操作步骤/输入 | 可观察预期结果 | Batch 47 基线/缺陷 | 修复/自动化映射 | 执行前预置结果 | 执行前状态 | 执行前证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B47-MOD-001 | 模块树 | 三层以上完整树与懒加载一致 | P0 | API/树结构 | bundle 含根/子/孙节点 | 请求完整树和 children API | 孙节点存在；children 与 child_count 一致；两种结果结构相同 | 失败 / B47-DEF-014 | DEF-014 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-MOD-002 | 项目隔离 | 他项目 parent/bundle 不可读取 | P0 | API/安全 | 项目 1 用户；项目 999 私有树 | 用项目 1 身份请求项目 999 children/full tree | 403/404；不得泄露名称、数量或结构；日志不含敏感内容 | 失败 / B47-DEF-013 | DEF-013 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-MOD-003 | 列表 | 过滤、分页和 count 使用同一条件 | P1 | API/组合 | 多平台/类型/层级/状态且超过一页 | 逐项和组合筛选，翻页并重复请求 | total 与 items 条件一致；排序稳定；无重复/遗漏 | 未执行 | `test_batch48_requirement_modules.py` 组合矩阵 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-MOD-004 | 模块提取 | 同 bundle 重复/并发提取幂等 | P1 | API/并发 | 可用蓝湖证据包 | 连续/并发 extract 并查询最终树/审计 | 不重复插入或明确版本覆盖；失败完整回滚 | 阻塞 / ENV-002 | 模块并发自动化 + 真实蓝湖 E2E | 目标页有界下载完成；真实 PostgreSQL 4 路并发均返回相同模块 ID，最终仅 1 module + 1 page | 通过 | `lanhu-three-regression-audit.md` |
| B47-MOD-005 | 交互/导航 | 交互 merge/replace 与全局导航分类 | P1 | API/状态 | 模块树已生成 | 提取、编辑、分类、再次读取；提交非法模块 | JSON 结构和状态持久化；非法模块/状态拒绝且无副作用 | 未执行 | `test_batch48_requirement_modules.py` 状态矩阵 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-MOD-006 | 附件 | 附件部分失败可追踪且不污染数据 | P1 | API/异常 | 真实证据包；正常附件与受控不可读附件 | 执行附件提取并核对分项、人工处理提示、知识实体和审计 | 分项结果可追踪；不可读项提示人工处理；知识实体不重复；失败项不污染成功数据 | 阻塞 / ENV-002 | 模块异常自动化 + 真实蓝湖证据包 | 正常项成功；不可读项计入 failed 并提示人工处理，失败项无业务副作用，重试无重复 | 通过 | `lanhu-three-regression-audit.md` |
| B47-MOD-007 | 管理端关联 | 只允许合法 client→ADMIN 关系 | P1 | API/规则 | APP/PC/WEB/ADMIN 模块齐全 | 创建合法、非法方向/平台/枚举、重复和并发关系 | 非法 400/422；合法持久化；重复/并发不产生多条 | 失败 / B47-DEF-015 | DEF-015 映射 + `test_batch48_postgresql_concurrency.py` | 已完成真实 PostgreSQL 6 路并发 | 通过 | `postgresql-concurrency-audit.md` |
| B47-MOD-008 | API 匹配 | 文档存在/归属与匹配响应准确 | P1 | API/正负面 | integration 需求和 Swagger 资产 | 正常匹配；不存在/他项目 document_id；他项目 endpoint | 正常返回候选；非法文档/endpoint 404；不泄露他项目信息 | 失败 / B47-DEF-015 | DEF-015 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-MOD-009 | API 关联 | 匹配确认后持久化需求→API 关系 | P1 | UI+API/追溯 | 已得到匹配候选 | 用户确认匹配，刷新并查询 coverage/DB | 关系可恢复；供覆盖追溯使用；审计同事务持久化 | 失败 / B47-DEF-012 | DEF-012 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-MOD-010 | 截图/OCR | 证据截图可查看且 OCR 文本可用 | P0 | UI+API/主流程 | 蓝湖证据包完成 | 在需求页查看截图、OCR/merged_text 和置信度 | 使用正确 asset URL；图片可见；文本与页面 ID 对应且可追溯 | 失败 / B47-DEF-016 | DEF-016 映射 | 目标页生成 7 段未截断截图；中文 OCR 637 块，merged_text 非空；浏览器控制台和失败请求均为 0 | 通过 | `lanhu-three-regression-audit.md` |
| B47-MOD-011 | 采集任务 | 轮询不重叠、可停止、故障不刷屏 | P1 | UI/稳定性 | 证据任务面板打开 | 长时间运行；模拟慢响应、网络故障、完成和卸载 | 单次轮询；不重叠；完成/卸载取消；3/6/12/30 秒退避；一次错误提示 | 失败 / B47-DEF-017 | DEF-017 映射 | 尚未执行 | 未执行 | 无（尚未执行） |

### 3.4 UI、迁移、自动化与依赖安全

| 用例编号 | 模块 | 用例标题 | 重要程度 | 类型 | 前提条件 | 操作步骤/输入 | 可观察预期结果 | Batch 47 基线/缺陷 | 修复/自动化映射 | 执行前预置结果 | 执行前状态 | 执行前证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B47-NFR-001 | 响应式 | 390×844 可完整操作需求页 | P0 | UI/兼容 | 移动视口 | 打开需求页并执行上传、搜索、分页、预览/审查入口 | 单列或合理折行；控件和内容不裁切；无需非预期横向滚动 | 失败 / B47-DEF-018 | DEF-018 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-NFR-002 | 无障碍 | 文档行具备键盘等价操作 | P1 | UI/a11y | 列表有文档 | Tab 聚焦；Enter/Space 选择；检查语义与可见焦点 | 可聚焦并激活；`aria-selected`/语义正确；鼠标与键盘结果一致 | 失败 / B47-DEF-018 | DEF-018 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-NFR-003 | 网络 | 首次进入仅一次有效列表 GET | P1 | UI/性能 | 新浏览器会话/Strict Mode | 进入 `/requirement`，记录网络并卸载页面 | 同一参数只有 1 次有效 GET；卸载取消请求；无重复副作用 | 失败 / B47-DEF-017 | DEF-017 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-NFR-004 | 迁移 | 空库升级到唯一 head | P0 | DB/部署 | 隔离空库 | `alembic upgrade head`；`alembic current`；再次升级 | exit 0；current=唯一 Batch 48 head；重复升级无操作 | 通过（仅空库） | DEF-019 映射 / `test_batch48_requirement_migration.py` | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-NFR-005 | 迁移 | 真实旧库升级包含新增字段 | P0 | DB/升级 | 脱敏旧生产 PostgreSQL 快照；`AUTO_CREATE_TABLES=false` | 记录升级前数据→升级到 head→查询字段/数据→重复升级 | 新字段/唯一索引存在；历史数据不丢；服务查询可用；重复升级安全 | 失败 / B47-DEF-019 | DEF-019 映射 | 已从旧卷隔离克隆升级并重复执行 | 通过 | `postgresql-alembic-drift-audit.md` |
| B47-NFR-006 | 迁移 | head 与 ORM metadata 无漂移 | P0 | DB/部署 | 已 upgrade head；模型完整注册 | `alembic check` 并检查 head 数量 | exit 0；唯一 head；不提议删除真实表/索引/字段 | 失败 / B47-DEF-019 | DEF-019 映射 | 唯一 head `20260727_batch48_pg_parity`；metadata 零漂移 | 通过 | `postgresql-alembic-drift-audit.md` |
| B47-NFR-007 | 后端质量 | F821、专项和全量 Pytest | P0 | 自动化/回归 | 依赖已安装 | Ruff；五组 requirement 专项；后端全量 tests | 全绿且记录精确通过/失败数；无新增失败；行为断言覆盖缺陷 | 通过（Batch 47 仅浅覆盖）/ B47-DEF-020 | DEF-020 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-NFR-008 | 前端质量 | typecheck、build、Vitest | P0 | 自动化/回归 | npm 依赖已安装 | 执行 typecheck、build、需求专项和前端全量 Vitest | 命令全绿；需求 API/页面/弹窗/审查/轮询有行为断言；记录精确统计 | 失败 / B47-DEF-020 | DEF-020 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-NFR-009 | 依赖安全 | 生产依赖无高危漏洞 | P0 | 安全/供应链 | lockfile 固定 | `npm audit --omit=dev` | high/critical=0；其他问题有处置结论和证据 | 失败 / B47-DEF-021 | DEF-021 映射 | 尚未执行 | 未执行 | 无（尚未执行） |
| B47-NFR-010 | 依赖安全 | 全依赖无严重未评估漏洞 | P1 | 安全/供应链 | lockfile 固定 | `npm audit` | 无 critical/high，或每项有责任人、到期日和批准的风险接受 | 失败 / B47-DEF-021 | DEF-021 映射 | 尚未执行 | 未执行 | 无（尚未执行） |

## 4. Batch 48 执行与证据登记

> 本表是 Batch 48 的权威执行结果；第 3 节固定保留 Batch 47 基线、复测步骤和修复映射。完整命令、环境、A01～A12 判定和剩余风险见 `work-logs/batch-48-需求服务验收修复-qa-report.md`。

| 用例 ID | Batch 48 实际结果 | 状态 | 新缺陷 ID | 执行人/日期 | 脱敏证据 |
| --- | --- | --- | --- | --- | --- |
| B47-REQ-001 | 登录、页面加载、单次列表 GET、控制台均符合预期 | 通过 | 无 | Codex / 2026-07-27 | Playwright / QA 报告 |
| B47-REQ-002 | 合法 Markdown 上传、刷新、持久化与审计一致 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 + Playwright |
| B47-REQ-003 | 正文按需加载、刷新恢复且跨项目不可读 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 + 三视口截图 |
| B47-REQ-004 | `.txt` 明确拒绝且无副作用 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 |
| B47-REQ-005 | 20 MB+1 返回 413 且无半成品 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 |
| B47-REQ-006 | 20 MB-1/20 MB 成功；伪造长度的实际超限仍返回 413 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 |
| B47-REQ-007 | 空文件、损坏 DOCX/XLSX 返回 400 且无半成品 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 |
| B47-REQ-008 | 101 条分页完整、稳定且无重复遗漏 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 |
| B47-REQ-009 | 服务端分页/搜索可到达第 101 条 | 通过 | 无 | Codex / 2026-07-27 | Vitest + 移动端 Playwright |
| B47-REQ-010 | 创建人准确且列表查询无逐条请求 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 + Vitest |
| B47-REQ-011 | Brief 无正文，详情按需返回完整正文 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 + Vitest |
| B47-REQ-012 | 删除、关联清理和审计同事务完成 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 + Playwright |
| B47-REQ-013 | 真实 AI 拆分得到 2 模块/15 功能点；确认后生成 13 条功能用例，状态、DB 与审计一致 | 通过 | 无 | Codex / 2026-07-27 | 真实 AI 专项 27/27 + QA 报告 |
| B47-REQ-014 | 仅 404/空结果触发新拆分；403/500/超时不覆盖旧结果 | 通过 | 无 | Codex / 2026-07-27 | `requirement.test.ts` |
| B47-REQ-015 | 确认/驳回可恢复，评估文本与审计正确 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 |
| B47-REQ-016 | 基于拆分生成传递 `use_extraction=true` | 通过 | 无 | Codex / 2026-07-27 | `RequirementPage.test.tsx` |
| B47-REQ-017 | 重新拆分只执行驳回+拆分，不误调用生成 | 通过 | 无 | Codex / 2026-07-27 | `RequirementPage.test.tsx` |
| B47-REQ-018 | 审查路由、队列、两类用例与计数可读取 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 + Vitest + Playwright |
| B47-REQ-019 | 批准、驳回、编辑持久化；非法索引 404 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 + Vitest |
| B47-REQ-020 | 编辑后的最终内容真实入库并可恢复 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 + Vitest |
| B47-REQ-021 | 功能/API 索引精确导入且计数累计准确 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 |
| B47-REQ-022 | 真实 PostgreSQL 4 路并发结果为 1 导入、3 跳过；最终仅 1 条且计数无漂移 | 通过 | 无 | Codex / 2026-07-27 | `postgresql-concurrency-audit.md` |
| B47-REQ-023 | 第二条失败时业务、计数和审计全部回滚 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 |
| B47-REQ-024 | 继承标记持久化、序列化并可重读 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 |
| B47-REQ-025 | 继承用例生成、查询、选择导入且幂等 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 |
| B47-REQ-026 | 关键成功写与审计同提交，失败同回滚 | 通过 | 无 | Codex / 2026-07-27 | 后端验收 + 模块验收 |
| B47-REQ-027 | 真实关联计算 75%，页面展示 75% | 通过 | 无 | Codex / 2026-07-27 | 后端验收 + Vitest |
| B47-MOD-001 | full/lazy 根子孙三层结构与计数一致 | 通过 | 无 | Codex / 2026-07-27 | 模块验收 |
| B47-MOD-002 | 跨项目 parent/bundle 被拒绝且不泄露结构 | 通过 | 无 | Codex / 2026-07-27 | 模块验收 |
| B47-MOD-003 | 过滤、层级、分页、count 与重复请求结果稳定 | 通过 | 无 | Codex / 2026-07-27 | 模块验收 |
| B47-MOD-004 | 真实目标页有界下载完成；真实 PostgreSQL 4 路并发全部返回相同模块 ID，最终仅 1 module + 1 page，无重复或半棵树 | 通过 | 无 | Codex / 2026-07-27 | `lanhu-three-regression-audit.md` |
| B47-MOD-005 | merge/replace、分类和非法模块/状态均符合契约 | 通过 | 无 | Codex / 2026-07-27 | 模块验收 |
| B47-MOD-006 | 复用真实 URL；正常附件继续处理，不可读附件返回人工处理提示且无业务副作用，重试不产生重复实体 | 通过 | 无 | Codex / 2026-07-27 | `lanhu-three-regression-audit.md` |
| B47-MOD-007 | 真实 PostgreSQL 6 路并发得到 1×200、5×409；最终仅 1 条关联且无漂移 | 通过 | 无 | Codex / 2026-07-27 | `postgresql-concurrency-audit.md` |
| B47-MOD-008 | 不存在/他项目文档、服务和 endpoint 均被拒绝 | 通过 | 无 | Codex / 2026-07-27 | 模块验收 |
| B47-MOD-009 | 匹配确认去重持久化，审计和 coverage 可追溯 | 通过 | 无 | Codex / 2026-07-27 | 模块验收 + API Vitest |
| B47-MOD-010 | 目标页生成 7 段未截断截图和 637 个中文 OCR 文本块；merged_text 非空，浏览器可见且控制台错误/失败请求均为 0 | 通过 | 无 | Codex / 2026-07-27 | `lanhu-three-regression-audit.md` |
| B47-MOD-011 | 轮询不重叠，可取消，按 3/6/12/30 秒退避且只提示一次 | 通过 | 无 | Codex / 2026-07-27 | `EvidenceTaskPanel.test.tsx` |
| B47-NFR-001 | 390×844 完成上传、分页、搜索、预览和审查入口，无全局溢出 | 通过 | 无 | Codex / 2026-07-27 | Playwright + 截图 |
| B47-NFR-002 | Enter/Space 均可选择，Axe 无违规 | 通过 | 无 | Codex / 2026-07-27 | Playwright |
| B47-NFR-003 | Strict Mode 首次仅一次有效 GET，取消请求不提示错误 | 通过 | 无 | Codex / 2026-07-27 | Vitest + Playwright |
| B47-NFR-004 | 空库升级到唯一 Batch 48 head，重复升级安全 | 通过 | 无 | Codex / 2026-07-27 | 迁移测试 + Alembic |
| B47-NFR-005 | 旧卷隔离克隆从 `20260714_lanhu_pg_reconcile` 升至 `20260727_batch48_pg_parity`；重复升级通过且数据计数不变 | 通过 | 无 | Codex / 2026-07-27 | `postgresql-alembic-drift-audit.md` |
| B47-NFR-006 | 唯一 head `20260727_batch48_pg_parity`；`alembic check` 零漂移 | 通过 | 无 | Codex / 2026-07-27 | `postgresql-alembic-drift-audit.md` |
| B47-NFR-007 | Ruff F821 通过；后端全量 812 通过、2 条默认跳过的真实 PG 集成用例（显式开启后 2/2 通过） | 通过 | 无 | Codex / 2026-07-27 | QA 报告 |
| B47-NFR-008 | typecheck/build 通过；前端 29 文件、124 测试通过 | 通过 | 无 | Codex / 2026-07-27 | QA 报告 |
| B47-NFR-009 | 生产依赖 high=0、critical=0；moderate=2 已登记 | 通过 | 无 | Codex / 2026-07-27 | `npm audit --omit=dev --json` |
| B47-NFR-010 | 全依赖 high=0、critical=0；moderate=2 已登记 | 通过 | 无 | Codex / 2026-07-27 | `npm audit --json` |

## 5. 执行汇总

本轮 48 条行为复测结果如下：

| Batch 48 状态 | 数量 | 说明 |
| --- | ---: | --- |
| 通过 | 48 | P0 28 条、P1 20 条 |
| 失败 | 0 | 本轮未发现新增失败 |
| 阻塞 | 0 | 无行为用例阻塞 |
| 未执行 | 0 | 无 |
| **总计** | **48** | **行为验收 48/48；A01～A12 全部通过，最终为 `READY`** |

## 6. 执行与证据回填要求

1. 初始实现提交：`d1f7e52be70757c14d4acc153dee17571773b931`；真实外部复测兼容与 PostgreSQL 修复提交：`4dc307ed481fdb9ba01f5b8f949aeed7aef24503`。
2. 浏览器证据使用确定性 API 契约 fixture；真实后端行为由同批次 Pytest/迁移测试独立证明，二者不能互相替代。
3. B47-REQ-022、B47-MOD-007 已在真实 PostgreSQL 多连接竞争下通过；并发输出和最终数据库状态见 `postgresql-concurrency-audit.md`。
4. 旧版 PostgreSQL 卷只使用隔离克隆复测，原卷未修改；升级与 metadata 证据见 `postgresql-alembic-drift-audit.md`。
5. B47-MOD-004、B47-MOD-006、B47-MOD-010 的统一脱敏执行证据见 `lanhu-three-regression-audit.md`；不得在文档中记录 URL、Cookie 或 OCR 正文。
6. `lanhu-mcp@74bfa7b463ef505008ea25466bc950ad9ed67324` 已发布到根仓配置的可访问 fork，并通过独立克隆验证；A12/交付可追溯通过，最终结论为 `READY`。
