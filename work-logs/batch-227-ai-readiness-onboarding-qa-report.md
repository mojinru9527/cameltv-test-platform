# Batch 227 — QA 报告

> QA | Date: 2026-09-03 | Verdict: PASS（代码与本地链路）

## 测试总览

| 条件数 | 通过 | 失败 | 外部阻塞 |
|--------|------|------|----------|
| 10 | 10 | 0 | 3 |

外部阻塞不影响本批代码验收，但体育 `16.0.0` 真实业务全链路仍保持 BLOCKED：缺健康 AI Provider、真实体育 OpenAPI/被测环境、以及耐久执行所需的在线 Worker/Runner。Temporal/Worker 是平台常驻基础设施，不要求普通用户随单次任务手动启动。

## 可执行门禁

| 检查 | 命令摘要 | 退出码/结果 |
|------|----------|-------------|
| 后端全量 | `python -m pytest -q` | 0；2407 passed / 49 skipped / 1 xfailed / 0 failed |
| 后端定向 | VersionTask + route inventory + migration revision/single head | 0；41 passed |
| 后端静态 | app import；`ruff check app/ --select F821` | 0；PASS |
| Alembic | `alembic heads` + 空内存 SQLite `upgrade head` | 0；单一 head `20260911_business_onboarding_context` |
| 前端全量 | `npm test -- --reporter=dot` | 0；133 files / 616 tests passed |
| 前端类型 | `npm run typecheck` | 0；PASS |
| 前端 lint | `npm run lint` | 0；PASS |
| 前端构建 | `npm run build` | 0；3666 modules transformed |
| G0-G2 | `dev-gate.ps1` | 2；`PASS_WITH_WARN`，0 HARD / 330 全仓 WARN，F821/typecheck/lint/4 route guards 全过 |
| C 条件审计 | `audit-cconditions.ps1 -RequireLatestBatch` | 0；0 hard / 0 warning，本批 C227-1/C227-2 已登记 |
| 浏览器 | Playwright visible browser，体育 16.0.0 完整需求 | 0；PASS，0 console error / 0 page error |

`dev-gate` 的退出码 2 是脚本定义的“机械项通过、存在 WARN 待人工复核”。初跑命中的 2 个 HARD 位于 `requirement_service.py:225/229` 的既有 JSON 降级分支；本批补充意图注释后为 0 HARD，未改变解析行为。330 条 WARN 为全仓人工复核基线，本批没有新增 HARD。

## 逐条件验证

| 条件 | 结果 | 证据 |
|------|------|------|
| 六个用户必填字段与缺项禁用 | PASS | `OnboardingPage.test.tsx:50`、E227-04 |
| 版本与需求正文落库 | PASS | `test_version_task.py`、E227-03 |
| 需求绑定 VersionTask AI 上下文 | PASS | `onboarding_service.py:75`、41 项定向回归 |
| 相同版本/相同需求幂等复用 | PASS | `test_version_task.py:536`；真实浏览器重复执行未再 500 |
| 相同版本/不同需求拒绝覆盖 | PASS | `test_version_task.py:591`；在 OpenAPI 访问前拒绝，导入批次为 0 |
| AI 只在最近真实健康态 ok 时 ready | PASS | `onboarding_service.py:184`、`test_version_task.py:760` |
| Temporal/Worker 平台托管语义 | PASS | `OnboardingPage.test.tsx:63`、E227-03 |
| readiness 页面只请求一次 | PASS | E227-03：readiness=1 |
| 三视口无溢出且长需求渐进展示 | PASS | E227-04 至 E227-07 |
| 缺外部条件不假绿 | PASS | E227-03：AI action disabled，baseline/durable 均未就绪 |

## 本轮发现与关闭

| # | 严重级 | 描述 | 状态 |
|---|--------|------|------|
| B227-P1-01 | P1 | 已有同项目同版本任务时重复创建 VersionTask，触发唯一约束 500 | 已修复并补 2 条回归 |
| B227-P1-02 | P1 | 同版本不同需求虽被拒绝，但拒绝前已产生 OpenAPI 导入副作用 | 已前移冲突校验；测试证明未访问 OpenAPI、导入批次为 0 |
| B227-P2-01 | P2 | 保存后完整展开长需求，移动端状态区过远 | 已改为默认收起并重采三视口 |
| B227-P2-02 | P2 | C 条件审计器不识别删除线中的已关闭 ID 与历史区间简写，产生 24 个假阳性 | 已兼容 `~~ID~~` 与既有区间 token；审计 0 hard / 0 warning |

## 发布建议

状态：READY FOR DRAFT PR。代码可进入 required checks；不得把本地 OpenAPI 导入 PASS 写成体育业务全链路 PASS。真实体育放行仍需在页面显示的外部条件全部就绪后重新执行。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 5h / 实际约 1.6h | 0/2/2/0 | 4 | 技术债 + 边界场景 + 工具链 | 冲突校验测试同时断言外部调用次数和数据库副作用为 0 |

**技能使用**：cameltv-agent-team、cameltv-bug-guard、cameltv-ui-conventions、Impeccable onboard、Playwright；结论均以命令和证据文件为准。
