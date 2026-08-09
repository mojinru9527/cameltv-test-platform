# Batch 130 — QA 报告（用例模块聚合与异常覆盖加固）

> **QA (🔍)** | Date: 2026-08-09 | Verdict: PASS（待用户总确认与 required checks）

## 1. 验收结论

- 用例服务按“产品界面 → 业务模块 → 子模块”聚合，用户端与运营后台明确分层；PC Web、安卓/iOS、移动 Web 仅保留为 `端:*` 标签，不再拆成业务模块。
- taxonomy、列表、分页和 Excel/XMind 导出共同使用 `surface/taxonomy_domain/taxonomy_module/positive_negative` 筛选契约；父模块筛选包含所有后代。
- 表格新增正向、负向、边界标签和场景筛选，可直接抽查非正常路径；列表输出不再丢失数据库已有的 `positive_negative`。
- 全量体育资产共 7,879 条、46 个数据入口、38 个业务模块；正向 3,983、负向 3,216、边界 680，非 happy-path 占 49.45%。
- 38/38 业务模块同时具备正向和负向用例，并各补充“故障恢复”和“重复/并发”两类可执行对抗用例，共新增 76 条。
- 导入器按来源清单锁定用户端/运营后台上层，解决“商城/UGC”等同名模块歧义；稳定 ID、精确查重和端别标签均有回归测试。

## 2. 测试先行与问题闭环

| 阶段 | 结果 |
|------|------|
| RED | 规范化、父级聚合、场景筛选、稳定 ID、精确查重和 38 模块对抗覆盖契约先失败 |
| GREEN（定向） | 后端相关 69 tests passed；前端 taxonomy/页面相关 8 tests passed |
| 对抗复核 | 发现共享裸名称会误判端别，新增“来源模块为权威上层”规则与 `source_module_mismatches` 数据门禁 |
| 兼容复核 | 首次最终定向回归暴露旧入口未重导出分类器；修复兼容导入后 69/69 通过 |

## 3. 数据质量门禁

`scripts/audit_sports_case_quality.py` 对完整 consolidated 资产执行，结果保存在 `work-logs/evidence/batch-130-case-module-quality/case-quality-audit.json`。

| 指标 | 结果 |
|------|------|
| 总量 / 唯一 ID | 7,879 / 7,879 |
| 业务模块 | 38 |
| 正向 + 负向成对 | 38/38 |
| 故障恢复 + 重复/并发 | 38/38 |
| 非 happy-path 占比 | 49.45% |
| 缺标题/前置/步骤/预期 | 0 / 0 / 0 / 0 |
| 终端渠道 taxonomy 节点 | 0 |
| 来源用户端/后台错配 | 0 |

同时修复两条基础资产缺陷：搜索无结果用例缺步骤/预期，后台商城奖牌编号不一致用例缺最终断言/预期。

## 4. 最终工程门禁

| 门禁 | 命令/范围 | 结果 |
|------|-----------|------|
| 后端运行时硬门禁 | `python -m ruff check app/ --select F821` | exit 0，All checks passed |
| 后端定向 | importer + overlay + testcase | exit 0，69 passed |
| 后端全量 | `python -m pytest -q` | exit 0，1292 passed / 3 skipped / 22 warnings，307.67s |
| 前端全量 | `npm test -- --run` | exit 0，108 files / 437 tests |
| 前端 lint | `npm run lint` | exit 0 |
| 前端类型 | `npm run typecheck` | exit 0 |
| 前端构建 | `npm run build` | exit 0，3447 modules transformed |
| 应用导入 | `python -c "import app.main"` | exit 0（本机无 adb 为非阻塞提示） |
| 迁移拓扑 | `python -m alembic heads` | exit 0，唯一 head `20260808_batch121_topo_edges` |
| 常见 Bug | `scan-common-bugs.ps1` | HARD 0；WARN 251；新增 2 项均为运维审计/生成脚本的预期 `print` |
| Worktree | `verify-ai-worktree.ps1 -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor codex` | exit 0；分支、执行器、scope、端口匹配 |
| C 条件 | `audit-cconditions.ps1 -RequireLatestBatch` | exit 0；hard 0 / warning 0 / closed missing evidence 0 |
| 差异格式 | `git diff --check` | exit 0（仅已有 CRLF 转换提示） |

3 个 skip 为仅 PostgreSQL 环境运行的既有并发场景，本批没有新增 skip。22 个 warning 均为既有框架/测试警告；无新增测试失败。

## 5. 浏览器与视觉证据

Playwright 使用隔离服务 `frontend:5219 / backend:8049` 和隔离 SQLite 数据库，可见 Chromium 执行。

| 场景 | 结果 |
|------|------|
| 产品界面分层 | 用户端、运营后台分开显示 PASS |
| 终端壳层 | 分类树无 PC Web、安卓/iOS、移动 Web 节点 PASS |
| 业务模块聚合 | 赛事详情计数 3；预测 Pick 父模块包含 3 个后代 PASS |
| 异常筛选 | 负向筛选返回 2 条，单次操作有效 GET 1 次 PASS |
| 响应式 | 768×1024、390×844 无正向横向页面溢出 PASS |
| 浏览器总览 | console errors 0、page errors 0 |

证据目录：`work-logs/evidence/batch-130-case-module-quality/browser/`。

## 6. 风险与发布边界

- 规范筛选对既有约 8k 用例采用先做 SQL 条件收窄、再规范匹配的兼容路径；本批规模可接受，未来数量显著增长时可考虑持久化规范列和索引。
- 完整资产和安全导入器已就绪，但本批没有在生产执行导入；必须在代码合入并进入受控发布后，使用生产凭据执行并复验计数。
- `npm ci` 对锁文件报告既有 4 个 high severity 依赖告警；本批未新增依赖。
- 本报告仅证明本地交付就绪，不代表已推送、合入或发布生产。

## 7. QA 判定

**PASS / READY FOR TOTAL CONFIRMATION**。允许展示完整待推送范围并请求一次总确认；确认后才可推送、创建 Draft PR，required checks 和最终 PR 审计全部通过后方可合入 `main`。
