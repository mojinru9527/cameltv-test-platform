# Batch 60 测试平台生产级验收 QA 报告

## 1. 结论

**最终判定：`NEEDS WORK`；production 发布：`DEFERRED`。**

本地可控范围已形成真实数据、浏览器、API、数据库和自动化执行闭环，前后端全量测试与构建通过；但 Test5 六服务、体育业务 E2E、真实旧 PostgreSQL、外部 AI/蓝湖/通知/集成、真机性能仍阻塞，体育 UI 自动化生产依赖仍有 7 个 high 漏洞，A01–A14 尚未全部满足，因此不得签署生产验收通过。

## 2. 固定基线与环境

| 项目 | 结果 |
| --- | --- |
| 分支 | `feature/batch-60-sports-platform-production-validation` |
| 起始基线 | `d15ed2197e41bbcecfac733f059160a912373317` |
| 当前交付状态 | 基于上述基线的验收修复与 QA 收尾；最终本地提交、push 和 PR 状态以交付记录为准 |
| 工作流 | 独立 Agent Team worktree，执行器 Codex |
| 前端 | `http://localhost:5196`，HTTP 200 |
| 后端 | `http://127.0.0.1:8026/api/v1/open/health`，HTTP 200；前端代理同端点 HTTP 200 |
| 数据库 | 独立 SQLite `platform-local.db`；未纳入版本控制 |
| 浏览器证据 | Chrome/Chromium；PC 视口 `1440×900` |
| 外部安全边界 | 生产体育系统只允许获准 GET/HEAD；未执行支付、发布、封禁、推流、压测或其他写操作 |

## 3. 执行范围与真实数据

- 已覆盖登录、工作台、质量追溯、需求、知识、脑图、用例、计划、接口测试、UI 自动化、音视频、定时任务、报告、系统、项目、缺陷、数据集、集成、Agent、性能、通知、环境、主题和发布包。
- R1 OpenAPI 形成 `5 paths → 5 接口资产 → 7 测试用例 → 计划/执行/缺陷/报告/追溯` 的本地真实闭环。
- UI 自动化真实 Job 1 / Run 5：`5 total / 4 pass / 0 fail / 1 skip`；跳过项为无授权生产账号的登录，不计通过。
- Run #5 的 5 个产物均经 Cookie 与 `X-Project-Id` 鉴权接口返回 200，3 张 PNG 均实际解码并可查看。
- 音视频任务使用仓库真实 MP4 经 HTTP Range 和 ffprobe 执行，终态 `done`，持久化 6 项真实指标。
- 已建立禁用的 R1 周回归 Cron、R1 原型冻结版→生产验收基线发布链，并完成管理员/测试员权限复核。
- 历史 Test5 `892/1323` 仅作为需求与回归输入，未计入本轮通过。

体育接口与 UI 自动化逐条用例、正负面覆盖及阻塞见 `batch-60-sports-api-ui-automation-validation.md`。该专项共 39 条：14 通过、5 失败、8 阻塞、12 未执行。

## 4. PC 使用证据

| 项目 | 结果 |
| --- | --- |
| 功能 PNG | 51 张，均在 `1440×900` 浏览器视口下生成 |
| 截图形态 | 40 张精确视口图；11 张为允许的 full-page 长页图 |
| 数据要求 | 正向 PASS 来自真实成功状态；负面 PASS 仅记录明确的 fail-closed 状态；普通加载、空壳、Mock 和错误态未计入通过 |
| 最新复核 | UI 生产范围确认、Wiki/Skills/图谱前置条件、定时任务、发布版本链、测试员只读与 Run #5 均视觉通过 |
| 索引 | `batch-60-pc-usage-snapshot-index.md`，PC-B60-0001～PC-B60-0053（含 2 份 CSV 证据） |

A14 当前为部分通过：已完成子功能有证据；知识真实摄取/检索、通知、外部集成、真机和其他阻塞功能不得用普通空态截图替代。

## 5. 缺陷与修复结果

问题台账共 53 项：P0 4、P1 43、P2 6；本轮新增仓库制品清理关闭项，并将批量删除、历史交互标注和搜索请求修复登记为“已修复待复测”；P0/P1 未关闭或外部阻塞仍决定本批次不得放行。

本轮主要关闭项包括：本地监听 PID 解析、项目上下文刷新、审计持久化/导出、接口数值断言、评审 wildcard 权限、脑图全屏、缺陷流转、报告统计、音视频异步语义、性能移动标签、移动缺陷表格 a11y、主题脚本稳定性、定时任务 RBAC、发布包权限、UI 自动化错误态/制品鉴权（`B60-P1-035`）、默认输出/部署 URL（`B60-P1-007`）、非法项目门禁、知识 Skills/图谱/Wiki 前置条件、Agent 假可用、通知假成功、Runner 假健康/Windows 编码/管道死锁和 React 挂载竞态，以及本轮仓库 SQLite/备份制品清理（`B60-P1-015`）。本轮另完成 API 生产权限/跨项目环境、批量删除确认、历史交互标注恢复和搜索提交态修复，均保留“已修复待复测”。UI 自动化直触发的生产双门禁也已完成，但 B60-P0-004 因其他入口未覆盖仍仅部分关闭。

仍影响放行的重点问题：

- `B60-P0-004`：UI 自动化直触发已具备 PROD 标识、专门权限和 `confirm_prod`；ApiDebugPanel、发布包回归和双向集成等入口仍未统一。
- `B60-P1-012/013`：体育业务脚本仍有无数据 skip/弱断言，生产冒烟不能替代业务 E2E。
- `B60-P1-019`：接口测试五入口的环境、变量与生产保护尚未统一；单条 API 路由的生产权限与跨项目环境校验已补测试，但不能代表五入口闭环。
- `B60-P1-023`：体育 UI 自动化供应链存在 7 high 漏洞。
- `B60-P2-006`：知识中心标签在 1440×900 仍需横向滚动，桌面信息密度有优化空间。

## 6. 质量门禁结果

| 门禁 | 命令/范围 | 结果 |
| --- | --- | --- |
| 后端 F821 | Ruff 0.15.22 `check app --select F821` | PASS；0 错误。项目 venv 未安装 Ruff，使用机器锁定工具执行 |
| 后端 Playwright Executor | `pytest tests/test_playwright_executor.py -q` | PASS；24 passed |
| 后端 Agent/Knowledge | Agent/Knowledge/Skills/Graph 定向回归 | PASS；无 AI、无片段和编排器失败均 fail-closed |
| 后端全量 | `pytest tests -q` | PASS；946 collected，943 passed，0 failed，3 skipped，3 warnings；skip 均为 PostgreSQL 并发环境用例 |
| 前端全量 | `npm test -- --run` | PASS；73/73 文件、272/272 测试通过 |
| 前端类型 | `npm run typecheck` | PASS；无诊断 |
| 前端构建 | `npm run build` | PASS；Vite 生产构建完成，3415 modules |
| 体育自动化安全 | `npm run test:security` | PASS；6/6，包括无默认账号、凭据不进入 AI 指令、深层流量脱敏和会话隔离 |
| 体育自动化类型 | `npm run typecheck` | PASS |
| 前端生产依赖 | `npm audit --omit=dev` | PASS；0 vulnerability |
| 体育自动化生产依赖 | `npm audit --omit=dev` | FAIL；4 low、9 moderate、7 high、0 critical；`npm audit fix --force` 需要 breaking 的 `@midscene/web@1.10.8` |
| 后端依赖审计 | `pip-audit -r requirements.txt` | INCOMPLETE；已在忽略的 Batch 60 venv 安装工具，UTF-8 重试访问 advisory 服务约 184 秒后超时，未取得可签署的干净审计结果 |
| 补丁卫生 | `git diff --check` | PASS；无空白错误 |

本轮收尾修复新增行为测试并通过：`test_batch60_api_production_guard.py`（2 条）、用例批量删除确认（1 条）、`InteractionAnnotator.test.tsx`（2 条）和测试计划/报告的 committed keyword 请求修复；同时从版本控制移除 SQLite/`.bak` 制品并补充忽略规则。全量测试绿色仍不能覆盖外部阻塞、真实旧库、浏览器 a11y 或供应链 high 风险，因此 A11 仍不通过。

## 7. A01–A14 判定

| 门禁 | 判定 | 依据/缺口 |
| --- | --- | --- |
| A01 基线可追溯 | PARTIAL | 起始 SHA、分支、矩阵和数据清单已固定；本地交付提交不等于已 push/PR，远端审计仍待授权 |
| A02 隔离环境 | PASS | worktree、端口、SQLite 独立且健康；实际监听 PID 解析、manifest 和 worktree 归属校验已通过 |
| A03 功能正负面 | NEEDS WORK | 多模块仍为部分通过、阻塞或未执行 |
| A04 API 三类校验 | PARTIAL | 本地接口入参/业务/返回链已验证；Test5 当前契约、生产白名单和写副作用不足 |
| A05 RBAC/项目隔离 | PARTIAL | 项目切换、用例、定时任务、发布包已复核；全模块三身份矩阵未完成 |
| A06 UI/API/DB/审计一致 | PARTIAL | 计划/缺陷/报告/审计等闭环通过；外部写链未执行 |
| A07 幂等/并发/重试 | PARTIAL | 音视频幂等、Runner 超时/取消服务回归通过；全模块浏览器并发不足 |
| A08 跨页查询 | NOT COMPLETE | 未完成全部列表的多页、排序、筛选与 count 同源验证 |
| A09 浏览器/响应式/a11y/网络 | NOT COMPLETE | 移动缺陷表格键盘滚动和主题定位器缺陷已关闭；其余模块的平板/移动、键盘、焦点和网络矩阵仍未全覆盖 |
| A10 真实旧库迁移 | BLOCKED | 缺脱敏旧 PostgreSQL 快照；空库/SQLite 不能替代 |
| A11 自动化/供应链 | FAIL | 双端全量通过，但体育自动化仍有 7 high；后端 pip-audit 因 advisory 服务超时未取得完整结果 |
| A12 文档/证据一致 | PARTIAL | 矩阵、问题、数据、快照、专项与本报告已同步；仍有历史 PRD/能力漂移 |
| A13 运维发布与同制品晋级 | DEFERRED | ADR-0015 和架构要求已记录；统一发布控制面、test→production 同 digest 晋级尚未建设 |
| A14 PC 快照完整性 | PARTIAL | 已索引 51 张真实正向/负面功能 PNG；阻塞/未执行功能仍缺有效快照 |

## 8. 外部阻塞与解除条件

| 阻塞 | 解除条件 |
| --- | --- |
| Test5 六服务、用户端和运营后台 | 明确授权 OpenVPN 切换；提供六份当前契约、最小权限账号、稳定数据和清理规则 |
| AI/蓝湖/OCR | 提供独立非生产 Key/账号、允许处理的数据范围、费用与隐私授权 |
| SMTP/Webhook/Jira/TAPD/ELK | 提供非生产端点、最小权限凭据、接收/清理规则和证据脱敏要求 |
| 真机性能 | 提供 SoloX、ADB/tidevice、授权设备、包名和采集窗口 |
| 真实旧 PostgreSQL | 提供可恢复的脱敏旧库快照、来源版本和升级前后数据断言 |

## 9. 发布建议

1. 保持 production 发布 `DEFERRED`，不得把本地 Runner 结果表述为体育生产业务 E2E 通过。
2. 先关闭生产误触发、接口五入口一致性、关键 skip/弱断言和供应链 high 风险。
3. 取得 R2 条件后先执行只读 API、鉴权负面和首页/列表/详情 E2E，再单独审批支付/退币/赠送写链。
4. 补真实旧 PostgreSQL 升级、全模块三身份隔离、跨页/并发/a11y 和后端依赖审计。
5. 所有 P0/P1、A01–A14 和外部关键链路均有证据后，才能重新判定 `READY` 或 `CONDITIONAL`。
