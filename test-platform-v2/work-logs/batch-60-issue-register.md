# Batch 60 全平台问题台账

## 1. 状态定义

| 状态 | 定义 |
| --- | --- |
| 已复现 | 已在 Batch 60 独立环境观察到可重复实际结果 |
| 静态确认 | 代码路径确定存在，但业务影响仍需浏览器/API/DB 动态验证 |
| 待复现 | 高风险假设，尚未取得足够运行证据 |
| 阻塞 | 缺外部环境、权限、设备、契约或数据；已写明解除条件 |
| 已修复待复测 | 已有修复，但缺完整受影响回归 |
| 已关闭 | 修复、历史失败和受影响闭环均通过 |

严重程度使用 P0/P1/P2/P3；P0/P1 未关闭或关键外部链路阻塞时，Batch 60 结论不得高于 `NEEDS WORK`。

## 2. 当前问题

| ID | 级别 | 模块 | 状态 | 问题 | 影响 | 证据/位置 | 下一步验证或修复 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B60-P0-001 | P0 | 体育 UI 自动化 / 凭据安全 | 已修复待复测 | `auth.ts` 将用户名和密码插入 Midscene 自然语言指令；真实凭据可能发送给外部多模态模型 | 凭据外发，违反真实数据和证据安全门禁 | `tests/automation/ui/utils/auth.ts`；`tests/automation/ui/tests/security/security-utils.spec.ts` | 已改为本地 Playwright locator 填写并移除默认账号；安全契约 3 项通过。需在获授权 Test5 会话中完成真实登录复测后关闭 |
| B60-P0-002 | P0 | 体育 UI 自动化 / 流量证据 | 已修复待复测 | 流量捕获原样保存 URL、query、body、headers 和 response，未脱敏 Authorization、Cookie、access token、password、token | 运行真实体育数据时可能把凭据和个人信息写入报告或 Git | `tests/automation/ui/utils/traffic-capture.ts`；`tests/automation/ui/tests/security/security-utils.spec.ts` | URL/basic auth/query/header/body/response 递归脱敏、未知原始 body fail-closed、会话隔离均已通过红队测试；需在授权 Test5 真实流量中复核生成文件后关闭 |
| B60-P0-003 | P0 | 多项目隔离 | 已修复待复测 | 从项目 A 需求页切到项目 B 后自动需求 GET 为 0，A 的真实体育需求仍显示；点击删除时请求已使用 B 上下文并返回业务 404 | 用户看到 A 数据却对 B 发写请求；当前后端隔离阻止误删，但所有编辑/批量/任务入口都有上下文错位风险 | `frontend/src/layouts/ProjectScopeBoundary.tsx`；`frontend/src/layouts/MainLayout.tsx`；`work-logs/evidence/batch-60-sports-platform-validation/project-isolation/` | 回归测试和需求页 A→B 真实浏览器复测已通过：B 列表仅 GET 1 次、A 陈旧行 0；继续扩展到 testcase/testplan/report/defect/trace/environment/dataset/integration/uitest 后关闭 |
| B60-P1-001 | P1 | 本地环境脚本 | 已关闭 | Windows 虚拟环境启动后，脚本原先记录父/启动 PID，但实际监听的是另一个 Python PID，健康服务会被 `status` 误报 | 用户误判本地环境失败，无法可靠复用/监控服务 | `scripts/start-platform-environment.ps1`、`scripts/test-start-platform-environment.ps1` | 启动后解析唯一真实监听 PID并校验严格 worktree 路径边界；旧 manifest 可在内存安全校正，外部/多监听器拒绝。隔离 PowerShell 回归与当前 5196/8026 status 均通过，manifest 已记录新后端 PID |
| B60-P1-002 | P1 | 导航 / 信息架构 | 静态确认 | 发布包、缺陷、数据集、集成被主动隐藏；通知、环境无菜单权限定义；命令面板也漏多个页面 | “全平台”功能对用户不可发现，易产生未验收/未使用的功能孤岛 | `frontend/src/layouts/MainLayout.tsx:237`；`backend/app/seed.py:17`；`frontend/src/components/CommandPalette.tsx:26` | 逐模块确认成熟度；生产可用模块恢复菜单/命令入口，未完成模块明确显示状态而非静默隐藏 |
| B60-P1-003 | P1 | 失败分诊 / 缺陷闭环 | 已关闭 | 创建缺陷后跳转 `/defect/{id}`，路由仅定义 `/defect`，最终进入通配占位页 | 测试执行失败无法继续缺陷详情、状态流转和关闭闭环 | `frontend/src/router/index.tsx`、`pages/defect/index.tsx`、`pages/defect/__tests__/DefectDeepLink.test.tsx`；`issues/B60-P1-003-triage-defect-route-FAIL.png` | 真实计划分诊创建缺陷后稳定复现占位页；新增项目域内详情深链并自动打开既有 Sheet。7 条缺陷/脑图相关测试、typecheck 和可见 Chrome `/defect/1` 深链闭环通过 |
| B60-P0-004 | P0 | 生产环境保护 | 部分关闭 | API DebugTab 已有生产确认；UI 自动化直触发原先缺专门权限、目标展示和二次确认；ApiDebugPanel quick execute、发布包回归触发与双向集成同步仍未统一 | 未关闭入口仍可能在目标/范围不清楚时执行写请求、回归或双向同步 | `backend/app/services/ui_test_service.py`、`api/v1/ui_test.py`、`frontend/src/pages/uitest/index.tsx`；`FP-UI-001-04-production-guard-PASS.png`；本轮补充 `backend/tests/test_batch60_api_production_guard.py`；其余见 `DebugTab.tsx`、`ApiDebugPanel.tsx`、`BundleDetail.tsx`、`pages/integration/index.tsx` | UI 任务列表已显示 PROD/目标环境，后端以 `uitest:trigger_prod + confirm_prod=true` 在建 run 前双门禁并校验环境项目归属，5 条后端、19 条前端相关测试及真实浏览器 400/零 run/范围预览通过；本轮单条 API 执行已转发超级管理员/通配生产权限，API 任务已拒绝跨项目环境（2 条测试通过）；继续把同一 guard 扩展到剩余入口 |
| B60-P1-005 | P1 | 音视频专项 | 已关闭 | `trigger` 只启动后台线程并置 `running`，前端 await 后立即提示“检测已完成”，且不轮询最终状态 | 对真实流给出假完成反馈，用户可能重复触发并发任务 | `frontend/src/pages/special/index.tsx`；`backend/app/services/av_check_service.py`；`backend/tests/test_av_measurements.py`；`pc-usage-snapshots/FP-AV-001-01-r1-real-media-probe-PASS.png` | running 提示、终态轮询、按钮禁用、重复触发幂等和终态通知均已实现；后端 7 条、前端 4 条测试及真实 MP4 六指标闭环通过 |
| B60-P1-006 | P1 | 用例批量操作 | 已修复待复测 | 批量删除直接执行，无二次确认；单条删除反而有确认 | 多选状态下易造成大范围不可逆删除 | `frontend/src/pages/testcase/index.tsx`、`frontend/src/pages/testcase/index.test.tsx` | 已增加所选数量、当前项目范围和不可逆提示，确认前不发请求；定向测试通过。仍需浏览器复核 DB、审计和失败回滚 |
| B60-P1-007 | P1 | UI 自动化结果 / 部署配置 | 已关闭 | 结果页原先默认落在不可用输出 Tab；报告与 WebSocket 又混用硬编码 `/api/v1` 或当前 host | 诊断输出不可见；物理分离部署下报告或 WebSocket 链接错误 | `pages/uitest/index.tsx`、`api/baseUrl.ts`、`api/report.ts`、`hooks/usePerfWebSocket.ts`；`FP-UI-001-03-default-stdout-PASS.png` | 已按 stdout→stderr→无输出选择首个可用结果页；报告与性能 WS 统一解析 `VITE_API_BASE_URL`/兼容旧配置，同源代理和物理分离均不重复 `/api/v1`；14 条 URL/输出测试、typecheck 与可见 Run #5 通过 |
| B60-P1-008 | P1 | 发布包交互标注 | 已修复待复测 | 解析已保存 `page_interactions` 后无条件 `setRegions([])`；历史标注无法回显、审查或编辑 | 用户只能重复新增，发布包证据和回归范围失真 | `frontend/src/pages/release-bundles/components/InteractionAnnotator.tsx`、`InteractionAnnotator.test.tsx` | 已将历史语义交互恢复为可编辑占位区域，保留已有坐标并为旧数据生成稳定位置；解析回归通过。仍需真实截图保存→重载→编辑浏览器复测，旧语义数据的合成坐标不能替代真实截图定位 |
| B60-P1-009 | P1 | 权限 UX | 部分已修复待复测 | 多数页面对无权限角色仍显示新增、删除、执行等入口，点击后才收到 403；用例服务已按权限隐藏新增、编辑、删除、批量和评审入口 | 误导只读用户、增加失败请求并暴露能力结构 | `frontend/src/pages/testcase/index.tsx`；`pc-usage-snapshots/FP-SYS-001-04-readonly-role-PASS.png`；testplan/requirement/report/schedule/environment/dataset/notify/API 调试页面仍待覆盖 | 保留用例服务前后端双重拒绝；继续以统一权限组件收敛其余模块，并完成三身份矩阵复测 |
| B60-P1-010 | P1 | 前后端能力闭环 | 静态确认 | 用例 Excel/XMind 导入导出、报告模板 CRUD、API Token、改密/重置、playground 等后端/客户端能力缺前端入口；质量追溯无明细下钻 | 文档声称能力与实际用户可操作能力不一致 | `frontend/src/api/testcase.ts`、`reportTemplate.ts`；`backend/app/api/v1/token.py`、`auth.py`、`playground.py`；`pages/trace/index.tsx` | 逐项确定“补 UI / 明确 API-only / 删除死能力”；同步 PRD 和菜单；补行为级测试 |
| B60-P1-011 | P1 | 无障碍 | 静态确认 | 多处 label 未关联输入，图标按钮缺可访问名称，DebugTab aria-label 与控件真实含义相反 | 屏幕阅读器和语音控制无法可靠操作；违反 A09/WCAG AA | `pages/uitest/index.tsx:429`、`pages/report/index.tsx:456`、notify/report/schedule/DefectDetailSheet/AuditTab/DebugTab 已定位点 | 用浏览器+axe+键盘逐页验证；修复 label/aria-label；每个图标按钮提供可感知名称 |
| B60-P1-012 | P1 | 体育 UI 自动化可信度 | 静态确认 | 19 个测试只有 8 个显式断言，7 处无数据直接 skip；测试无预置/清理闭环，也无运营后台脚本 | 可能假绿，无法支持“体育平台已生产验收”结论 | `tests/automation/ui/specs/` | 每条 P0 旅程至少一个结果断言和 API/业务证据；缺数据应建立 fixture 或明确 BLOCKED；补后台主链 |
| B60-P1-013 | P1 | 生产冒烟可信度 | 静态确认 | 生产冒烟计算 `loggedIn` 但不断言；登录错误只截图不失败；API 数量断言恒真；无凭据也可通过 | 生产登录和接口资产未真正工作时仍返回绿灯 | `production-smoke.spec.ts`、`production-web-smoke.spec.ts` | 缺凭据时标记 BLOCKED/失败而非通过；断言登录后会话和真实可见业务元素；移除恒真断言 |
| B60-P1-014 | P1 | 体育自动化命令 | 已关闭 | npm `test:test` / `test:prod` 使用 Playwright 不支持的 `--env=` 参数 | 标准命令不可执行或环境选择失效 | `tests/automation/ui/package.json`；`tests/automation/ui/tests/security/security-utils.spec.ts` | 已使用跨平台 `TEST_ENV` 注入；`npm run test:test -- --list` 与 `npm run test:prod -- --list` 均成功收集 25 条测试 |
| B60-P1-015 | P1 | 仓库卫生 | 已关闭 | 主干跟踪了 SQLite 数据库和 `.bak` 备份文件 | 违反 AGENTS.md 强制提交规则，可能夹带用户/业务数据和不可复现状态 | `.gitignore`；删除 `test-platform-v2/frontend/data/platform.db`、`test-platform-v2/docs/theme-mockup-v3.html.bak`；`git ls-files` hygiene 复核 | 已从版本控制移除并补充数据库、WAL/SHM、备份和临时文件忽略规则；当前变更范围未再包含这两类已知制品 |
| B60-P1-016 | P1 | PRD / 事实源 | 静态确认 | PRD 仍描述 React 18、localStorage JWT、简单缺陷、随机 API/UI/音视频等旧实现；只覆盖 13 个模块 | 测试设计和用户期望基于错误能力边界，A12 不通过 | `docs/现状功能PRD.md`、完整 PRD、`test-platform-v2/CLAUDE.md` 等 | 以代码/路由/OpenAPI为准重建模块清单、成熟度和限制；同步 README/PRD/手册 |
| B60-P1-017 | P1 | 全平台测试资产 | 静态确认 | 正式平台用例索引主要只有需求服务；11 个平台 Playwright spec 中 5 个用 Mock，真实后端套件多为路由壳检查 | 不能证明全部按钮、CRUD、状态机、项目隔离和跨模块闭环 | `test-platform-v2/frontend/e2e/`；`tests/test-cases/` | 建立本文件配套全功能点矩阵并逐条执行；Mock 结果与真实后端证据分开统计 |
| B60-P1-018 | P1 | Jira/TAPD 集成凭据 | 已关闭 | 编辑集成时前端把凭据字段重置为空，保存时仍提交包含空凭据的 `auth_json` | 只修改名称也可能清空原凭据，连接与同步突然失效 | `frontend/src/pages/integration/authPayload.ts`；`backend/app/services/integration_service.py`；`frontend/src/pages/integration/authPayload.test.ts`；`backend/tests/test_batch60_integration_credentials.py`；`work-logs/evidence/batch-60-sports-platform-validation/integration/` | 3 条前端、2 条后端及既有 5 条管理回归通过；真实本地 SQLite 复核 Email/Token/Project Key 均保留，UI 名称编辑和删除确认通过 |
| B60-P1-019 | P1 | API 用例执行一致性 | 静态确认 | 快速、资产、单条、分组、批量五种执行入口对环境选择和生产确认的处理不一致；单条执行可能忽略用户所选环境 | 同一用例从不同入口执行到不同目标，结果不可比较并可能触发生产风险 | `DebugTab.tsx:265`、`ApiDebugPanel.tsx:175`、`ApiCaseTab.tsx:102`、`:119` | 统一执行请求构造器；五入口使用同一环境、变量、保护和结果 schema；用同一 GET/POST 用例做参数化回归 |
| B60-P1-020 | P1 | 强制改密 | 静态确认 | 后端登录结果支持 `must_change_password`，前端类型未声明也未处理，且没有改密/忘记/重置入口 | 管理员重置后的用户可能绕过强制改密或陷入不可完成流程 | `frontend/src/types/index.ts:20`；`backend/app/api/v1/auth.py` | 声明字段并增加受保护改密流程；首次登录必须完成改密后才能访问业务路由；补过期/取消/弱密码用例 |
| B60-P1-021 | P1 | 移动端缺陷表格 / A11y | 已关闭 | 390×844 下缺陷表格横向滚动容器原先不可聚焦、无角色和可访问名称 | 键盘用户无法访问横向隐藏列；Axe `scrollable-region-focusable` serious，A09 阻断 | `components/ui/table.tsx`、`pages/defect/DefectTable.tsx`、`DefectTableAccessibility.test.tsx`；`browser/TC-B60-A09-MOBILE-DEFECT-scroll-region-PASS.png` | 容器已具备 `region`、可访问名称和 `tabIndex=0`；3 文件 5 测试、typecheck 与 390×844 Chrome 键盘 ArrowRight 0→40 回归通过 |
| B60-P1-022 | P1 | 全路由 E2E / 主题实验室 | 已关闭 | 主题实验室验收脚本原先等待已删除文案，且视口套件串行会让单点失败跳过后续移动用例 | 形成测试资产假失败和漏执行 | `frontend/e2e/batch56-full-platform-real-backend.spec.ts` | 定位器改为稳定 `main#theme-lab-workspace`，平板/移动用例取消串行耦合；E2E 列表完整收集 13 项，相关测试、typecheck 和可见移动回归通过 |
| B60-P2-001 | P2 | 查询体验 / 网络 | 已修复待复测 | 测试计划、报告页面 keyword 每次输入即进入请求依赖，同时又提供“搜索”按钮 | 每按键请求一次，产生无效 GET、结果抖动和后端压力 | `pages/testplan/index.tsx`、`pages/report/index.tsx`；前端全量 73 文件/272 测试通过 | 已分离 draft 与 committed keyword，输入变化不再触发请求，搜索按钮/回车后提交一次；类型检查、测试和构建通过。仍需浏览器 Network 逐次确认取消旧请求和每次提交仅一条有效 GET |
| B60-P2-002 | P2 | 响应式 / 触控 | 部分关闭 | 报告详情使用 10 列网格且自定义 820px 宽度被通用 Sheet 的 `data-side` 384px 上限覆盖，1440×900 下统计文本已出现裁切；多处小按钮触控面积仍待移动端审计 | 报告通过/失败/pending 指标不可读，移动端还可能溢出或难以点击 | `pages/report/index.tsx`；`pc-usage-snapshots/FP-REP-001-02-detail-gate-PASS.png` | Sheet 使用同一 `data-[side=right]` 变体覆盖 820px，统计改为移动 2 列/桌面 7 列；PC 复拍无裁切。390×844/768×1024 触控与全局小按钮仍待执行，故保持部分关闭 |
| B60-P1-023 | P1 | 体育 UI 自动化供应链 | 已复现 | `npm audit --omit=dev` 报告 7 high、9 moderate、4 low、0 critical，主要来自 `@midscene/web@0.20.1` 的传递依赖；自动修复要求升级到 1.10.8 | 体育自动化运行环境带有高危依赖，不能作为生产验收绿色供应链证据 | `tests/automation/ui/package-lock.json`；Batch 60 安全子任务审计记录；`npm run test:security -- --list` 收集 6 项，`npm run typecheck` 通过 | 单独评估 Midscene 0.x→1.x 兼容性和迁移；当前 `npm audit fix --force` 会引入 breaking 版本，不能直接自动升级；升级后重跑 25 条收集、安全红队、真实 Test5 只读旅程与 npm audit |
| B60-P1-024 | P1 | 项目管理 / 顶部选择器 | 已关闭 | 项目管理页新增项目后只刷新管理表格，顶部“当前项目”仍使用登录时旧列表，新项目不可选择 | 用户创建项目后无法立即进入，误以为创建失败；停用当前项目也可能保留无效上下文 | `frontend/src/pages/project/index.tsx`；`frontend/src/stores/auth.ts`；`frontend/src/stores/__tests__/auth.test.ts` | CRUD 后重新读取当前用户可见项目；当前项目不可见时回退首个项目。13 条 store 回归、typecheck 和真实浏览器新增后立即出现选项均通过 |
| B60-P1-025 | P1 | 项目停用语义 | 已关闭 | UI 使用“删除/不可撤销/删除关联数据”，后端实际仅把 `status` 改为 0 且管理列表继续保留记录 | 用户误判历史数据已物理删除；审计保留策略与界面表达矛盾 | `frontend/src/pages/project/index.tsx`；`backend/app/services/project_service.py`；`work-logs/evidence/batch-60-sports-platform-validation/project-management/` | UI 改为“停用”，明确从选择器移除但保留历史和审计；真实浏览器确认停用后选择器移除、管理表显示“禁用” |
| B60-P1-026 | P1 | 系统管理 / 审计持久化 | 已关闭 | 请求级数据库会话成功结束时未统一提交，系统服务只 `flush` 的审计记录可能在会话边界被回滚丢失 | 用户/角色等高风险管理动作缺少可追溯审计，无法满足生产合规和事故复盘要求 | `backend/app/core/db.py`；`backend/tests/test_batch60_audit_durability.py`；`work-logs/evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-SYS-001-03-audit-PASS.png` | 成功请求统一 commit、异常统一 rollback；2 条定向测试通过，浏览器审计页与 CSV 均回读到跨请求持久化记录 |
| B60-P1-027 | P1 | 系统管理 / 审计 CSV | 已关闭 | CSV 二进制导出仍读取已废弃的 `localStorage.access_token`，没有携带 httpOnly Cookie 和当前项目头 | Cookie 会话登录正常但审计导出失败，且项目隔离上下文不完整 | `frontend/src/api/system.ts`；`frontend/src/api/__tests__/system.test.ts`；`work-logs/evidence/batch-60-sports-platform-validation/system/FP-SYS-001-audit-user-create.csv` | 导出改为 `credentials: include`，携带当前项目头并仅在内存 Token 存在时兼容 Authorization；定向测试和真实 CSV 导出均通过 |
| B60-P1-028 | P1 | API 测试 / 响应断言 | 已关闭 | 可视化断言编辑器把期望状态码作为字符串提交，后端 `eq/neq` 使用类型严格比较，导致真实 HTTP 200 与字符串 `"200"` 被误判为失败 | 正常接口被标红，批量任务、报告和质量门禁可能产生系统性假失败 | `backend/app/services/api_execution_service.py`；`backend/tests/test_apitest_generation.py`；`pc-usage-snapshots/FP-API-001-03-local-health-debug-PASS.png` | 仅在一侧为数字、另一侧为可解析数字字符串时按数值比较；字符串对字符串和布尔比较保持原语义。修复前测试稳定失败，修复后相关 3 条测试及真实 `/health` 断言通过 |
| B60-P1-029 | P1 | 用例评审 / RBAC | 已关闭 | 评审通过接口直接检查权限字符串，未使用统一 RBAC wildcard 语义，导致拥有 `*` 的超级管理员提交评审后仍被 HTTP 403 拒绝通过 | 超级管理员无法完成用例评审闭环，且 UI 展示可操作入口但后端拒绝 | `backend/app/api/v1/test_case.py`；`backend/tests/test_batch60_review_permissions.py`；`pc-usage-snapshots/FP-CASE-001-02-batch-priority-review-PASS.png` | 路由改用 `rbac_service.has_permission`；红测稳定复现 403，修复后与 API 数值断言定向回归共 2 条通过，真实浏览器提交→通过→回读 `approved` 成功 |
| B60-P1-030 | P1 | 用例脑图 / 全屏与可读性 | 已关闭 | 进入全屏后 Markmap 节点坐标变为视口外（文本 `x=-40,y=89.5`，SVG 顶部 `111.5`），画面空白；顶部“退出全屏”按钮又被 fixed 卡片和 SVG 截获点击；正常视图节点文字与背景对比度也很低 | 用户进入全屏后既看不到体育用例树，也无法用按钮退出，甲方快照无法证明该功能正常 | `frontend/src/pages/mindmap/index.tsx`、`index.test.tsx`、`frontend/src/globals.css`；`pc-usage-snapshots/FP-MIND-001-02-r1-fullscreen-PASS.png` | fit 改为等待下一帧并按实际 SVG 视口执行，退出控件移入 fixed 卡片并支持 Escape，画布文字使用主题 foreground；3 条组件测试、typecheck 通过，可见 Chrome 展开 13 节点均在视口内且按钮真实退出成功 |
| B60-P1-031 | P1 | 缺陷状态流转 | 已关闭 | 状态流转成功后对话框未关闭，最终显示陈旧的“已关闭 → 已关闭”且确认按钮仍在 | 用户误以为流转未完成并可能重复提交，PC 快照无法作为正常状态证据 | `pages/defect/DefectTransitionDialog.tsx`、`pages/defect/__tests__/DefectWorkflow.test.tsx` | 成功回调后清空备注并关闭弹窗；4 条缺陷定向测试、typecheck 及四段真实浏览器流转通过，复拍已无陈旧弹窗 |
| B60-P1-032 | P1 | 报告详情 / 数据契约 | 已关闭 | 后端报告快照持久化 `stats.pass`，前端只读取 `stats.pass_`，导致真实 1 条通过被显示为 0 且通过率错误 | 报告、趋势和甲方快照给出错误质量结论 | `pages/report/index.tsx`、`pages/report/reportStats.test.ts`；`pc-usage-snapshots/FP-REP-001-02-detail-gate-PASS.png` | 优先读取服务端 `pass` 并兼容旧 `pass_`；2 条契约测试、typecheck 和可见 Chrome 7/1/1/5、14% 回读及 CSV 923 bytes 验证通过 |
| B60-P2-003 | P2 | 用例服务 / 统计文案 | 已关闭 | 用例页把“全部/功能用例”数量硬编码为 901/795，不随项目数据变化 | 用户看到与当前项目不一致的数量，只读空项目也显示虚假资产规模 | `frontend/src/pages/testcase/caseListFormatters.ts`；`frontend/src/pages/testcase/index.tsx`；`frontend/src/pages/testcase/__tests__/caseListFormatters.test.ts`；`work-logs/evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-SYS-001-04-readonly-role-PASS.png` | 从当前项目领域聚合全部数量并排除“接口测试”得到功能用例数量；格式化测试通过，空项目浏览器回读 0/0 |
| B60-P2-004 | P2 | 音视频详情 / 协议 | 已关闭 | 通用 Sheet 的 384px 上限覆盖音视频详情宽度，长 URL/指标重叠；协议列表缺 HTTP/HTTPS，真实 MP4 任务只能错误标记为其他协议 | 详情不可读且持久化协议与实际来源不一致 | `frontend/src/pages/special/index.tsx`、`index.test.tsx`；`pc-usage-snapshots/FP-AV-001-01-r1-real-media-probe-PASS.png` | 详情宽度显式覆盖并允许长 URL 换行，新增 HTTP/HTTPS 选项；真实 HTTP 媒体任务复拍无重叠 |
| B60-P2-005 | P2 | 性能监控 / 移动端 | 已关闭 | 390×844 下四个标签超出容器且报告标签不可见/不可点击 | 真机性能功能在常见手机视口无法完整操作 | `frontend/src/pages/perftest/index.tsx`、`__tests__/PerftestAccessibility.test.tsx`；`browser/TC-B60-PERF-MOBILE-TABS-PASS.png` | 移动端改为稳定 2×2、44px 高标签，桌面保持四列；4 条定向测试和真实 390×844 无横向溢出验证通过 |
| B60-P1-033 | P1 | 定时任务 / RBAC 与空状态 | 已关闭 | 测试员菜单可见但缺 `schedule:list`；写入口未按权限收敛，空数据与缺计划提示不符合真实状态 | 低权限用户不可使用可见模块，或看到无权限写操作并产生 403 噪声 | `backend/app/seed.py`、`frontend/src/pages/schedule/index.tsx`、双方定向测试；`FP-SCH-001-02-tester-readonly-PASS.png` | 种子权限与菜单一致，CRUD/触发按权限显示，真实 EmptyState 和中文校验已补齐；测试员浏览器复核四类写入口均为 0、无 5xx |
| B60-P1-034 | P1 | 发布包 / 回归范围授权 | 已关闭 | 回归范围读取未要求知识查看权限，空范围返回不完整对象；列表/详情创建、删除、编辑、差异与 UI 回归触发的权限边界不一致 | 低权限用户可能枚举发布结构或触发不应允许的回归任务 | `backend/app/api/v1/release_bundles.py`、`tests/test_release_bundle_permissions.py`、前端权限测试；`FP-REL-001-02-tester-readonly-PASS.png` | 后端补 `knowledge:view/manage`，UI 触发单独要求 `uitest:trigger`，空范围返回完整契约；后端 3 条、前端 6 条和测试员只读浏览器复核通过 |
| B60-P1-035 | P1 | UI 自动化 / 错误与制品鉴权 | 已关闭 | 列表请求错误/403 被显示为“空数据”，脚本被重复拉取；截图/Trace/报告原始 URL 无法携带 `X-Project-Id` | 用户误判无任务，受保护产物 403，且产生重复 GET | `frontend/src/api/uitest.ts`、`pages/uitest/index.tsx`、14 条定向测试；`FP-UI-001-02-run-detail-artifacts-PASS.png` | 错误态可重试、脚本单一请求，所有产物经 Cookie+项目头获取 Blob 并清理 object URL；Run #5 五个产物接口 200，三张 PNG 均真实加载 |
| B60-P1-036 | P1 | Agent 工作台 / 假可用 | 已关闭 | 无 AI Key/未启用 AI 时仍把 7 类 Agent 显示为可用，触发后才失败 | 用户被诱导执行必失败任务，可能产生无意义队列和假运行记录 | `backend/app/api/v1/agent.py`、`tests/test_knowledge.py`、`frontend/src/pages/agent-workbench/index.tsx`；`browser/TC-B60-AGENT-FAIL-CLOSED-PASS.png` | API 返回可用性与原因，触发在入队前 503；UI 显示“暂不可用”并禁用按钮。Agent API 6 条及可见浏览器负面链路通过 |
| B60-P1-037 | P1 | 通知 / 测试结果语义 | 已关闭 | 渠道测试返回 0 success/0 failed/0 skipped 时前端仍提示成功 | 实际未发送任何消息却给出假成功，验收证据失真 | `frontend/src/pages/notify/notifyResult.ts`、`notifyResult.test.ts` | 仅 sent>0 且 failed=0 才成功；零发送为警告，存在失败或 sent=0 为错误；3 条结果分类测试通过 |
| B60-P1-038 | P1 | UI Runner / 假健康 | 已关闭 | 仅检测全局 `playwright` 命令即可判健康，但实际执行目录缺锁定的 `@playwright/test` | 页面显示可执行，任务启动后才因模块缺失失败 | `backend/app/services/playwright_executor.py`、`tests/test_playwright_executor.py` | 预检改为要求本地锁定依赖，部署目录执行 `npm ci` 并安装 Chromium；专项 24 条通过，Run #5 真实完成 |
| B60-P1-039 | P1 | UI Runner / Windows 编码 | 已关闭 | 子进程按系统 GBK 解码 Playwright UTF-8 中文输出，触发 `UnicodeDecodeError` 后超时 | 中文测试标题使真实任务不可完成 | 同上；失败 Run #2 与成功 Run #5 | 子进程固定 UTF-8 且替换坏字节；编码回归和真实中文 spec 通过 |
| B60-P1-040 | P1 | UI Runner / 输出管道死锁 | 已关闭 | 父进程等待 Playwright 退出后才读取 stdout/stderr，JSON reporter 填满管道后子进程无法退出 | 正常任务被错误判定超时，取消和超时状态不可信 | 同上；失败 Run #3 与成功 Run #5 | 启动后立即由后台线程排空输出，同时保留取消/超时语义；专项死锁回归和 Run #5 通过 |
| B60-P1-041 | P1 | UI 自动化 / React 挂载竞态 | 已关闭 | TC-PROD-003 在 React 首个交互元素挂载前立即计数，正常页面被偶发判为不可交互 | 冒烟任务出现不稳定假失败 | `backend/tests/playwright/specs/production-smoke.spec.ts`；Run #4 / Run #5 | 先等待首个交互元素可见再计数；Run #5 结果 4 pass/0 fail/1 明确 skip |
| B60-P1-042 | P1 | 项目存在性 / API 一致性 | 已关闭 | 知识、通知和 Agent 等端点原先对不存在项目 `999999` 返回空 200 | 调用方无法区分“真实空项目”和“不存在/不可访问项目”，削弱隔离与审计语义 | `backend/app/core/deps.py`、`services/project_service.py`、`tests/test_project_existence_guard.py` | 统一依赖先按身份执行成员边界，再验证 active 项目：超级管理员无效项目返回 404，非成员保持不泄露的 403；7 条门禁测试、相关 118+14 条回归及真实浏览器 404 通过 |
| B60-P1-043 | P1 | 知识中心 / 能力前置条件 | 已关闭 | 无 AI、无有效知识片段时，实体提取和 Skills 原先仍可操作并可能返回 prompt 假成功 | 用户反复触发必失败任务，无法理解缺失条件，可能产生空记录 | `services/knowledge/skill_service.py`、`api/v1/knowledge.py`、`SkillsTab.tsx`、`GraphTab.tsx`；`FP-KNOW-001-01/02-*-PASS.png` | API 返回结构化 available/reason，Skills 和图谱提取在任务/审计/提交前 fail-closed；后端 82 条、前端 15 条定向回归及 1440×900 可见 Chrome 复验通过 |
| B60-P1-044 | P1 | 知识中心 / Wiki 前置条件 | 已关闭 | Wiki 未启用、没有 active 发布包或仅有草稿时，同步原先只在执行后显示失败 | 用户无法预判必失败操作，错误提示不能指导下一步 | `backend/app/api/v1/wiki.py`、`tests/test_wiki_sync_availability.py`、`frontend/src/pages/knowledge/components/WikiTab.tsx`、`WikiTabAvailability.test.tsx`；`FP-KNOW-001-03-wiki-no-active-bundle-PASS.png` | 新增只读 availability 契约，UI 预先禁用并链接发布包管理；POST 保持 `wiki:manage`，跨项目 404、非 active 409，预检零写入。后端扩展 131 条、前端相关 8 条及可见 Chrome 复验通过 |
| B60-P2-006 | P2 | 知识中心 / 桌面布局 | 已复现 | 1440×900 下知识标签横向溢出，Skills/Agent 卡片横向空间利用率低 | PC 端需要横向滚动或难以扫描，甲方使用体验下降 | Batch 60 知识/Agent 浏览器审计截图 | 标签支持换行/可访问滚动，卡片采用响应式列数和合理最大宽度；复核 1440×900、768×1024、390×844 |

## 3. 已知外部阻塞

| ID | 级别 | 模块 | 缺失条件 | 已完成验证 | 解除条件 |
| --- | --- | --- | --- | --- | --- |
| B60-BLK-001 | P0 | Test5 六服务与运营后台 | OpenVPN 未启用；缺当前契约/有效凭据；节点 6 历史 503 | R1 静态合同和历史用例已盘点 | 用户明确授权 VPN 切换，并提供六份当前契约、最小权限账号和清理规则 |
| B60-BLK-002 | P0 | AI/蓝湖/OCR | 本地 AI 禁用；无授权 Key/蓝湖登录态/OCR 运行条件 | 本地无外呼路径可验证 | 提供独立非生产凭据、数据范围和费用/隐私授权 |
| B60-BLK-003 | P1 | 通知/集成/ELK | 无 SMTP/Webhook/Jira/TAPD/ELK 非生产端点和凭据 | 本地 schema、错误路径和状态机可继续测试 | 提供非生产接收端、最小权限凭据和证据脱敏规则 |
| B60-BLK-004 | P1 | 性能监控 | 无 SoloX、ADB/tidevice、授权真机 | 服务 fail-closed，可验证无 mock 假数据 | 提供授权设备、包名、采集窗口和恢复方案 |
| B60-BLK-005 | P0 | 旧 PostgreSQL 迁移 | 无脱敏旧库快照 | 空库迁移不能替代 | 提供可恢复脱敏快照、来源版本和数据保留断言 |

## 4. 首次浏览器基线

| 检查 | 结果 |
| --- | --- |
| 管理员登录 | PASS，进入 `/workbench` |
| 菜单接口 | HTTP 200，业务 code 0，返回 20 条 |
| 工作台统计 | HTTP 200，业务 code 0 |
| 控制台错误 | 0 |
| HTTP 4xx/5xx | 0 |
| 可见导航 | 16 项；隐藏/直达模块不在侧栏 |
| 工作台数据 | 独立新库，全部为 0；待导入 R1 体育资产 |

冷启动第一张截图曾在路由/模块编译完成前出现空壳；等待 3 秒后的复核正常。当前证据不足以登记为缺陷，后续以可量化的首屏时序和加载状态用例判断。

## 5. 修复与复测约束

1. 每项修复先补能稳定失败的行为测试。
2. 修复只覆盖问题根因，不顺带重构无关模块。
3. 复测包含问题点、历史失败用例和受影响 P0 闭环。
4. P0/P1 修复必须同时核对 UI、API、DB/任务副作用和审计（适用时）。
5. 状态从“已修复待复测”转为“已关闭”时，必须填写提交和证据路径。
