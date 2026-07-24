# Batch 40 — PRD Summary: 剩余事项收官 + 增强补齐
> **Product (🟦)** | Date: 2026-07-24 | Status: Draft | 来源: batch-39 核查结论

## 1. 背景

Batch-39 对 100+ 未完成事项进行了全量代码核查，发现大部分已在 batch-22~37 期间实现。**实际剩余待办 12 项**，分为 P1 功能补全、P2 增强、工程收尾三类。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| P1 功能补全 | 3 | 0 |
| P2 增强补齐 | 5 | ≤2（大型功能独立排期） |
| 工程收尾 | 4 | 0 |
| CI 门禁 | vitest swallow / 无 Python lint | 全部 block 失败 |

## 3. Phase 1 — P1 功能补全 (3 项)

### US-P1-1: 质量门禁 CI/CD 集成
- As a 发布负责人, I want CI/CD pipeline 可以查询质量门禁状态, so that 不达标的构建被自动阻止
- 当前: `QualityGateConfig` 模型 + `_compute_gate()` 评估已存在，缺 webhook 端点
- Given CI 调用 `GET /api/v1/reports/{id}/gate` / When 门禁不通过 / Then 返回非 200 状态码阻止 pipeline
- **后端**: 新增 `/reports/{id}/gate/check` 端点，返回 `{"blocked": true/false, "details": [...]}`
- **估时**: 2h

### US-P1-2: 模块联动 — 导入自动创建测试计划
- As a 测试工程师, I want Swagger 导入后可选自动创建测试计划, so that 接口用例不散落在用例库中
- 当前: ImportDialog 仅有 `generate_cases`，无测试计划创建
- Given 确认导入 / When 勾选"创建测试计划" / Then 自动创建计划并关联导入的用例
- **后端**: confirm 接口增加 `create_plan: bool` + plan_name；**前端**: ImportDialog 增加 checkbox
- **估时**: 3h

### US-P1-3: 模块联动 — 需求-API 语义映射升级
- As a 测试工程师, I want AI 语义匹配需求功能点与 API endpoint, so that 关联准确率高于关键词匹配
- 当前: `requirement_service.match_api_endpoints()` 基于关键词打分，非 LLM
- Given 一个需求文档 / When 执行语义映射 / Then 使用 LLM embedding 计算功能点描述与 endpoint summary 的相似度
- **后端**: 在 match_api_endpoints 中增加 LLM embedding 分支（feature flag 控制）
- **估时**: 4h

## 4. Phase 2 — P2 增强补齐 (5 项)

### US-P2-1: 审计日志导出（前端按钮）
- 后端 `GET /audit-logs/export` 已在 batch-39 实现，补前端下载按钮
- **前端**: system 审计日志页增加"导出 CSV"按钮
- **估时**: 1h

### US-P2-2: C-CONDITIONS 批量关闭（17 项本地可处理）
- 逐项核查 17 个 Open C-CONDITIONS，已完成则标记 Closed，未完成则纳入后续 batch
- 高优先级: C21-P1-2 (三个服务单测)、C21-P2 (task_worker 5 个 bug)
- **估时**: 4h（含 C21-P1-2 写测试）

### US-P2-3: npm 漏洞清零
- 当前: 14 漏洞（6 moderate, 6 high, 2 critical）
- js-yaml 可安全升级 (`npm update js-yaml`)
- esbuild/vite → 需评估 vite 6→8 升级影响
- hono/@modelcontextprotocol/sdk → 需评估 shadcn 升级影响
- **估时**: 2h（含兼容性测试）

### US-P2-4: 移动端响应式适配
- 核查当前页面在小屏下的表现，修复明显破损的布局
- **估时**: 3h（核查 + 修复关键页面）

### US-P2-5: 验证码/SSO/密码找回安全基线 (P2-5)
- 核查登录安全：是否支持验证码、SSO 集成点、密码找回流程
- 若有缺口，实现最小可行版本
- **估时**: 3h

## 5. Phase 3 — 工程收尾 (4 项)

### US-D-1: 前端 vitest 测试修复 + CI 强制通过
- batch-39 已移除 `|| echo` swallow，但需确认 vitest 实际全绿
- 运行 `npx vitest run` 修复失败用例
- **估时**: 2h

### US-D-2: 后端 pytest 预存失败清零
- 运行 `pytest tests/ -v` 确认 9 个预存失败确实已修复（C25v2-C1 Closed）
- 如有残留失败，修复或标记 skip with reason
- **估时**: 1h

### US-D-3: Ruff 全量扫描 + 渐进修复
- batch-39 已添加 ruff 配置，执行首次全量扫描
- `ruff check backend/ --statistics` → 优先修复 F (pyflakes) 和 B (bugbear)
- 目标: F 错误清零，B 错误 ≤10
- **估时**: 3h

### US-D-4: 报告模板可配置 (P2-11)
- 核查 report_template 模型是否存在、前端是否可编辑模板
- 若缺失，实现最小版本：模板 CRUD + 报告生成时选择模板
- **估时**: 3h

## 6. 非目标（排入 batch-41+）

| 项 | 原因 |
|----|------|
| 自定义仪表盘 (P2-7) | 需 Widget 模型 + 拖拽布局设计，独立 PRD |
| 项目模板/归档/克隆 (P2-9) | 需 schema 变更 + 迁移脚本 |
| 用户组织/部门树 (P2-10) | 需新模型 + RBAC 联动设计 |
| source_req_id 显式字段 (L4) | source_doc_id 已满足追溯需求，低优先级 |
| C-CONDITIONS staging/设备依赖项 (6 项) | 需 staging 环境或物理设备 |
| 5 主题视觉回归 (C24-C3) | 需人工设计走查 |

## 7. 估时汇总

| Phase | 项目 | 估时 |
|-------|------|------|
| P1 功能补全 | 3 项 | 9h |
| P2 增强补齐 | 5 项 | 13h |
| 工程收尾 | 4 项 | 9h |
| **合计** | **12 项** | **~31h (约 4 工作日)** |

## 8. 技术考量

- **ruff 首次扫描**: 预计 150-200 违规，优先修复 F 级（pyflakes 未定义名称/未使用导入）
- **LLM embedding**: 复用现有 DeepSeek API，需评估延迟和成本
- **vite 升级**: 6→8 涉及主要版本跨越，需在独立分支验证
