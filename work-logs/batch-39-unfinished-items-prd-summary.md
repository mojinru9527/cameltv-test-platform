# Batch 39 — PRD Summary: 全部未完成事项大收官
> **Product (🟦)** | Date: 2026-07-24 | Status: Draft

## 1. 问题陈述

通过 work-logs/ 全量轮询（173 个文件，覆盖 batch-18 至 batch-38），发现约 **100+ 未完成事项**分布在前 20+ 个批次中。核心问题：

- **P0 致命阻塞**：音视频指标是 `random.uniform` 假数据、API 测试无生产保护、UI 产物无法实际回放——测试平台在直播场景下不可信
- **P1 严重功能缺口**：Swagger 导入、批量执行、报告导出、缺陷全流程、用例评审——核心工作流不完整
- **P1 待验证不一致**：7 项功能 Backlog 声称已交付但验收报告称缺失
- **P2 增强缺失**：11 项体验/安全/效率改进未落地
- **工程债务**：17 个 npm 漏洞、develop 零保护、9 个预存测试失败、32 个 Open C-CONDITIONS
- **20+ 个批次零进展**：PM 计划齐全但从未开始编码

## 2. 成功指标

| 指标 | 基线 | 目标 | 条件 |
|------|------|------|------|
| P0 致命阻塞 | 3 | 0 | 全部修复 |
| P1 严重功能缺口 | 11 | ≤2（仅 staging 依赖项豁免） | 可本地验证的必须完成 |
| P1 不一致验证 | 7 | 逐项复核并记录结论 | 全部关闭 |
| P2 增强 | 11 | ≤3（非阻塞豁免） | 至少完成 8 项 |
| 工程债务 | 6 | ≤1 | npm audit 高危清零 |
| Open C-CONDITIONS | 32 | ≤10（仅 staging/设备依赖豁免） | 环境阻塞项明确标记 |
| 预存测试失败 | 9 | 0 | 全部修复 |
| CI 门禁 | 通过 | 通过 | ruff F821 / TS typecheck / build / Alembic 单头 |

## 3. 非目标（本次不做）

- **需 staging 环境验证的项**：C27-C1~C4（模块树准确率/图性能/bundle端到端/Wiki同步覆盖率）→ 标记为 `BLOCKED:staging`，等环境就绪后走独立 batch
- **需物理设备的项**：CP-C1（Android 真机）、CP-C2（iOS 真机）→ 标记为 `BLOCKED:device`
- **P3 长期项**：缺陷双向同步、多语言测试框架、测试数据工厂、微服务拆分、AI 根因分析、多租户 SaaS → 排入后续版本
- **已合入 batch-38 的内容**：8 个知识中心修复（PR #64）
- **模块联动方案 Phase 2-3**（L6-L13）：依赖 Phase 1 完成 + 真实数据积累，排入后续版本

### C-CONDITIONS 豁免说明

| 条件 ID | 豁免原因 |
|----------|---------|
| C27-C1~C4 | 需 staging 环境，本地不可验证 |
| CP-C1, CP-C2 | 需物理设备（Android/iOS），本地不具备 |
| C31-2, C31-3 | 需人工审查者 + 生产地址/账号，非代码层面可解决 |
| batch-18-C14 | 分环境灰度放量 SOP — 运维文档，非平台功能 |
| 其余 22 个 Open C-CONDITIONS | **纳入本次 batch-39** |

## 4. 用户故事 + 验收标准

### Phase 1 — P0 致命阻塞 (3 US)

**US-P0-1: 音视频真实流探测**
- As a 测试工程师, I want `/special` 页面的 AV 指标来自真实 ffprobe/ffplay 而非 `random.uniform`, so that 直播流启播延迟/卡顿率/首帧时间可真实衡量
- Given 一个可访问的流地址 / When 进入 Special 测试页并启动检测 / Then 指标值来自 ffprobe 实际探测结果，非随机数

**US-P0-2: API 测试生产环境保护**
- As a 平台运维, I want API 测试模块有环境标记和误击保护, so that 测试请求不会误发到生产环境
- Given 配置了环境类型标记 / When 在生产环境执行 API 测试 / Then 显示明确警告并要求二次确认；Given 非生产环境 / When 执行 API 测试 / Then 正常执行不拦截

**US-P0-3: UI 自动化产物回放**
- As a 测试工程师, I want UI 自动化的 screenshot/video/trace 可实际查看, so that 失败用例可以回溯复现
- Given 一条已执行的 UI 用例 / When 点击查看产物 / Then screenshot 可预览、video 可播放、trace 可下载

### Phase 2 — P1 严重功能缺口 (7 US)

**US-P1-1: Swagger 文档导入**
- As a 测试工程师, I want 上传 Swagger JSON/YAML 自动生成 API 测试用例, so that 不需要逐条手写接口用例
- Given 一个有效的 Swagger 文件 / When 上传到 API 资产管理 / Then 解析出所有 endpoint 并自动生成基础用例模板

**US-P1-2: 测试计划批量执行**
- As a 测试负责人, I want 测试计划内的所有用例可以批量执行, so that 2384 条用例不需要逐条点击
- Given 一个包含 N 条用例的测试计划 / When 点击"批量执行" / Then 所有用例按顺序执行，进度实时展示

**US-P1-3: 报告 PDF/Excel 导出**
- As a 测试负责人, I want 把测试报告导出为 PDF/Excel, so that 可以交付给外部干系人
- Given 一份已生成的测试报告 / When 点击导出 / Then 生成格式正确的 PDF 或 Excel 文件

**US-P1-4: 缺陷全流程状态机**
- As a 测试工程师, I want 缺陷有完整的确认→修复→回归→关闭流程, so that 缺陷生命周期可追溯
- Given 一个新建缺陷 / When 依次流转确认/修复/回归/关闭 / Then 状态变更记录在历史中，含评论和附件

**US-P1-5: 用例评审流程**
- As a 测试负责人, I want AI 生成的用例入库前经过人工评审, so that 低质量用例不会污染用例库
- Given AI 生成了一批测试用例 / When 提交入库 / Then 必须先经过评审（approve/reject/edit-then-import）

**US-P1-6: API 请求快照**
- As a 测试工程师, I want API 测试执行时记录完整 request/response, so that 失败用例可以基于快照复现
- Given 执行了一条 API 测试 / When 查看执行记录 / Then 可以看到完整的请求头/请求体/响应头/响应体/状态码/耗时

**US-P1-7: UI 测试异步执行**
- As a 测试工程师, I want UI 自动化异步执行且不阻塞页面, so that 提交测试后可以继续其他操作
- Given 提交了一个 UI 测试任务 / When 任务在后台执行 / Then 页面不阻塞，可查看进度，完成后通知

### Phase 3 — P1 待验证不一致项 (7 项复核)

**US-V-1~7: Backlog vs 验收报告不一致复核**
复核以下 7 项（每项产出验证结论：实际存在/实际缺失/部分存在）：
1. 缺陷状态机+评论+附件
2. 用例评审流程 (C3)
3. 用例版本历史 (C4)
4. Xmind/Mindmap 导入导出 (C2)
5. 报告 PDF/Excel 导出 (R1)
6. 多计划趋势分析 (R2)
7. 质量门禁 (R3)

### Phase 4 — P2 增强 (11 US)

**US-P2-1**: 蓝湖原型路径灵活配置（替换硬编码）
**US-P2-2**: Xmind/Mindmap 导入导出支持
**US-P2-3**: 用例版本历史追溯
**US-P2-4**: CI/CD 质量门禁检查点
**US-P2-5**: 验证码/SSO/密码找回安全基线
**US-P2-6**: 移动端响应式适配
**US-P2-7**: 自定义仪表盘
**US-P2-8**: 审计日志导出
**US-P2-9**: 项目模板/归档/克隆
**US-P2-10**: 用户组织/部门树
**US-P2-11**: 报告模板可配置

### Phase 5 — 工程债务 + C-CONDITIONS 清理

**US-D-1**: `npm audit` 17 漏洞修复（2 critical + 7 high → 0）
**US-D-2**: develop/main 分支保护规则（至少 1 个 required check）
**US-D-3**: 9 个预存测试失败修复（CaseDrawer/DebugTab/testcase）
**US-D-4**: Ruff 全规则违规逐步修复（201 → ≤50）
**US-D-5**: `create_case` 内部 `db.commit()` 与 `transaction()` 冲突解决
**US-D-6**: C-CONDITIONS 22 个可本地处理的 Open 项逐一关闭或升级

### Phase 6 — 模块联动 Phase 1 (L1-L5)

**US-L-1**: Swagger 导入解析（上传→解析→展示路径列表）
**US-L-2**: 需求-API 语义映射（AI 匹配 REQ 与 Swagger endpoint）
**US-L-3**: AiResultModal Tab 切换（功能/API/UI 三 Tab）
**US-L-4**: 用例 `source_req_id` 追溯链补全
**US-L-5**: 导入后自动创建测试计划选项

## 5. 技术考量

| 依赖 | 状态 | 说明 |
|------|------|------|
| ffprobe/ffplay | 需安装 | P0-1 依赖；Windows 下需 ffmpeg 套件 |
| imagehash | 可选 | P0-3 screenshot 对比；ImportError 时优雅降级 |
| Swagger parser | 需引入 | P1-1 依赖 `openapi-schema-validator` 或等效库 |
| PDF/Excel 生成库 | 需引入 | P1-3 依赖 `weasyprint`/`openpyxl` |
| npm 依赖升级 | 有风险 | D-1 可能引入 breaking changes |

**已知风险**：
- 批量执行可能触发数据库连接池耗尽 → 需要并发控制
- Swagger 解析兼容性：不同版本/不规范文档 → 需要健壮的错误处理
- UI 异步执行需要 BackgroundTasks 或 Celery → 评估方案

## 6. 上线计划

| 阶段 | 受众 | 内容 | 成功门槛 |
|------|------|------|---------|
| Phase 1 | 内部测试 | P0 阻塞修复 | 3/3 完成 |
| Phase 2 | 内部测试 | P1 功能缺口 | 7/7 完成（不含 staging 依赖） |
| Phase 3 | 内部测试 | 不一致项复核 | 7/7 有结论 |
| Phase 4 | 内部测试 | P2 增强 | ≥8/11 |
| Phase 5 | 内部测试 | 工程债务 | npm 高危清零 + 测试全部通过 |
| Phase 6 | 灰度 | 模块联动 | L1-L5 可用 |
