# Batch 37 — PRD Summary
> **Product (🟦)** | Date: 2026-07-23 | Status: Draft

## 1. 问题陈述

### 背景

测试平台 V2 已完成 24 个路由页面的核心闭环（需求→AI用例→计划→执行→报告→缺陷），V2.2-V2.6 六个大版本全部交付。但 batch-34 初版验收和 Leader 走查发现：**平台在"生产就绪"维度存在 3 个 P0 阻断项和 5 个 P1 严重缺口**，导致平台无法真正投入 camel1.tv 体育直播平台的生产测试使用。

### 核心痛点

1. **音视频质量检测是假的**：camel1.tv 作为体育直播平台，最核心的测试需求是直播流质量（起播时延、卡顿率、首帧时间、画质切换）。当前指标全部用 `random.uniform` 伪造——测试结果不可信，无法用于生产决策。

2. **API 测试没有生产保护**：执行 API 测试时无环境标记/拦截机制，存在误伤生产环境的致命风险。一旦测试请求打到 camel1.tv 线上，可能造成数据污染或服务中断。

3. **UI 自动化产物不可回看**：Playwright 执行产生的截图/视频/trace 字段已占位但无法实际查看——执行结果不可验证，自动化测试形同虚设。

4. **接口用例创建效率极低**：1591 条接口用例的来源不明，缺少 Swagger 文档导入能力。测试同学需要手工逐条填写 API endpoint、method、parameters、assertions——效率低且易出错。

5. **大规模执行不可行**：2384 条用例、7 个测试计划，不支持批量执行和执行指派——逐条手工执行在现实中不可能完成。

6. **报告无法对外交付**：报告无 PDF/Excel 导出、无趋势分析——测试成果无法正式交付给项目干系人。

### 证据

| 证据来源 | 发现 |
|----------|------|
| batch-34 验收报告 §2.5 | 音视频指标 `random.uniform` 伪造，"对 camel1.tv 致命" |
| batch-34 验收报告 §2.2 | API 测试缺生产环境保护，"可能误伤线上" |
| batch-34 验收报告 §2.3 | UI 产物"截图/视频/trace 字段占位，不可实际查看" |
| batch-34 验收报告 §4 | Swagger 导入缺失，报告导出缺失，批量执行缺失 |
| batch-34 Leader 审查 §2.1-2.3 | P0×3, P1×5 待补齐 |
| batch-34 模块联动方案 §5 | Swagger→API映射→全链路联动全部未启动 |

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 音视频指标真实性 | 0%（全随机数） | 100%（ffprobe 真实探测） | 单次执行 |
| API 生产环境保护 | 无保护 | 生产环境标记 + 执行前拦截确认 | 每次执行 |
| UI 产物可回看率 | 0% | 100%（截图/视频/trace 可在线查看） | 每次执行 |
| Swagger 导入成功率 | 不支持 | ≥95%（标准 OpenAPI 3.0/2.0 规范） | 导入操作 |
| 批量执行吞吐 | 1 条/次 | ≥50 条/批次，支持指派到人 | 单次批量执行 |
| 报告导出格式 | 仅在线查看 | PDF + Excel 双格式 | 单次导出 |
| 用例评审覆盖率 | 0%（无评审流） | AI 生成用例 100% 经人工评审入库 | 每次 AI 生成 |

## 3. 非目标（本次不做）

以下功能明确排除在 batch-37 之外：

- **音视频多协议支持（HLS/WebRTC 之外）**：先做 HLS 主流协议，DASH/RTMP 等远期
- **Appium 移动端测试**：属于 P2，batch-37 聚焦 Web 端
- **缺陷双向同步（禅道/Jira）**：属于 P3，远期
- **多语言测试框架**：属于 P3，远期
- **微服务拆分 / SaaS 化**：属于 P3 架构演进，远期
- **联动方案 Phase 2-3**（L6-L13）：本次只做 Phase 1 基础联动（L1-L5）
- **C-CONDITIONS 遗留项**：batch-18/19/21/24/25/26/27 的 Open 条件与本次范围无直接关联，不纳入；batch-31 的 C31-2/C31-3 需单独处理

## 4. 用户故事 + 验收标准

### Epic 1：音视频质量真实化（P0）

**US-1.1** — As a 测试工程师, I want 平台使用 ffprobe 真实拉流探测音视频指标, so that 起播时延/卡顿率/首帧时间等指标反映真实用户体验。

- **验收**：Given 配置了 camel1.tv 直播流 URL / When 执行音视频专项测试 / Then 指标来自 ffprobe 真实探测结果，非随机数；控制台可查看原始 ffprobe 输出日志

**US-1.2** — As a 测试工程师, I want 支持配置多个直播流地址和探测参数, so that 可以批量验证不同赛事/频道的流质量。

- **验收**：Given 添加了 3 个直播流 URL / When 执行批量音视频检测 / Then 每个流独立返回指标结果

### Epic 2：API 测试生产保护（P0）

**US-2.1** — As a 平台管理员, I want 每个环境标记为"生产/测试/预发布", so that 系统可以识别并拦截对生产环境的测试请求。

- **验收**：Given 环境 A 标记为"生产" / When 尝试对该环境执行 API 测试 / Then 系统弹出二次确认："此环境标记为生产环境，确认执行？"；用户确认后才执行

**US-2.2** — As a 测试工程师, I want API 测试执行后保存完整请求/响应快照, so that 失败时可以复现问题。

- **验收**：Given 执行了一条 API 测试 / When 查看执行结果 / Then 可以看到完整的 request（method/url/headers/body）和 response（status/headers/body/timing）

### Epic 3：UI 自动化产物回看（P0）

**US-3.1** — As a 测试工程师, I want 在 UI 测试执行结果中直接查看截图/视频/trace, so that 可以验证 UI 自动化是否按预期执行。

- **验收**：Given 一条 UI 测试执行完成 / When 打开执行结果详情 / Then 截图以缩略图展示、视频可在线播放、trace 可下载或用 Playwright Trace Viewer 打开

**US-3.2** — As a 测试工程师, I want UI 测试异步执行且支持环境变量注入（baseURL/凭据）, so that 长时间测试不会超时且能适配不同环境。

- **验收**：Given 配置了 baseURL 和测试凭据 / When 提交 UI 测试任务 / Then 任务异步执行，Playwright 脚本自动注入环境变量，完成后通知用户

### Epic 4：Swagger 导入 + 接口用例自动生成（P1 + 联动 L1）

**US-4.1** — As a 测试工程师, I want 上传 Swagger JSON/YAML 文件自动生成接口用例, so that 不需要手工逐条填写 1591 条接口用例。

- **验收**：Given 上传了标准 OpenAPI 3.0 JSON / When 系统解析 / Then 展示 path 列表，每个 path 可勾选，勾选后自动生成 ApiTestCase（含 method/endpoint/parameters/response schema）

**US-4.2** — As a 测试工程师, I want Swagger 导入时自动匹配需求文档中的 integration 类型功能点, so that 接口用例与需求建立追溯关系。

- **验收**：Given 已导入需求文档并完成 AI 分析 / When 上传 Swagger 并执行映射 / Then integration 类型功能点自动关联到匹配的 Swagger endpoint，生成的接口用例带 source_req_id

### Epic 5：批量执行 + 执行指派（P1）

**US-5.1** — As a 测试工程师, I want 在测试计划中一键批量执行所有用例, so that 不需要逐条点击执行 2384 条用例。

- **验收**：Given 一个包含 50 条用例的测试计划 / When 点击"批量执行" / Then 所有用例依次执行，显示总体进度条，完成后汇总结果

**US-5.2** — As a 测试经理, I want 将测试计划中的用例指派给不同测试人员, so that 团队可以分工协作执行测试。

- **验收**：Given 一个测试计划 / When 为每条用例选择指派人和截止日期 / Then 被指派人可在工作台看到自己的待执行用例列表

### Epic 6：报告导出 + 趋势分析（P1）

**US-6.1** — As a 测试经理, I want 将测试报告导出为 PDF/Excel, so that 可以正式交付给项目经理和业务方。

- **验收**：Given 一份测试报告 / When 点击"导出 PDF"或"导出 Excel" / Then 生成格式规范的 PDF（含图表）或 Excel（含数据明细）

**US-6.2** — As a 测试经理, I want 查看多计划执行趋势图, so that 可以评估版本质量变化趋势。

- **验收**：Given 同一项目下有 3+ 份已完成报告 / When 打开趋势分析 / Then 展示通过率趋势折线图、缺陷发现趋势图、用例增长趋势图

### Epic 7：用例评审流（P1）

**US-7.1** — As a 测试工程师, I want AI 生成的用例先进入评审状态再由 Reviewer 审核, so that AI 生成的用例质量有人工把关后才能入库。

- **验收**：Given AI 生成了一批用例 / When 导入时 / Then 用例进入 draft 状态，需 Reviewer 逐条或批量 approve/reject（带评审意见）后才能变为 active

### Epic 8：联动增强 — Phase 1 基础链路（P1）

**US-8.1** — As a 测试工程师, I want AiResultModal 分成"功能/接口/UI"三个 Tab 展示, so that 一眼看清 AI 为需求生成了哪些类型的用例。

- **验收**：Given AI 完成需求分析和用例生成 / When 打开 AiResultModal / Then 看到三个 Tab：功能用例（manual）、接口用例（api）、UI 回归建议（ui），各 Tab 显示用例数量和预览

**US-8.2** — As a 测试工程师, I want AI 生成的用例自动标记 source_req_id, so that 每条用例可以追溯到来源需求功能点。

- **验收**：Given AI 生成了用例 / When 在用例库中查看 / Then 每条用例显示关联的 REQ 功能点编号和需求文档链接

**US-8.3** — As a 测试工程师, I want 导入用例时可选择"自动创建测试计划", so that 减少手工创建计划的操作步骤。

- **验收**：Given AI 生成了 15 条用例 / When 勾选"导入并创建测试计划" / Then 系统自动创建 draft 状态测试计划，包含全部导入用例

## 5. 技术考量

### 依赖

| 依赖项 | 状态 | 说明 |
|--------|------|------|
| ffprobe (FFmpeg) | 需服务端安装 | 音视频真实化核心依赖，需在部署环境安装 ffmpeg |
| Playwright Trace Viewer | 需前端集成 | UI 产物回看需要 trace 在线查看能力 |
| Swagger Parser (Python) | 需引入 `openapi-spec-validator` 或 `prance` | Swagger 导入解析 |
| ReportLab / openpyxl | 需引入 Python 库 | PDF/Excel 报告生成 |
| DeepSeek LLM API | 已有 | 需求-API 语义映射 |

### 已知风险

| 风险 | 影响 | 对策 |
|------|------|------|
| ffprobe 直播流探测超时 | 音视频测试结果延迟 | 可配置超时时间 + 重试次数，超时标记为 TIMEOUT |
| Swagger 文档不规范（非标准 OpenAPI） | 导入失败率高 | 支持 OpenAPI 2.0/3.0 双版本，解析失败给出明确错误行号 |
| UI 产物文件过大 | 存储压力，前端加载慢 | 截图压缩、视频限时长、trace 过期清理策略 |
| 批量执行并发过高 | 后端压力/目标服务限流 | 可配置并发数和间隔时间 |
| 需求-API 语义映射不准 | 生成错误的接口关联 | AI 映射结果需人工确认环节 |

### 待解决问题

1. 音视频探测是否需要支持鉴权直播流（需 token/sign 的流地址）
2. UI trace 文件在线查看是自建 viewer 还是引导用户用 Playwright Trace Viewer 桌面版
3. 报告 PDF 模板是否需要品牌化定制（logo/页眉页脚）

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 | 预估工作量 |
|------|------|---------|-----------|
| Phase 1: P0 阻断修复 | 内部测试团队 | 音视频做真 + API 保护 + UI 产物回看 三项全部可用 | 1-2 周 |
| Phase 2: P1 效率提升 | 内部测试团队 | Swagger导入 + 批量执行 + 报告导出 + 评审流 四项全部可用 | 2-3 周 |
| Phase 3: 联动增强 | 内部测试团队 | AiResultModal Tab + source_req_id + 自动建计划 可用 | 1-2 周 |
| Phase 4: P2 体验 + 工程债务 | 全体用户 | 按优先级逐项交付 | 持续 |

---

*本 PRD 基于 batch-34 Leader 审查清单、初版验收报告和模块联动方案编写。关联 C-CONDITIONS：本次不直接处理任何 Open C 条件（均与本批次范围无交集），但 batch-31 的 C31-2/C31-3 需在后续单独评估。*
