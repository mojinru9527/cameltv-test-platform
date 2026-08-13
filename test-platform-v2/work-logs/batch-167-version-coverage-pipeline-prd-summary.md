# Batch 167 — 版本级三类型模块覆盖主链路（Phase 0–3）— PRD Summary
> **Product (🟦)** | Date: 2026-08-13 | Status: Approved | Mode: full

mode: full
理由: 引入新行为、新接口、新配置与 Schema 变更（覆盖矩阵、需求源适配、接口用例绑定、功能→UI 自动转换），按 pipeline-modes 判定完整批次。

## 0. 背景与用户诉求
用户愿景：输入「需求地址、体育生产地址、接口地址、运营后台地址、对应账号」后，平台自动完成
版本需求提取 → 功能用例 + 接口用例 + UI 自动化用例 → 测试计划自动关联三类用例 → 自动执行并覆盖 ≥60% 的版本模块。

当前四条核心差距（已代码定位）：
1. 无版本级「模块 × 三类型 × 执行状态」覆盖度量，无法知道差多少、差在哪。
2. 需求只支持文件上传/蓝湖，不支持通用需求 URL；大文档提取单次 LLM 调用易截断，失败静默降级。
3. 需求生成的接口用例是 AI 猜路径，未绑定已导入 OpenAPI 的真实端点与需求模块。
4. 计划一键执行把 manual 用例一律 skip；UI 编译是正则规则引擎，自然语言步骤大量落 TODO；无「功能→UI 自动转换」。

## 1. 问题陈述（按用户原话逐条对应）
| 用户观察 | 根因（代码锚点） |
|---------|------------------|
| 功能用例大量跳过 | `test_plan_service.execute_all_cases` 对非 api/ui 用例直接 `status=skip, notes=需人工执行` |
| 需求提取不完整 | `ai_service.extract_features` 单次调用 + `_build_local_extraction_fallback` 静默降级；上传仅文件/蓝湖 |
| 接口自动化瑕疵 | 需求侧 api_cases 由 LLM 猜测端点；`match_api_endpoints` 关键词打分错配；未回填 `requirement_module_id` |
| UI 自动化瑕疵 | `playground_service._gherkin_to_playwright` 正则映射落 `TODO` 即失败；`generate_ui_drafts` 空步骤模板；from-cases 只建空任务 |

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 版本模块三类型覆盖率（all-three） | <15%（估） | 有真实数据版本 ≥60%（P0/P1 模块优先，分母=全部模块） | 合入后按真实版本测量 |
| 需求 URL 接入 | 仅文件/蓝湖 | 通用 URL/PingCode/Confluence 可提取为需求文档 | 合入后 |
| 大文档提取完整度 | 单次调用 | 分块提取 + 截断/降级显式透出，无静默丢功能点 | 合入后 |
| 需求接口用例真实性 | LLM 猜路径 | 绑定已导入真实 ApiEndpoint 后确定性生成并回填模块 | 合入后 |
| 计划执行 skip 率 | manual 全 skip | auto_ui 开启时 manual(P0/P1 有步骤) 自动转 UI 执行，仅无步骤用例 skip | 合入后 |
| 计划三类型自动关联 | 仅功能+API | 功能+API+UI 三类一次导入即关联 | 合入后 |

## 3. 非目标（本次不做）
- 不做 Phase 4 的完全无人工「一键全自动」编排页面（计划自动创建已覆盖，后续批次做版本任务 UI 编排）。
- 不接真实第三方凭据（PingCode token/账号由环境变量注入，缺凭据 fail closed 并给明确错误，不伪造）。
- 不做生产环境写接口自动执行（沿用既有生产保护，写方法仍需确认/权限）。
- 不改 lanhu-mcp 子模块本体；蓝湖仍走既有证据包质量门禁。
- 不做 UI 自愈/选择器对象库的持久化版本管理（登录态与数据准备的稳定性缺口登记为 C167-N）。

## 4. 用户故事 + 验收标准
- As 测试负责人, I want 版本详情页看到「模块 × 功能/接口/UI × 执行」覆盖矩阵和 60% 门禁, so that 我能量化每个版本的三类型覆盖。
  - Given 发布包已有模块树与用例 / When 打开版本覆盖面板 / Then 矩阵逐模块展示三类用例数、执行数、all-three 覆盖率，缺口按 P0/P1 优先排序。
- As 测试人员, I want 粘贴需求 URL 直接提取, so that 不再手工下载上传文档。
  - Given 需求 URL 可访问 / When 提交提取 / Then 生成需求文档并进入功能拆分；不可访问时给出分类错误（超时/403/格式）。
- As 测试人员, I want 大文档提取不被截断且降级可见, so that 提取结果完整可信。
  - Given 文档超过分块阈值 / When 提取 / Then 分块合并返回，`extraction_meta.mode=chunked`；降级/截断在 UI 明显标注。
- As 测试人员, I want 需求 integration 功能点绑定已导入接口后确定性生成接口用例并回填模块, so that 接口用例真实可执行可统计。
  - Given 项目已导入 OpenAPI 端点 / When 点击「按已导入接口生成接口用例」/ Then 生成用例含真实 method/path/schema 断言，`requirement_module_id` 已回填，重复生成幂等。
- As 测试人员, I want 导入用例创建计划时自动生成 UI 变体并关联, so that 计划内天然具备三类用例。
  - Given 勾选功能用例并创建计划 / When 导入 / Then 计划包含功能、接口、UI 三类用例；UI 变体可编译执行。
- As 测试人员, I want 一键执行时 manual P0/P1 自动转 UI 执行, so that 不再大量 skip。
  - Given 计划含 manual 用例且 auto_ui=true / When 一键执行 / Then 有步骤用例走编译执行（LLM 优先，规则引擎兜底）并回写结果与 UI 任务；无步骤用例 skip 并注明原因。

## 5. 技术考量
- Schema：`requirement_document` 增 `source_url`/`extraction_meta`；`release_bundle` 增 5 个接入字段；`version_mission` 增 `api_spec_url`（与既有字段对齐）。
- 需求源适配：`requirement_source_service.fetch_url_content` 统一超时/错误分类/HTML→文本；PingCode/Confluence token 走 `settings` 环境变量，缺则 fail closed。
- 覆盖口径（与用户确认）：模块被覆盖 = 同时有功能用例 + 接口用例 + UI 用例；执行覆盖 = API 与 UI 用例均至少执行一次。分母=版本全部模块，P0/P1 模块加权展示。
- UI 编译：`case_compiler_service.compile_to_playwright`（LLM）优先，`playground_service.compile_spec`（规则）兜底；编译含 TODO 时如实 fail 不伪造 pass。
- 已知风险：真实账号/登录态、写操作数据准备依赖外部输入；外部不可达时 fail closed 并在矩阵标「执行未覆盖」。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全队 | 后端 ruff/import/alembic 单头/受影响 pytest；前端 typecheck/build/vitest；CI required checks 全绿 |
| test 部署后 | 测试负责人 | 用真实版本跑覆盖矩阵与 60% 门禁；需求 URL 提取、接口绑定、auto_ui 走查 |

## 7. 技能使用
- cameltv-bug-guard → 后端静态路由/迁移/envelope 码、前端 useEffect cleanup/无 N+1、测试 StaticPool/双 404 约定。
- cameltv-agent-team → 本批次六部门流水线。
- test-case-design / cameltv-api-test → 用例与接口生成口径对齐团队标准。
