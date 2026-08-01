# Batch 60 PC 端功能使用快照索引

## 1. 用途与判定规则

本索引用于甲方按功能查看测试平台的真实使用状态。统一快照目录：

`work-logs/evidence/batch-60-sports-platform-validation/pc-usage-snapshots/`

- 视口统一为 `1440×900`；需要展示长列表或详情时允许 full-page，但浏览器视口不变。
- 文件名格式：`<功能点ID>-<序号>-<动作>-PASS.png`。
- 每张通过快照必须来自实际成功操作，能看到真实体育数据、持久化结果、执行输出、审计或可核对的成功反馈。
- 同一张图可证明紧密相关的连续步骤，但必须在索引中逐项说明；只有路由外壳、加载态、空态、Mock、错误页或静态摆拍不计为功能通过。
- 密码、Token、Cookie、Secret、连接串、私钥和非必要个人信息必须在截图前隐藏；若无法安全隐藏则不截图，并将功能标记为待补证据。
- 外部条件不足、功能失败或仅 API 可用的能力保留 `BLOCKED`、`FAIL` 或 `API-ONLY`，不得用图片伪装正常使用。

## 2. 快照状态

已生成 22 个真实后端 PC 顶级页面基线图，位于 `pc-usage-snapshots/route-baseline/`。这些图片用于甲方预览整体页面，但不计为功能操作 `PASS`；功能通过仍以本表和第 3 节的具体动作快照为准。

| 功能点 | 模块 | 应展示的正常使用状态 | 数据 | 快照 | 状态 |
| --- | --- | --- | --- | --- | --- |
| FP-AUTH-001 | 登录鉴权 | 登录成功、会话恢复、登出 | 本地隔离账号 | `FP-AUTH-001-01-expired-session-recovery-PASS.png`、`FP-AUTH-001-02-logout-route-guard-PASS.png` | PARTIAL PASS |
| FP-WB-001 | 工作台 | 体育项目真实统计与时间筛选 | R1 闭环数据 | `FP-WB-001-01-r1-summary-range-PASS.png` | PARTIAL PASS |
| FP-TRACE-001 | 质量追溯 | 需求—用例—执行—缺陷下钻 | R1 闭环数据 | `FP-TRACE-001-01-r1-quality-overview-PASS.png` | PARTIAL PASS |
| FP-REQ-001 | 需求管理 | 上传、拆分、评审、导入、覆盖率 | R1 体育需求 | `FP-REQ-001-01-r1-document-preview-PASS.png` | PARTIAL / AI BLOCKED |
| FP-REL-001 | 发布包 | 版本、差异、全景、交互标注、回归范围 | R1 蓝湖快照 | `FP-REL-001-01-r1-version-chain-PASS.png`、`FP-REL-001-02-tester-readonly-PASS.png` | PARTIAL PASS |
| FP-KNOW-001 | 知识中心 | 摄取、检索、审核、图谱、Wiki | R1 体育文档 | `FP-KNOW-001-01-skills-fail-closed-PASS.png`、`FP-KNOW-001-02-graph-no-source-PASS.png`、`FP-KNOW-001-03-wiki-no-active-bundle-PASS.png` | PARTIAL PASS；真实摄取/检索与 AI BLOCKED |
| FP-MIND-001 | 用例脑图 | 真实用例层级、筛选、全屏 | R1 体育用例 | `FP-MIND-001-01-r1-api-hierarchy-PASS.png`、`FP-MIND-001-02-r1-fullscreen-PASS.png` | PARTIAL PASS |
| FP-CASE-001 | 用例服务 | 导入、CRUD、评审、版本、导出 | R1 体育用例 | `FP-CASE-001-01-r1-sports-search-PASS.png`、`FP-CASE-001-02-batch-priority-review-PASS.png`、`FP-CASE-001-03-version-history-PASS.png` | PARTIAL PASS |
| FP-PLAN-001 | 测试计划 | 计划编排、执行、历史、失败分诊 | R1 体育用例 | `FP-PLAN-001-01-r1-plan-cases-PASS.png`、`FP-PLAN-001-02-execution-history-PASS.png`、`FP-PLAN-001-03-rule-triage-PASS.png` | PARTIAL PASS |
| FP-API-001 | API 测试 | 契约导入、资产、调试、用例、任务、快照 | R1 体育 OpenAPI | `FP-API-001-01-openapi-import-PASS.png`、`FP-API-001-02-generated-cases-PASS.png`、`FP-API-001-03-local-health-debug-PASS.png` | PARTIAL PASS |
| FP-UI-001 | UI 自动化 | 真实 Playwright 运行和截图/Trace/报告 | 本地真实页面 | `FP-UI-001-01-local-playwright-run-PASS.png` 至 `FP-UI-001-04-production-guard-PASS.png` | PARTIAL PASS；生产体育 E2E BLOCKED |
| FP-AV-001 | 音视频专项 | 真实探测运行态、终态和指标 | R1 仓库媒体 | `FP-AV-001-01-r1-real-media-probe-PASS.png` | PARTIAL PASS；实时流 BLOCKED |
| FP-SCH-001 | 定时任务 | Cron 配置、触发和运行历史 | 本地真实计划 | `FP-SCH-001-01-disabled-schedule-PASS.png`、`FP-SCH-001-02-tester-readonly-PASS.png` | PARTIAL PASS |
| FP-REP-001 | 报告中心 | 报告详情、趋势、门禁和导出 | R1 闭环数据 | `FP-REP-001-01-r1-report-list-PASS.png`、`FP-REP-001-02-detail-gate-PASS.png`；`report/FP-REP-001-r1-plan.csv` | PARTIAL PASS |
| FP-SYS-001 | 系统管理 | 用户、角色、权限、审计和导出 | 本地身份矩阵 | `FP-SYS-001-01-roles-PASS.png`、`FP-SYS-001-02-users-PASS.png`、`FP-SYS-001-03-audit-PASS.png`、`FP-SYS-001-04-readonly-role-PASS.png`；`system/FP-SYS-001-audit-user-create.csv` | PASS |
| FP-PROJ-001 | 项目管理 | 项目/成员/主题/门禁及安全切换 | 本地 A/B 项目 | `FP-PROJ-001-01-project-switch-PASS.png`、`FP-PROJ-001-02-project-quality-gate-PASS.png`、`FP-PROJ-001-03-project-members-PASS.png` | PARTIAL PASS |
| FP-DEF-001 | 缺陷管理 | 缺陷详情、评论、附件、状态历史和同步 | R1 闭环数据 | `FP-DEF-001-01-deeplink-closed-PASS.png`、`FP-DEF-001-02-comment-PASS.png`、`FP-DEF-001-03-r1-attachment-PASS.png`、`FP-DEF-001-04-status-history-PASS.png` | PARTIAL PASS |
| FP-DATA-001 | 测试数据集 | JSON/CSV 导入、详情、编辑和绑定 | R1 体育数据 | `pc-usage-snapshots/FP-DATA-001-01-sports-dataset-list-PASS.png`、`FP-DATA-001-02-sports-dataset-detail-PASS.png` | PARTIAL PASS |
| FP-INT-001 | 集成配置 | 配置、连接、同步和日志 | R2 测试集成 | `pc-usage-snapshots/FP-INT-001-01-integration-config-PARTIAL.png` | PARTIAL PASS / R2 BLOCKED |
| FP-AGENT-001 | Agent 工作台 | 触发、队列、结果、统计和取消 | 本地 Provider | 待补 | NOT RUN |
| FP-PERF-001 | 性能监控 | 真机采集、实时指标、停止、报告和对比 | 授权真机 | 待补 | BLOCKED |
| FP-NOTIFY-001 | 通知配置 | 渠道、订阅、测试发送和结果 | R2 接收端 | 待补 | BLOCKED |
| FP-ENV-001 | 环境与变量 | 环境、加密变量、解析和生产保护 | R1 本地/Test5 地址 | `pc-usage-snapshots/FP-ENV-001-01-environment-variables-PASS.png` | PARTIAL PASS |
| FP-OPEN-001 | Open API / Token | Token、触发、查询、回写和门禁 | 本地 Token | 无前端入口 | API-ONLY |
| FP-PLAY-001 | Playground | 编译、执行、错误与产物 | 本地脚本 | 无前端入口 | API-ONLY |
| FP-THEME-001 | 主题 | 五主题、明暗模式和项目主题 | 本地 UI | `FP-THEME-001-01-cyberpunk-PASS.png` 至 `FP-THEME-001-06-desktop-layout-PASS.png` | PASS（五主题切换、持久化与桌面布局） |
| FP-OPS-001 | 运维发布平台 | Release、环境、审批、发布、回滚和审计 | 未来 test/production | 平台尚未建设 | DEFERRED |

## 3. 已登记快照

| 快照 ID | 功能点 | 操作 | 结果 | 数据来源 | 文件 |
| --- | --- | --- | --- | --- | --- |
| PC-B60-0001 | FP-PROJ-001 | 项目 A 需求页切换到空项目 B，旧数据清空且 B 仅请求一次 | PASS（该子功能） | R1 体育需求 + 本地项目 B | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-PROJ-001-01-project-switch-PASS.png` |
| PC-B60-0002 | FP-ENV-001 | Test5 环境新增/编辑、明文变量、加密变量掩码、空名称拒绝和临时环境删除 | PASS（已执行子功能） | R1 仓库登记 Test5 G3 地址；无真实 Token，故加密值使用明确标记的本地 M 数据 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-ENV-001-01-environment-variables-PASS.png` |
| PC-B60-0003 | FP-DATA-001 | 创建并编辑 5 行 Test5 六服务安全用例 JSON 数据集，删除临时记录 | PASS（已执行子功能） | R1 `tests/api-testing/cases/Test5-六服务增改查用例.md` | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-DATA-001-01-sports-dataset-list-PASS.png` |
| PC-B60-0004 | FP-DATA-001 | 打开数据集详情并核对 5 条真实用例编号、服务、方法和路径 | PASS（已执行子功能） | 同上；未包含 Token/Cookie/密码 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-DATA-001-02-sports-dataset-detail-PASS.png` |
| PC-B60-0005 | FP-INT-001 | Jira 配置新增、名称留空凭据编辑、坏 URL 零请求拒绝和临时配置删除 | PARTIAL PASS；外部连接/同步未执行 | 无 Jira/TAPD 测试端点，使用 `.invalid` 与本地 M 凭据验证存储；DB 仅输出保留布尔值 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-INT-001-01-integration-config-PARTIAL.png` |
| PC-B60-0006 | FP-PROJ-001 | 项目编辑、95%/P0=0/P1=3 门禁保存、新增项目选择器同步与停用历史保留 | PASS（已执行子功能） | 本地 A/B 项目与隔离账号 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-PROJ-001-02-project-quality-gate-PASS.png` |
| PC-B60-0007 | FP-PROJ-001 | 为项目 B 添加/更新 tester 为“测试人员”角色并回读成员列表 | PASS（已执行子功能） | 本地种子 tester/测试人员角色 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-PROJ-001-03-project-members-PASS.png` |
| PC-B60-0008 | FP-SYS-001 | 创建并回读 `batch60_readonly` 只读角色，确认本项目数据范围与 9 个只读权限 | PASS | 本地身份矩阵 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-SYS-001-01-roles-PASS.png` |
| PC-B60-0009 | FP-SYS-001 | 回读管理员、测试人员和甲方只读验收用户的启用状态与角色绑定 | PASS | 本地隔离账号 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-SYS-001-02-users-PASS.png` |
| PC-B60-0010 | FP-SYS-001 | 在请求会话结束后查询两条临时用户创建审计，操作人、动作、目标、详情和 IP 均持久化 | PASS | 本地真实后端审计记录 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-SYS-001-03-audit-PASS.png` |
| PC-B60-0011 | FP-SYS-001 | 只读账号登录项目 B，侧栏和用例页写入口按权限收敛，用例数量回读当前项目真实值 0/0 | PASS | 本地只读角色与空项目 B | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-SYS-001-04-readonly-role-PASS.png` |
| PC-B60-0012 | FP-SYS-001 | 使用 httpOnly Cookie 会话和当前项目头导出两条 `user:create` 审计 CSV，并与审计页逐字段核对 | PASS | 本地真实后端审计记录 | `evidence/batch-60-sports-platform-validation/system/FP-SYS-001-audit-user-create.csv` |
| PC-B60-0013 | FP-API-001 | 导入仓库 R1 CamelTv OpenAPI，持久化 5 个体育接口资产并按服务回读 | PASS（已执行子功能） | R1 `test-platform/tests/api-testing/specs/cameltv-openapi.yaml` | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-API-001-01-openapi-import-PASS.png` |
| PC-B60-0014 | FP-API-001 | 从 5 个接口资产生成并按端点分组回读 7 条接口用例 | PASS（已执行子功能） | 同一 R1 OpenAPI；未外呼生产写接口 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-API-001-02-generated-cases-PASS.png` |
| PC-B60-0015 | FP-API-001 | 选择本地真实开发环境调用 `/health`，HTTP 200、响应体、请求/响应快照及 `status_code = 200` 断言全部通过 | PASS（已执行子功能） | 本地 Batch 60 FastAPI 真实健康接口 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-API-001-03-local-health-debug-PASS.png` |
| PC-B60-0016 | FP-CASE-001 | 在 7 条 R1 API 用例中按“首页赛事数据”筛选并回读 2 条真实用例 | PASS（已执行子功能） | R1 CamelTv OpenAPI 生成用例 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-CASE-001-01-r1-sports-search-PASS.png` |
| PC-B60-0017 | FP-CASE-001 | 批量设置目标体育用例为 P0，并完成提交评审与超级管理员通过评审 | PASS（已执行子功能） | 同一 R1 用例；UI/API/SQLite 持久化回读 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-CASE-001-02-batch-priority-review-PASS.png` |
| PC-B60-0018 | FP-CASE-001 | 打开目标体育用例版本历史并回读优先级变更快照 | PASS（已执行子功能） | 同一 R1 用例版本记录 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-CASE-001-03-version-history-PASS.png` |
| PC-B60-0019 | FP-MIND-001 | 按“接口测试”域筛选并回读 7 条真实用例的脑图根层级 | PASS（仅筛选/正常视图）；全屏失败不计入本图 | R1 CamelTv OpenAPI 生成用例 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-MIND-001-01-r1-api-hierarchy-PASS.png` |
| PC-B60-0020 | FP-WB-001 | 回读 7 条总用例、7 条 API 用例，切换近 30 天后仅产生 1 次有效统计 GET | PASS（已执行子功能） | R1 CamelTv OpenAPI 生成用例 + 本地真实统计接口 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-WB-001-01-r1-summary-range-PASS.png` |
| PC-B60-0021 | FP-MIND-001 | 全屏展开域、Ads/Auth/Client/Sports 四模块和 7 条真实接口用例，13 个节点均位于 SVG 视口内；点击卡片内退出按钮恢复正常视图 | PASS（已执行子功能） | R1 CamelTv OpenAPI 生成用例 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-MIND-001-02-r1-fullscreen-PASS.png` |
| PC-B60-0022 | FP-PLAN-001 | 新建 R1 接口回归计划并关联 7 条 OpenAPI 生成用例 | PASS（已执行子功能） | R1 CamelTv OpenAPI 生成用例 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-PLAN-001-01-r1-plan-cases-PASS.png` |
| PC-B60-0023 | FP-PLAN-001 | 人工记录 1 条通过、1 条失败并回读执行历史、备注、统计与 14% 通过率 | PASS（已执行子功能） | 本地真实计划；失败备注仅驱动本地分诊，不外呼生产 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-PLAN-001-02-execution-history-PASS.png` |
| PC-B60-0024 | FP-PLAN-001 | 对失败执行运行本地规则分诊，分类为 Bug、置信度 90%，生成缺陷草稿 | PASS（已执行子功能） | 本地 rule-only 分诊，无 AI/Mock | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-PLAN-001-03-rule-triage-PASS.png` |
| PC-B60-0025 | FP-DEF-001 | 从 `/defect/1` 深链打开一键分诊创建的 P0 缺陷，并完成四段合法状态流转至已关闭 | PASS（已执行子功能） | R1 计划失败执行与真实缺陷记录 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-DEF-001-01-deeplink-closed-PASS.png` |
| PC-B60-0026 | FP-DEF-001 | 在缺陷详情添加并回读体育接口验收评论 | PASS（已执行子功能） | 本地真实缺陷 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-DEF-001-02-comment-PASS.png` |
| PC-B60-0027 | FP-DEF-001 | 上传并回读 4.2 KB 仓库 R1 `cameltv-openapi.yaml` 证据附件 | PASS（已执行子功能） | R1 CamelTv OpenAPI 文件 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-DEF-001-03-r1-attachment-PASS.png` |
| PC-B60-0028 | FP-DEF-001 | 回读 open→confirmed→fixing→pending_review→closed 四段操作人、时间和备注历史 | PASS（已执行子功能） | 本地真实缺陷流转记录 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-DEF-001-04-status-history-PASS.png` |
| PC-B60-0029 | FP-REP-001 | 报告列表回读 1 份 R1 计划报告、14.3% 趋势与缺陷收敛统计 | PASS（已执行子功能） | R1 计划执行与缺陷快照 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-REP-001-01-r1-report-list-PASS.png` |
| PC-B60-0030 | FP-REP-001 | 报告详情回读 7/1 pass/1 fail/5 pending、14% 通过率和 warn 质量门禁 | PASS（已执行子功能） | 同一真实计划快照 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-REP-001-02-detail-gate-PASS.png` |
| PC-B60-0031 | FP-REP-001 | 从 UI CSV 菜单生成真实导出 URL，并以同一 Cookie/项目上下文回读 923-byte CSV 体育用例明细 | PASS（已执行子功能） | 同一真实报告 | `evidence/batch-60-sports-platform-validation/report/FP-REP-001-r1-plan.csv` |
| PC-B60-0032 | FP-REQ-001 | 打开并展开仓库 R1 `batch60-天声猜猜猜-真实需求` Markdown 完整内容，回读 parsed 状态 | PASS（预览子功能） | `产品需求/产品需求-天声猜猜猜-20260617_145800.md` 的本地上传记录 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-REQ-001-01-r1-document-preview-PASS.png` |
| PC-B60-0033 | FP-TRACE-001 | 回读 7 用例、7 入计划、2 执行、1 通过、1 缺陷、接口域分布及 0/1 需求断链 | PASS（概览/断链识别子功能） | R1 需求、接口用例、计划、缺陷和报告闭环 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-TRACE-001-01-r1-quality-overview-PASS.png` |
| PC-B60-0034 | FP-AUTH-001 | 会话过期后回登录页并使用真实本地账号恢复工作台会话 | PASS（已执行子功能） | 本地隔离账号；截图不含密码/Cookie | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-AUTH-001-01-expired-session-recovery-PASS.png` |
| PC-B60-0035 | FP-AUTH-001 | 登出后访问 `/special` 受保护路由，稳定重定向到完整登录页 | PASS（已执行子功能） | 本地隔离账号 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-AUTH-001-02-logout-route-guard-PASS.png` |
| PC-B60-0036 | FP-THEME-001 | 切换并回读 Cyberpunk 主题 | PASS（主题子功能） | 本地 UI | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-THEME-001-01-cyberpunk-PASS.png` |
| PC-B60-0037 | FP-THEME-001 | 切换并回读 Apple 主题 | PASS（主题子功能） | 本地 UI | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-THEME-001-02-apple-PASS.png` |
| PC-B60-0038 | FP-THEME-001 | 切换并回读 Clay 主题 | PASS（主题子功能） | 本地 UI | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-THEME-001-03-clay-PASS.png` |
| PC-B60-0039 | FP-THEME-001 | 切换并回读 XLab 主题 | PASS（主题子功能） | 本地 UI | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-THEME-001-04-xlab-PASS.png` |
| PC-B60-0040 | FP-THEME-001 | 切换并回读 Liquid Glass 主题 | PASS（主题子功能） | 本地 UI | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-THEME-001-05-liquid-glass-PASS.png` |
| PC-B60-0041 | FP-THEME-001 | 1440×900 桌面布局、侧栏和顶部项目区完整显示 | PASS（桌面布局子功能） | 本地 UI | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-THEME-001-06-desktop-layout-PASS.png` |
| PC-B60-0042 | FP-AV-001 | 对仓库真实 MP4 执行 HTTP ffprobe，等待终态并回读 6 项真实指标 | PASS（真实媒体探测子功能） | R1 `tests/音视频项目测试/materials/av_sync_test.mp4` | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-AV-001-01-r1-real-media-probe-PASS.png` |
| PC-B60-0043 | FP-REL-001 | 回读 R1 体育原型冻结版→生产验收基线两级发布版本链 | PASS（版本链子功能） | R1 原型快照 + 固定代码基线 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-REL-001-01-r1-version-chain-PASS.png` |
| PC-B60-0044 | FP-REL-001 | 测试员查看同一发布链，新建和删除入口均不可见 | PASS（低权限只读子功能） | 本地测试员角色 + R1 版本链 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-REL-001-02-tester-readonly-PASS.png` |
| PC-B60-0045 | FP-SCH-001 | 管理员回读绑定 R1 计划、保持禁用的周回归 Cron 任务 | PASS（创建/回读子功能；未触发） | 本地 R1 接口计划 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-SCH-001-01-disabled-schedule-PASS.png` |
| PC-B60-0046 | FP-SCH-001 | 测试员查看真实 Cron 任务，新建/触发/编辑/删除入口均不可见 | PASS（低权限只读子功能） | 本地测试员角色 + R1 计划 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-SCH-001-02-tester-readonly-PASS.png` |
| PC-B60-0047 | FP-UI-001 | 测试平台内回读真实 Playwright Job，最新状态为“已完成” | PASS（任务执行列表子功能） | 本地 Chrome + 仓库 locator 脚本 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-UI-001-01-local-playwright-run-PASS.png` |
| PC-B60-0048 | FP-UI-001 | 打开 Run #5 详情，回读 5/4/0/1、5 个产物并通过鉴权 Blob 加载 3 张真实截图 | PASS（结果/制品子功能） | 本地真实 Run #5；1 条授权登录用例明确 skip | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-UI-001-02-run-detail-artifacts-PASS.png` |
| PC-B60-0049 | FP-UI-001 | 打开 Run #5 后自动激活 stdout，直接回读真实中文 Playwright 执行输出 | PASS（默认输出子功能） | 本地真实 Run #5 stdout；无凭据内容 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-UI-001-03-default-stdout-PASS.png` |
| PC-B60-0050 | FP-KNOW-001 | 无 AI 服务时回读 0/6 个能力可用，6 个 Skills 卡片均明确显示“暂不可用”并禁止执行 | PASS（负面前置条件子功能） | 本地真实配置状态；不读取或展示 Key | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-KNOW-001-01-skills-fail-closed-PASS.png` |
| PC-B60-0051 | FP-KNOW-001 | 当前项目无有效知识片段时图谱页显示缺失条件，并禁用“触发实体提取” | PASS（负面前置条件子功能） | 本地真实知识源/分块状态，均为 0 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-KNOW-001-02-graph-no-source-PASS.png` |
| PC-B60-0052 | FP-UI-001 | 生产标记任务显示 PROD、目标环境/地址/脚本范围；无 `confirm_prod` 的 API 请求返回 400 且运行记录保持 0 | PASS（生产保护负面子功能；未实际访问生产） | `.invalid` 明确标记的临时 M 环境；验证后任务和环境均删除 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-UI-001-04-production-guard-PASS.png` |
| PC-B60-0053 | FP-KNOW-001 | Wiki 未启用或缺少可同步 active 发布包时显示明确前置条件、禁用同步并提供发布包管理入口 | PASS（负面前置条件子功能） | 本地真实 Wiki 配置和两条 draft 发布包 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-KNOW-001-03-wiki-no-active-bundle-PASS.png` |

当前 A14 状态：`部分通过`。现有 51 张 PNG 均在 `1440×900` 浏览器视口下生成，其中 40 张为精确视口图、11 张为本索引允许的 full-page 长页图；正向成功状态和明确的负面 fail-closed 状态已分别标注并完成视觉复核。阻塞、失败和未执行功能仍不得以普通空态、错误页或 Mock 图片替代，补齐全功能矩阵后才能提交最终甲方验收包。
