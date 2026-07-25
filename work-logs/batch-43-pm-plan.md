# Batch 43 — PM Plan
> **PM (🟨)** | Date: 2026-07-25

## 规格摘要

**原始需求**: 见 [batch-43-prd-summary.md](batch-43-prd-summary.md)
- 目标：test-platform-v2 全线功能验收 + 逻辑查漏补缺
- 三层验收：Tier 1 (7 核心模块) → Tier 2 (9 支撑模块) → Tier 3 (8 辅助模块)
- 每个模块：加载态/空态/错误态/边界值 + 正常 CRUD
- C-CONDITIONS: ≥8 个 Close

**目标时间**: batch-43 一个完整六部门周期

---

## 开发任务

### Slice 1: 核心链路① — 用例管理 + 测试计划

#### [ ] Task 1.1: 测试用例模块功能验收 (60min)
**描述**: 对 testcase 页面执行全功能验收：列表/搜索/筛选/创建/编辑/删除/批量操作/导入导出。检查每个操作的正常路径和异常路径（空字段、非法值、超长文本）。
**验收标准**:
- 用例 CRUD 全部正常，列表分页/搜索/筛选正确
- 空标题提交 → 前端表单校验拦截（不报 500）
- 超长文本输入 → 有截断或提示
- 导入格式错误 → 明确错误消息
- 删除操作有确认弹窗
**涉及文件**: 
- `frontend/src/pages/testcase/` — 用例列表/详情/表单
- `backend/app/api/v1/test_case.py` — 用例 CRUD API
- `backend/app/services/test_case_service.py` — 业务逻辑
- `backend/app/models/test_case.py` — 数据模型
**参考**: PRD §US-1

#### [ ] Task 1.2: 测试计划模块功能验收 (45min)
**描述**: 对 testplan 页面执行功能验收：创建计划→添加用例→设置执行顺序→分配执行人→查看执行进度。
**验收标准**:
- 计划 CRUD 正常，用例关联正确
- 空计划（无用例）展示合理空态
- 重复添加同一用例有去重或提示
- 执行进度百分比计算正确
**涉及文件**:
- `frontend/src/pages/testplan/` — 计划页面
- `backend/app/api/v1/test_plan.py` — 计划 API
- `backend/app/services/test_plan_service.py` — 业务逻辑
- `backend/app/models/test_plan.py` — 数据模型
**参考**: PRD §US-1

---

### Slice 2: 核心链路② — API 测试 + UI 测试

#### [ ] Task 2.1: API 测试模块功能验收 (60min)
**描述**: apitest 页面验收：Swagger 导入→测试用例生成→执行→查看结果→断言验证。重点检查执行引擎逻辑（超时处理、重试、并发安全）。
**验收标准**:
- API 资产列表正常展示，搜索/筛选有效
- Swagger URL 导入成功，解析错误有提示
- 单条/批量执行正常，结果与手动 curl 一致
- 执行超时有合理超时时间和错误信息
- 断言失败时错误详情清晰
**涉及文件**:
- `frontend/src/pages/apitest/` — API 测试页面
- `backend/app/services/api_execution_service.py` — 执行引擎
- `backend/app/services/openapi_import_service.py` — Swagger 导入
- `backend/app/models/api_asset.py` — API 资产模型
**参考**: PRD §US-1, C27-C3

#### [ ] Task 2.2: UI 测试模块功能验收 (45min)
**描述**: uitest 页面验收：用例关联→Playwright 执行→截图查看→结果分析。检查执行队列、并发限制、失败重试。
**验收标准**:
- UI 测试用例列表正常，关联的功能用例跳转正确
- 单条执行完成并返回截图/日志
- 并发执行不超过配置上限
- 执行失败有可读的错误信息和截图
**涉及文件**:
- `frontend/src/pages/uitest/` — UI 测试页面
- `backend/app/services/playwright_executor.py` — Playwright 执行器
- `backend/app/services/ui_runner_queue.py` — 执行队列
- `backend/app/models/ui_test.py` — UI 测试模型
**参考**: PRD §US-1

---

### Slice 3: 核心链路③ — 执行调度 + 报告 + 缺陷

#### [ ] Task 3.1: 执行调度模块功能验收 (45min)
**描述**: schedule 页面验收：定时任务 CRUD→触发执行→查看历史→暂停/恢复。检查 cron 表达式校验、时区处理、任务堆积保护。
**验收标准**:
- 定时任务 CRUD 正常，cron 表达式校验正确
- 手动触发立即执行
- 执行历史可追溯（状态/耗时/日志）
- 同一任务堆积时有保护（不无限创建执行实例）
**涉及文件**:
- `frontend/src/pages/schedule/` — 调度页面
- `backend/app/services/schedule_service.py` — 调度服务
- `backend/app/models/test_schedule.py` — 调度模型
**参考**: PRD §US-1

#### [ ] Task 3.2: 测试报告 + 缺陷管理功能验收 (60min)
**描述**: report + defect 页面验收：报告生成→查看详情→趋势图表→缺陷 CRUD→关联用例/报告。检查报告数据准确性、缺陷流转状态机。
**验收标准**:
- 执行完成后自动生成报告，数据与执行结果一致
- 报告详情含通过率/耗时/失败详情
- 缺陷状态流转正确（Open→In Progress→Resolved→Closed）
- 缺陷可关联测试用例和报告
- 空报告/零缺陷列表展示合理空态
**涉及文件**:
- `frontend/src/pages/report/` + `frontend/src/pages/defect/` — 页面
- `backend/app/services/report_service.py` — 报告服务
- `backend/app/services/defect_service.py` — 缺陷服务
- `backend/app/models/test_report.py` + `backend/app/models/defect.py` — 模型
**参考**: PRD §US-1

---

### Slice 4: 支撑模块① — 需求 + 知识中心 + 数据集

#### [ ] Task 4.1: 需求管理模块功能验收 (45min)
**描述**: requirement 页面验收：需求 CRUD→模块树→版本关联→蓝湖导入。重点检查模块树逻辑和导入完整性。
**验收标准**:
- 需求 CRUD 正常，模块树展示正确
- 蓝湖导入成功后需求内容完整（文本+图片）
- 需求与测试用例的追溯关系正确
- 版本筛选有效
**涉及文件**:
- `frontend/src/pages/requirement/` — 需求页面
- `backend/app/services/requirement_service.py` — 需求服务
- `backend/app/models/requirement.py` + `requirement_module.py` — 模型
- `backend/app/services/lanhu_evidence/` — 蓝湖导入
**参考**: PRD §US-2, C27-C1

#### [ ] Task 4.2: 知识中心模块功能验收 (45min)
**描述**: knowledge 页面验收：知识入库→分类→检索→图谱→Wiki 同步。检查数据隔离、搜索准确性、图谱渲染。
**验收标准**:
- 知识列表/搜索/筛选正常
- 知识图谱渲染不崩溃（节点 ≤200）
- 两域（平台知识/业务知识）数据隔离正确
- Wiki 同步状态可查看
**涉及文件**:
- `frontend/src/pages/knowledge/` — 知识页面
- `backend/app/services/knowledge/` — 知识服务
- `backend/app/models/knowledge.py` + `wiki.py` — 模型
**参考**: PRD §US-2, C26KB-C2/C3

#### [ ] Task 4.3: 数据集模块功能验收 (30min)
**描述**: dataset 页面验收：数据集 CRUD→数据预览→关联测试用例→导出。
**验收标准**:
- 数据集 CRUD 正常
- 数据预览展示正确（表格/JSON）
- 导出格式正确（CSV/JSON）
**涉及文件**:
- `frontend/src/pages/dataset/` — 数据集页面
- `backend/app/services/dataset_service.py` — 数据集服务
- `backend/app/models/dataset.py` — 模型
**参考**: PRD §US-2

---

### Slice 5: 支撑模块② — 环境/集成/通知/版本/项目/系统

#### [ ] Task 5.1: 环境管理 + 集成管理 (45min)
**描述**: environment + integration 页面验收：环境配置 CRUD→连通性测试→集成配置→同步触发。
**验收标准**:
- 环境 CRUD 正常，连通性测试返回正确结果
- 集成配置保存后同步触发
- 敏感字段（密码/token）不返回前端
**涉及文件**:
- `frontend/src/pages/environment/` + `frontend/src/pages/integration/` — 页面
- `backend/app/services/environment_service.py` + `integration_service.py` — 服务
- `backend/app/models/environment.py` + `integration.py` — 模型
**参考**: PRD §US-2

#### [ ] Task 5.2: 通知中心 + 版本使命 + 项目设置 + 系统管理 (45min)
**描述**: notify + version_mission + project + system 页面验收：通知配置→版本进度→项目信息→系统参数。
**验收标准**:
- 通知渠道（钉钉/飞书/企微）配置保存
- 版本使命进度计算正确
- 项目设置保存生效
- 系统管理权限控制正确（仅管理员可操作）
**涉及文件**:
- `frontend/src/pages/notify/` + `project/` + `system/` — 页面
- `backend/app/services/notify_service.py` + `version_mission_service.py` — 服务
- `backend/app/services/project_service.py` + `rbac_service.py` — 项目/RBAC
**参考**: PRD §US-2, US-3

---

### Slice 6: 辅助模块 + 收尾

#### [ ] Task 6.1: Tier 3 辅助模块门禁检查 (45min)
**描述**: login/workbench/agent-workbench/perftest/release-bundles/mindmap/trace/special 八个页面依次打开，检查：页面不白屏、基本交互正常、无 console 错误。
**验收标准**:
- 8 个页面全部可加载，无白屏/JS 崩溃
- 基本操作（登录/看板查看/脑图渲染/链路查询）正常
- console 无未捕获的 error
**涉及文件**: 上述 8 个页面目录
**参考**: PRD §Tier 3

#### [ ] Task 6.2: C-CONDITIONS 归位 (30min)
**描述**: 遍历 32 个 Open C-conditions，将本次修复的标记为 Closed，无法处理的给出明确原因和计划。
**验收标准**:
- ≥8 个条件 Closed
- 剩余条件有明确的归位计划或排除理由
**涉及文件**: `C-CONDITIONS.md`
**参考**: PRD §US-4

#### [ ] Task 6.3: 前端硬门禁 + 后端硬门禁 (30min)
**描述**: 运行最小硬门禁确保代码质量：前端 typecheck+build；后端导入检查+ruff F821+Alembic 单头+revision。
**验收标准**:
- `npm run typecheck` 零错误
- `npm run build` 成功
- `python -c "import app.models, app.services, app.api"` 无报错
- `ruff check app --select F821` 零未定义
- `alembic check` 通过
**涉及文件**: 全量
**参考**: QA 硬门禁

---

## 质量要求

- [x] 每个 Task 30-60 分钟可完成
- [x] 每个 Task 有明确的涉及文件和验收标准
- [x] 引用 PRD 章节
- [ ] 响应式（Desktop + Tablet）— Design 走查覆盖
- [ ] OpenAPI 同步 — API 测试模块验证
- [ ] 单元测试覆盖 — Dev 按 TDD 补充
- [ ] 无障碍（ARIA/键盘）— Design 走查覆盖
- [ ] 无 console 报错/告警 — QA 逐页检查
