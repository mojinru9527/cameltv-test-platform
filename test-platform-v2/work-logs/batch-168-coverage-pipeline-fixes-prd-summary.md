# Batch 168 — PRD Summary
> **Product (🟦)** | Date: 2026-08-13 | Status: Approved（承接 Batch 167 C167-2 真实复测缺陷）

## 1. 问题陈述
Batch 167 合入后按用户真实版本（16.0.0，18 模块/119 功能点）在生产跑端到端基线，主链路可运行，但「指定版本 → 提取 → 三类型用例 → 计划关联 → 60% 模块覆盖」目标未达成。证据（work-logs/evidence/batch-167/）：
- 覆盖矩阵每行均为全局计数 8082/34/0，723 个模块全部误标 P0/P1，覆盖率恒 0%（D1）。
- 版本分母回退到全项目 723 模块，非版本 18 模块（D2）。
- 接口生成报告 7 条、实际可见 0 条：upsert 命中软删除行 + 5 模板互相覆盖（D3）。
- UI 用例无法为已导入功能用例生成（D4），三类型关联缺 UI。
- 版本详情 Tab JSX 错位，出现「三类型覆盖版本差异」合并标签（D5）。
- auto_ui 失败信息仅「未知」（D6）。
- API/UI 共用单一执行环境，无法分别指向 api.cameltv.live / www.camel1.tv（D7）。
- 端点匹配只命中 1/18 模块（实时赔率），接口用例无法覆盖多数模块（D8）。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 16.0.0 三类型覆盖 | 0/723（失真） | ≥60%（分母=18 个版本模块；P0/P1 模块单独统计） | 合入后真实复测 |
| 接口生成可见用例 | 0/7 | 生成 N、可见 N（无软删除污染） | 合入后 |
| UI 变体 | 0 | 405 条中 P0/P1 有步骤全部生成 UI 用例 | 合入后 |
| auto_ui 执行 | 5/5 执行 0 skip | 执行失败原因可读（含 stdout/断言） | 合入后 |
| 覆盖矩阵正确性 | 每行=全局 | 每行=该模块自身计数 | 合入后 |

## 3. 非目标（本次不做）
- 不做新的一键全自动编排页面（Phase 4）。
- 不改蓝湖证据包/提取质量门禁本体；本次只消费既有 doc#11 提取结果。
- 不伪造执行：无登录态/不可达仍如实失败（承接 C167-1）。
- 不新增第三方依赖、不改数据库结构（用既有字段/表）。

## 4. 用户故事 + 验收标准
- As 测试负责人, I want 版本覆盖矩阵逐模块真实统计, so that 每个模块的功能/接口/UI 与执行数可复核。
  - Given 发布包有模块树 / When 打开三类型覆盖 / Then 每行=该模块计数、P0/P1 仅按该模块用例优先级判定。
- As 测试负责人, I want 发布包关联其需求文档模块树, so that 分母=版本模块而非全项目。
  - Given 发布包绑定需求文档 / When 计算覆盖 / Then total_modules=该文档模块数（无树时优先用该版本已导入用例的模块）。
- As 测试人员, I want 接口生成真实落库, so that 生成报告与实际可见一致。
  - Given 项目已导入端点 / When 生成 / Then 不更新软删除行、模板变体各自独立、可见数=生成数。
- As 测试人员, I want 已导入功能用例也能补生成 UI 变体, so that 老版本数据也可三类型关联。
  - Given 需求已有已导入 P0/P1 功能用例 / When 导入时开启 create_ui_cases / Then 为其生成 UI 变体且幂等。
- As 测试人员, I want 模块级端点匹配, so that 接口用例覆盖大多数版本模块。
  - Given 模块名与已导入端点可对齐 / When 生成 / Then 每模块至少 1 个真实端点绑定（读安全优先、置信度阈值、可去重）。
- As 测试人员, I want 执行失败可读, so that 不用翻容器日志。
  - Given UI 执行失败 / When 查看执行记录 / Then notes 含错误摘要或 stdout 尾部。
- As 测试人员, I want API 与 UI 分环境执行, so that 同一计划两类用例各打各的目标。
  - Given 计划执行 / When 选择 API 环境 + UI 环境 / Then API 用 API 环境 base_url、UI 用 UI 环境 base_url。

## 5. 技术考量
- 覆盖矩阵 key 从 (module_id,type) 改为 (module_id,name,type)，修正 fallback id=None 冲突。
- 接口生成 upsert：existing 过滤 is_deleted=false；模板变体用 (method,path,title) 判定已有，或每变体新增唯一 title 行。
- UI 变体回填复用 import_cases 的幂等键 (title,module)，create_ui_cases 时同时扫描 source_doc_id 全部 P0/P1 已导入用例。
- 模块级匹配：对未命中模块用模块名 token/双字重叠匹配端点，仅 GET/只读安全优先，confidence>=0.4，每模块最多 1 端点，跨模块去重。
- 执行环境：ExecuteAllBody 增 ui_environment_id（可选，缺省回退原 environment_id）；前端执行弹窗加 UI 环境选择。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全队 | 后端 ruff/import/alembic/全量 pytest；前端 typecheck/lint/build/vitest；CI required 全绿 |
| 真实复测 | 测试负责人 | 16.0.0：接口可见用例、UI 变体、计划三类型关联、auto_ui 执行、覆盖 ≥60% 截图证据 |

## 7. 技能使用
cameltv-bug-guard → 后端 envelop/迁移/StaticPool、前端 useEffect/Radix Select；cameltv-ui-conventions → Tab/Select 规范；test-case-design → 接口生成口径。
