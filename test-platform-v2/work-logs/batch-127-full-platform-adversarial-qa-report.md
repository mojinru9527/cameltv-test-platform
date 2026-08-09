# Batch 127 — QA 报告（全功能第一性原理验收与对抗性加固）

> **QA (🔍)** | Date: 2026-08-09 | Verdict: PASS（远端 required checks 待 Draft PR）

## 1. 验收结论

- 生产环境完成全路由、动态详情和知识中心 12 页签只读走查，全程未执行创建、编辑、审批、导入、删除、发布或回滚。
- 隔离本地环境完成真实登录/强制改密、35 路由、动态详情、导航、创建与清理计划/发布包夹具、权限/项目隔离和受控失败验证。
- 共记录 14 项问题：P0×0、P1×10、P2×4、P3×0；本批修复 14 项中的可代码闭环部分，外部依赖/数据资产债务沿用既有 C 条件，不记为通过。
- C120-3（交互缺口分页/筛选）已关闭；没有新增未跟踪 Leader 条件。

## 2. 关键交付

| 域 | 交付 |
|----|------|
| 数据与契约 | 用例类型 canonical/统计守恒、软删除排除、实体服务端全量统计、Token scopes JSON、安全兼容旧数据、OpenAPI 类型同步 |
| 性能与并发 | 交互缺口一次性文本索引；AbortSignal 清理；ADB 直连硬超时；设备发现与 DB 会话解耦；Android/iOS 包列表正确调用 |
| 产品体验 | 状态中文化、UI 结果业务摘要、计划状态兜底、需求/缺口分页、受控 503、性能标题/连接态、生产主题实验室门禁 |
| 可发现性/a11y | 发布包、缺陷、数据集、集成恢复菜单入口；删除、调度开关、审计刷新补可访问名称 |
| 工程治理 | SQLite `batch_alter_table` 迁移修复、旧 E2E 扩面、README/现状 PRD 更新、C 条件结构修复、两处吞异常改显式运维日志 |

## 3. 最终门禁证据

| 门禁 | 命令/范围 | 结果 |
|------|-----------|------|
| 后端运行时硬门禁 | `ruff check app/ --select F821` | exit 0，All checks passed |
| 后端全量 | `pytest` | exit 0，`1233 passed, 3 skipped, 21 warnings`，299.81s |
| 性能采集定向 | `pytest -q tests/test_perf_collector_contract.py tests/test_perf_api.py` | exit 0，47 passed |
| 前端全量 | `npm test -- --run` | exit 0，101 files / 391 tests |
| 前端类型与构建 | `npm run build`（含 `tsc -b`） | exit 0，3438 modules，Vite build 成功 |
| 真实浏览器矩阵 | Playwright PC cyberpunk/light + 真实本地后端 | exit 0，1 test；35 routes、0 issues、0 duplicate GET、1 个预期受控 blocker |
| 迁移 | brand-new SQLite `alembic upgrade head` + `alembic heads` | exit 0；新库从零到 head；唯一 head `20260808_batch121_topo_edges` |
| OpenAPI | `openapi-typescript http://127.0.0.1:8048/openapi.json` | exit 0；统计端点及既有 schema 漂移已同步 |
| 工作树 | `verify-ai-worktree.ps1 -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor codex` | exit 0；分支/执行器/scope/端口元数据匹配 |
| C 条件 | `audit-cconditions.ps1 -RequireLatestBatch` | exit 0；hard 0 / warning 0；closed evidence missing 0 |
| 常见 Bug | `scan-common-bugs.ps1` | HARD 0；WARN 249（运维脚本显式输出等非阻断项） |
| 差异格式 | `git diff --check` | exit 0；仅 Git 提示一个内容哈希未变化的 CRLF stat，刷新索引后不在变更范围 |

### WARN 复核

- Batch 126 记录的观测值为 247；本批为 249，新增 2 个命中均是把 `except: pass` 硬错误改为可观测的运维脚本 `print(..., file=sys.stderr)`，属于扫描器明确标注“运维脚本可接受，需复核”的同一既有类别。
- 相比仓库静态 `warn-baseline.json`（209）没有新增类别；该基线自身遗漏 10 个既有文件，不能用其总数替代逐文件复核。
- 本批生产代码无 `console.log`、`debugger`、`breakpoint`、裸 `print` 或硬编码凭据；本地一次性凭据和运行日志已删除，未纳入 Git。

## 4. 失败与返工闭环

| 首轮失败 | 根因 | 闭环 |
|----------|------|------|
| 全平台浏览器矩阵出现重复有效 GET/冷启动设备探测等待 | React StrictMode 请求未取消；SoloX 内部 ADB 无超时 | AbortSignal cleanup；API timeout；最终改为直接 ADB 硬超时且无 shell |
| 运维未配置态被 Axe 判定不可识别 | 预期 503 走通用错误/toast | 专用受控未启用 alert + 恢复文案，矩阵 0 issues |
| 前端全量 3 个断言失败 | UI 统计文案已中文化，测试仍匹配旧英文 | 更新唯一漂移断言；定向 14/14、全量 391/391 |
| brand-new SQLite 迁移失败 | Batch 115 迁移使用 SQLite 不支持的 `ALTER COLUMN` | 改为 Alembic batch alter；半迁移重试与全新库升级均成功 |
| 清理本地服务发现孤儿 ADB probe | API 取消线程不能终止 SoloX `os.popen` 子进程 | TDD 增加有界 ADB/正确包列表/iOS 方法契约；孤儿进程和含凭据日志已删除 |

## 5. 受控限制

- 生产尚未包含本分支修复，必须在合入并进入发布火车后复验数据口径与主题实验室门禁。
- 没有可用的真实发布控制存储、第三方集成凭据和受支持 iOS 设备；相应页面必须保持明确未启用/阻塞，不得返回模拟数据。
- 知识实体来源、覆盖率/置信度、Wiki Markdown 与大图性能继续由 C126-1~4、C123-3/4 跟踪。

## 6. 发布建议

状态：**READY FOR TOTAL CONFIRMATION**。本地必修复为 0；待用户一次总确认后推送、创建 Draft PR，并以 required checks 与最终 `audit-ai-pr.ps1 -RequireSuccessfulChecks` 作为合入门禁。

**技能使用**：`cameltv-agent-team`、`test-case-design`、`playwright-skill`、`cameltv-bug-guard`、`cameltv-ui-conventions`、`design-taste-frontend`、`karpathy-guidelines`、`cameltv-api-test`；技能结论不替代上述执行证据。
