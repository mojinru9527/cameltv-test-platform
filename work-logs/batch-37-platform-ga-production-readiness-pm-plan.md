# Batch 37 — PM Plan
> **PM (🟨)** | Date: 2026-07-23

## 规格摘要

**原始需求**: batch-34 Leader 审查清单中的 P0×3 + P1×5 + 联动 L1-L5 + P2 体验增强
**目标时间**: 4-6 周（分 4 个 Phase 顺序交付）
**开发策略**: 按优先级分 Slice，每 Slice 独立可验证、独立可合入

---

## Phase 1：P0 阻断修复（Slice 1-3）

### Slice 1: 音视频真实化

#### [ ] Task 1.1: 后端 ffprobe 探测引擎
**描述**: 创建 `av_check_service.py` 的 ffprobe 实现，替换 `random.uniform` 伪造数据。调用系统 `ffprobe` 命令真实拉流，解析输出提取起播时延/码率/帧率/分辨率等指标。
**验收标准**:
- 配置直播流 URL 后可真实拉流
- 返回 JSON 包含 `startup_latency_ms`, `bitrate_kbps`, `fps`, `resolution`, `codec` 字段
- ffprobe 超时可配置（默认 30s），超时标记为 TIMEOUT
- 支持多个流地址批量探测
**涉及文件**:
- `test-platform-v2/backend/app/services/av_check_service.py` — 重写探测逻辑
- `test-platform-v2/backend/app/api/v1/special.py` — API 接口适配
**参考**: PRD US-1.1, US-1.2

#### [ ] Task 1.2: 前端音视频指标展示更新
**描述**: 更新 Special 页面，展示真实指标替代随机数。增加"探测状态"指示器（探测中/成功/超时/失败），显示原始 ffprobe 输出日志。
**验收标准**:
- 指标卡片显示真实数值 + 单位（ms/kbps/fps）
- 状态指示器颜色区分：绿色=成功、黄色=超时、红色=失败
- 可展开查看原始 ffprobe 输出
**涉及文件**:
- `test-platform-v2/frontend/src/pages/special/` — 组件更新
- `test-platform-v2/frontend/src/api/special.ts` — API 类型更新
**参考**: PRD US-1.1

### Slice 2: API 测试生产保护 + 请求快照

#### [ ] Task 2.1: 环境标记模型 + API
**描述**: 在 Environment 模型中增加 `env_type` 字段（production/staging/test）。API 测试执行前检查目标环境类型，若为 production 则要求二次确认。
**验收标准**:
- Environment 模型新增 `env_type` 字段，默认 test
- 创建/编辑环境时可选择环境类型
- API 测试执行时若目标环境为 production，返回 409 并要求 `confirm_production=true` 参数
**涉及文件**:
- `test-platform-v2/backend/app/models/environment.py` — 增加字段
- `test-platform-v2/backend/app/schemas/environment.py` — Schema 更新
- `test-platform-v2/backend/app/api/v1/environment.py` — API 更新
- `test-platform-v2/backend/app/services/av_check_service.py` 或 api_test 服务 — 执行前检查
- Alembic 迁移脚本
**参考**: PRD US-2.1

#### [ ] Task 2.2: API 请求/响应快照存储
**描述**: 执行 API 测试时保存完整的 request（method/url/headers/body）和 response（status/headers/body/timing）到 execution_result JSON。执行结果详情页展示快照。
**验收标准**:
- 每次 API 测试执行后保存完整快照
- 执行结果详情页展示格式化的 request/response
- 失败时快照帮助复现问题
**涉及文件**:
- `test-platform-v2/backend/app/services/` API 执行服务 — 快照采集
- `test-platform-v2/backend/app/models/` — execution 模型 JSON 字段
- `test-platform-v2/frontend/src/pages/apitest/` — 执行结果展示
**参考**: PRD US-2.2

#### [ ] Task 2.3: API 任务取消真中断
**描述**: 任务取消时通过 `asyncio.CancelledError` 或事件标志真正中断执行循环，而非仅改状态。
**验收标准**:
- 点击取消后 5 秒内执行循环停止
- 已完成的请求结果保留，未开始的不再执行
**涉及文件**:
- `test-platform-v2/backend/app/services/ui_runner_queue.py` — 取消逻辑（或同模式的服务）
**参考**: batch-34 验收报告 §2.2

### Slice 3: UI 自动化产物回看 + 异步执行

#### [ ] Task 3.1: UI 产物静态文件服务
**描述**: 后端提供产物文件（截图/视频/trace）的静态文件访问 API。Playwright 执行后将产物保存到指定目录，通过 API 暴露访问 URL。
**验收标准**:
- 截图可通过 URL 直接访问（返回 image/png）
- 视频可通过 URL 直接访问（返回 video/webm）
- trace 文件可下载
- 访问需鉴权（同用户 session）
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/uitest.py` — 产物访问端点
- `test-platform-v2/backend/app/main.py` — 静态文件挂载或路由
**参考**: PRD US-3.1

#### [ ] Task 3.2: 前端产物查看器
**描述**: UI 测试执行结果详情页增加产物查看组件：截图缩略图+放大、视频播放器、trace 下载按钮。
**验收标准**:
- 截图以缩略图网格展示，点击放大
- 视频用原生 `<video>` 播放
- trace 提供下载 + "用 Playwright Trace Viewer 打开"引导
**涉及文件**:
- `test-platform-v2/frontend/src/pages/uitest/` — 产物查看组件
- `test-platform-v2/frontend/src/api/uitest.ts` — API 类型
**参考**: PRD US-3.1

#### [ ] Task 3.3: UI 测试异步执行 + 环境注入
**描述**: 将 UI 测试执行从同步改为异步（BackgroundTasks 或任务队列）。支持从 Environment 配置注入 baseURL 和凭据到 Playwright 脚本。
**验收标准**:
- 提交 UI 测试后立即返回 task_id，后台异步执行
- Playwright 脚本执行前自动注入 `process.env.BASE_URL` 和 `process.env.TEST_CREDENTIALS`
- 执行完成后通过通知中心推送结果
**涉及文件**:
- `test-platform-v2/backend/app/services/ui_runner_queue.py` — 异步化
- `test-platform-v2/backend/app/api/v1/uitest.py` — API 改为异步提交
- `test-platform-v2/frontend/src/pages/uitest/` — 执行状态轮询
**参考**: PRD US-3.2

---

## Phase 2：P1 效率提升（Slice 4-7）

### Slice 4: Swagger 导入 + 接口用例自动生成（联动 L1）

#### [ ] Task 4.1: 后端 Swagger 解析器
**描述**: 创建 Swagger 解析服务，支持上传 OpenAPI 3.0/2.0 JSON/YAML，解析出 paths/operations/schemas。存储解析结果到 SwaggerImport 模型。
**验收标准**:
- POST `/api/v1/apitest/swagger/import` 接受文件上传
- 支持 JSON 和 YAML 格式
- 解析后返回 paths 列表（method + endpoint + summary）
- 解析失败返回具体错误行号和原因
- 新增 Alembic 迁移：`swagger_imports` 表
**涉及文件**:
- `test-platform-v2/backend/app/services/swagger_parser.py` — 新建
- `test-platform-v2/backend/app/models/swagger_import.py` — 新建
- `test-platform-v2/backend/app/schemas/swagger.py` — 新建
- `test-platform-v2/backend/app/api/v1/apitest.py` — 增加导入端点
- Alembic 迁移
**参考**: PRD US-4.1, 联动方案 L1

#### [ ] Task 4.2: Swagger → ApiTestCase 生成
**描述**: 用户在解析结果中勾选 paths，系统自动生成 ApiTestCase（method/endpoint/parameters/schemas/断言模板）。
**验收标准**:
- 勾选 paths 后一键生成接口用例
- 生成的用例自动填充 api_method, api_endpoint, request_body_schema, response_schema
- 自动生成基础断言：status_code=2xx, response_time<2000ms
- 可进一步手动编辑
**涉及文件**:
- `test-platform-v2/backend/app/services/swagger_parser.py` — 用例生成方法
- `test-platform-v2/backend/app/api/v1/apitest.py` — 生成端点
- `test-platform-v2/frontend/src/pages/apitest/` — Swagger 导入 UI
**参考**: PRD US-4.1

#### [ ] Task 4.3: 前端 Swagger 导入页面
**描述**: 在 API 测试模块增加 Swagger 导入入口：上传 → 预览 paths → 勾选 → 生成用例。
**验收标准**:
- 上传区域支持拖拽 JSON/YAML 文件
- 解析后列表展示 path/method/summary，每行有勾选框
- 支持全选/反选/按 tag 筛选
- 点击生成后跳转到用例列表
**涉及文件**:
- `test-platform-v2/frontend/src/pages/apitest/` — SwaggerImport 组件
- `test-platform-v2/frontend/src/api/apitest.ts` — API 函数
**参考**: PRD US-4.1

### Slice 5: 批量执行 + 执行指派

#### [ ] Task 5.1: 后端批量执行
**描述**: 新增测试计划批量执行端点，接受 plan_id，遍历所有 plan-case 依次或并发执行。返回总体进度。
**验收标准**:
- POST `/api/v1/test-plans/{id}/execute-all` 批量执行全部用例
- 支持并发数参数（默认 1，最大 10）
- 返回执行摘要：total/passed/failed/skipped/blocked
- 支持中途取消
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/test_plan.py` — 批量执行端点
- `test-platform-v2/backend/app/services/test_plan_service.py` — 批量执行逻辑
**参考**: PRD US-5.1

#### [ ] Task 5.2: 执行指派模型 + API
**描述**: 在 TestPlanCase 关联表中增加 assignee_id 和 due_date 字段。支持为每条用例指派执行人和截止日期。
**验收标准**:
- PUT `/api/v1/test-plans/{id}/cases/{case_id}/assign` 指派执行人
- GET `/api/v1/test-plans/{id}/cases?assignee_id=X` 筛选指派用例
- 工作台显示当前用户的待执行用例列表
**涉及文件**:
- `test-platform-v2/backend/app/models/test_plan.py` — TestPlanCase 增加字段
- `test-platform-v2/backend/app/api/v1/test_plan.py` — 指派 API
- `test-platform-v2/frontend/src/pages/testplan/` — 指派 UI
- Alembic 迁移
**参考**: PRD US-5.2

#### [ ] Task 5.3: 前端批量执行 + 指派 UI
**描述**: 测试计划详情页增加"批量执行"按钮和进度条。用例列表增加指派下拉框和截止日期选择。
**验收标准**:
- "批量执行"按钮触发全部用例执行，显示进度条（已完成/总数）
- 每条用例行有指派下拉框（团队成员列表）
- 工作台增加"我的待执行"卡片
**涉及文件**:
- `test-platform-v2/frontend/src/pages/testplan/` — 批量执行 + 指派组件
- `test-platform-v2/frontend/src/pages/workbench/` — 待执行卡片
**参考**: PRD US-5.1, US-5.2

### Slice 6: 报告导出 + 趋势分析

#### [ ] Task 6.1: 后端 PDF/Excel 导出
**描述**: 报告服务增加导出功能。PDF 使用 ReportLab 生成含图表的格式化报告；Excel 使用 openpyxl 生成明细数据表。
**验收标准**:
- GET `/api/v1/reports/{id}/export/pdf` 返回 PDF 文件
- GET `/api/v1/reports/{id}/export/excel` 返回 Excel 文件
- PDF 包含：标题/摘要/通过率饼图/缺陷统计/用例明细表
- Excel 包含：用例明细 sheet + 缺陷明细 sheet + 统计摘要 sheet
**涉及文件**:
- `test-platform-v2/backend/app/services/report_service.py` — 导出方法
- `test-platform-v2/backend/app/api/v1/report.py` — 导出端点
- 新增依赖：`reportlab`, `openpyxl`
**参考**: PRD US-6.1

#### [ ] Task 6.2: 多计划趋势分析
**描述**: 新增趋势分析 API，查询同一项目下多份报告的通过率/缺陷数/用例数变化趋势。
**验收标准**:
- GET `/api/v1/reports/trends?project_id=X` 返回趋势数据
- 前端趋势页面：通过率折线图 + 缺陷趋势柱状图 + 用例增长面积图
- 支持时间范围筛选
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/report.py` — 趋势端点
- `test-platform-v2/backend/app/services/report_service.py` — 趋势查询
- `test-platform-v2/frontend/src/pages/report/` — 趋势图表
**参考**: PRD US-6.2

#### [ ] Task 6.3: 前端报告导出按钮 + 趋势页面
**描述**: 报告详情页增加"导出 PDF"和"导出 Excel"按钮。新增趋势分析子页面。
**验收标准**:
- 报告详情页顶部增加导出按钮组
- 趋势页面展示 Recharts 图表
- 导出按钮点击后触发文件下载
**涉及文件**:
- `test-platform-v2/frontend/src/pages/report/` — 导出按钮 + 趋势页面
- `test-platform-v2/frontend/src/api/report.ts` — API 函数
**参考**: PRD US-6.1, US-6.2

### Slice 7: 用例评审流

#### [ ] Task 7.1: 后端用例评审状态机
**描述**: 为 TestCase 增加评审状态：draft → pending_review → approved / rejected → active。AI 生成的用例导入后默认为 draft/pending_review。增加评审 API。
**验收标准**:
- TestCase 增加 review_status 和 reviewer_id 字段
- POST `/api/v1/testcases/{id}/review` 提交评审（approve/reject + 评审意见）
- AI 生成的用例导入后状态为 pending_review
- 已 approved 的用例才能加入测试计划执行
**涉及文件**:
- `test-platform-v2/backend/app/models/test_case.py` — 增加字段
- `test-platform-v2/backend/app/api/v1/test_case.py` — 评审端点
- `test-platform-v2/backend/app/services/requirement_service.py` — AI 导入时设状态
- Alembic 迁移
**参考**: PRD US-7.1

#### [ ] Task 7.2: 前端评审界面
**描述**: 用例管理页面增加"待评审"筛选 Tab。每条用例有 Approve/Reject 按钮和评审意见输入框。
**验收标准**:
- 用例列表增加"待评审"Tab，显示 pending_review 的用例
- 用例详情/列表中有 Approve/Reject 按钮
- Reject 必须填写评审意见
- 支持批量审批
**涉及文件**:
- `test-platform-v2/frontend/src/pages/testcase/` — 评审组件
- `test-platform-v2/frontend/src/api/testcase.ts` — API 函数
**参考**: PRD US-7.1

---

## Phase 3：联动增强 Phase 1（Slice 8-9）

### Slice 8: AiResultModal 三 Tab + source_req_id（联动 L3/L4）

#### [ ] Task 8.1: 后端 AI 生成结果分类
**描述**: AI 用例生成时区分 case_type（manual/api/ui），并标记 source_req_id。API 返回时按类型分组。
**验收标准**:
- AI 生成结果中每条用例带 case_type 字段
- 每条用例带 source_req_id（关联到需求分析的 REQ 功能点）
- GET AI 结果 API 返回按 case_type 分组的数据
**涉及文件**:
- `test-platform-v2/backend/app/services/ai_service.py` — 生成逻辑
- `test-platform-v2/backend/app/services/requirement_service.py` — 结果处理
- `test-platform-v2/backend/app/api/v1/requirement.py` — API 返回格式
**参考**: PRD US-8.1, US-8.2, 联动方案 L3/L4

#### [ ] Task 8.2: 前端 AiResultModal Tab 切换
**描述**: AiResultModal 改造为三 Tab 布局：功能用例 / 接口用例 / UI 回归建议。每 Tab 独立展示对应类型的用例列表。
**验收标准**:
- 三个 Tab 切换流畅，显示各类型用例数量
- "接口用例" Tab 若无 Swagger 关联则显示引导提示
- "UI 回归建议" Tab 显示基于 release-bundle 的回归范围
**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/AiResultModal.tsx` — Tab 改造
**参考**: PRD US-8.1, 联动方案 L3

### Slice 9: 需求-API 映射 + 自动建计划（联动 L2/L5）

#### [ ] Task 9.1: 需求-API 语义映射引擎
**描述**: AI 将需求文档中 integration 类型的功能点与 Swagger 导入的 endpoint 做语义匹配，自动关联。
**验收标准**:
- 对每个 integration 类型 REQ 功能点，在 Swagger paths 中搜索匹配
- 匹配结果带置信度分数（0-1），>0.6 自动关联，<0.6 建议人工确认
- 关联后自动生成接口用例（含 source_req_id + swagger_operation_id）
**涉及文件**:
- `test-platform-v2/backend/app/services/ai_service.py` — 语义映射方法
- `test-platform-v2/backend/app/api/v1/requirement.py` — 映射 API
**参考**: PRD US-4.2, 联动方案 L2

#### [ ] Task 9.2: 导入后自动建测试计划
**描述**: AI 用例导入时增加"导入并创建测试计划"选项。勾选后自动创建 draft 状态测试计划。
**验收标准**:
- 导入对话框中增加 checkbox："同时创建测试计划"
- 勾选后自动创建测试计划（默认名：需求标题 + 日期）
- 创建的测试计划包含全部导入的用例
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/requirement.py` — 导入 + 创建计划
- `test-platform-v2/frontend/src/pages/requirement/AiResultModal.tsx` — 选项 UI
**参考**: PRD US-8.3, 联动方案 L5

---

## Phase 4：P2 体验 + 工程债务（Slice 10-12）

### Slice 10: P2 快速修复项

#### [ ] Task 10.1: 蓝湖原型配置化
**描述**: 将蓝湖原型接入的硬编码路径改为从系统配置/环境变量读取。
**验收标准**: 管理员可在系统设置中配置蓝湖 API 地址和项目 ID
**涉及文件**: 蓝湖相关配置 + System Settings 页面

#### [ ] Task 10.2: 质量门禁初版
**描述**: 报告中增加质量门禁判定：通过率阈值、P0 缺陷数上限、阻断用例数上限。
**验收标准**: 报告中显示质量门禁结果：PASS/FAIL + 不满足的门禁项

#### [ ] Task 10.3: 版本历史查看
**描述**: 用例编辑时记录变更历史（version history），支持查看和对比。
**验收标准**: 用例详情页有"版本历史"Tab，列出每次变更的时间/操作人/变更内容

### Slice 11: 工程债务清理

#### [ ] Task 11.1: npm audit 漏洞修复
**描述**: 修复 `npm audit` 报告的 2 critical + 7 high 漏洞。
**验收标准**: `npm audit` 无 critical/high 漏洞
**涉及文件**: `package.json` 依赖版本更新

#### [ ] Task 11.2: Ruff 全规则清理
**描述**: 修复 Ruff 报告的 201 条违规（重点是 113 unused import + 23 E712）。
**验收标准**: `ruff check app` 0 错误（或配置合理的 ignore 列表）
**涉及文件**: 后端 `app/` 全部文件

### Slice 12: 其他 P2 项（按优先级）

#### [ ] Task 12.1: 验证码/SSO/找回密码
#### [ ] Task 12.2: 自定义看板/仪表盘
#### [ ] Task 12.3: 项目模板/归档/克隆

---

## 质量要求

- [ ] 响应式（Desktop + Tablet）
- [ ] OpenAPI 同步（后端新端点自动生成文档）
- [ ] 单元测试覆盖（新增服务 ≥80%）
- [ ] 无 console 报错/告警
- [ ] Alembic 迁移可 upgrade/downgrade
- [ ] 所有新增依赖加入 `requirements.txt` / `package.json`

## 不纳入本次的任务（明确排除）

- 联动方案 Phase 2-3 (L6-L13)
- P3 远期功能（缺陷双向同步/多语言/微服务/测试数据工厂/SaaS化）
- Appium 移动端测试
- 音视频多协议（DASH/RTMP）
- 报告模板引擎（R4 自定义模板）
- C-CONDITIONS 中 batch-18/19/21/22/24/25/26/27 遗留项
