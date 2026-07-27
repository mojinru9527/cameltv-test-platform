# Batch 37 — 测试平台 GA 补缺 + 工程债务清理 PRD

> **Product 部门** | 2026-07-23 | 版本 2.0（精简版，基于代码现实核查）

## 前置声明

本 PRD 为 batch-37 的 **第二版**。第一版基于 batch-34 验收报告制定，后经全面代码核查发现报告中标记为"缺失"的功能有 **15/19 项已在后续迭代中实现**。用户明确指示"忽略不一致的地方"，本版仅保留 **真正缺失的 4 项功能 + 2 项工程债务**。

### C-CONDITIONS 审查

已审查 [C-CONDITIONS.md](../../C-CONDITIONS.md)，本次 batch 不直接处理任何 Open C 条件（均属于其他批次范围）。本 batch 聚焦平台自有缺口。

---

## 问题陈述

测试平台 V2 经过 batch-22~36 多轮迭代，核心链路（需求→用例→计划→执行→报告）已基本可用。但代码核查发现仍有 4 个功能性缺口阻碍生产就绪：

1. **测试计划缺少批量执行入口**：现有 `auto-execute` 仅覆盖 API 用例，计划中的人工用例/UI 用例无批量操作入口
2. **测试计划缺少指派机制**：`TestPlan` 模型无 `assignee_id` 和 `due_date`，无法将计划整体指派给执行人
3. **用例无法追溯到需求功能点**：`TestCase.source_doc_id` 只能关联到需求文档，无法精确追溯到文档内的 `REQ-xxx` 功能点
4. **AI 生成用例导入后不自动创建测试计划**：导入→计划是断开的，用户需手动建计划再关联用例

同时存在 2 项可量化的工程债务需要清理。

---

## 成功指标

| # | 指标 | 目标 | 验证方式 |
|---|------|------|---------|
| M1 | 测试计划支持一键批量执行 | 覆盖 API + 人工 + UI 三类用例 | API 测试 |
| M2 | 支持计划指派 | 可设置负责人和截止日期 | 功能验证 |
| M3 | 用例可追溯到需求功能点 | source_req_id 字段写入 + 追溯矩阵显示 | 集成测试 |
| M4 | 导入用例后可选自动创建计划 | 导入→计划一步完成 | 功能验证 |
| M5 | npm audit 无 critical/high | 0 critical + 0 high | `npm audit` |
| M6 | Ruff 零违规 | `ruff check` 通过 | CI |

---

## 非目标（明确排除）

- ❌ **ffprobe 音视频检测** — 已在 `ffmpeg_service.py` + `av_check_service.py` 完整实现
- ❌ **API 生产环境保护** — 已在 `apitest.py:682` 实现（`env_type=="prod"` 权限 + `confirm_prod` 确认）
- ❌ **API 任务取消真中断** — 已在 `api_task_worker.py:77` 实现（`cancel_requested` flag）
- ❌ **UI 异步执行 + 产物归档** — 已在 `ui_runner_queue.py:39` + `ui_test.py:193` 完整实现
- ❌ **蓝湖配置化** — 已在 `config.py:137` 实现（全面环境变量配置）
- ❌ **质量门禁** — 已在 `quality_gate.py:20` 完整实现（6 维度 QualityGateConfig）
- ❌ **报告导出 (CSV/Excel/PDF)** — 已在 `report.py:159` 后端 + 前端 export dropdown 完整实现
- ❌ **报告趋势/对比** — 已在 `report_service.py:521` 实现
- ❌ **环境管理 dev/test/staging/prod** — 已在 `environment.py:17` 实现
- ❌ **OpenAPI/Swagger 导入** — 已在 `apitest.py:337` 实现
- ❌ **API 请求快照 + curl 生成** — 已在 `apitest.py:78` 实现
- ❌ **用例评审状态机** — 已在 `test_case.py:57` 实现（draft/submitted/approved/rejected）
- ❌ **用例版本历史** — `TestCaseVersion` 模型 + CRUD 已存在
- ❌ **AiResultModal UI 重做** — 已有 extraction/analysis/func 三个 Tab（用户后续优化）
- ❌ **通知触发扩展 (task_started/finished/test_result)** — 已在多个 API 中实现
- ❌ **P2 功能 (captcha/SSO, mobile, custom dashboards)** — 不属于本 batch 范围

---

## 用户故事

### Epic 1: 测试计划闭环增强

#### US-1.1 — 计划批量执行（P1）

**作为** 测试执行者
**我想要** 对测试计划中的所有用例一键批量执行
**以便** 减少逐条点击的重复操作

**验收标准：**
- [ ] `POST /api/v1/test-plans/{plan_id}/execute-all` 端点可用
- [ ] API 类型用例：自动执行并记录结果
- [ ] 人工/UI 类型用例：标记为 skip + 附注"需人工执行"
- [ ] 返回汇总：total / executed / passed / failed / skipped / details[]
- [ ] 权限：`testplan:execute`

#### US-1.2 — 计划指派负责人（P1）

**作为** 测试管理者
**我想要** 将测试计划指派给指定执行人并设置截止日期
**以便** 明确责任归属和交付时间

**验收标准：**
- [ ] `TestPlan` 模型新增 `assignee_id` (FK→user) + `due_date` 字段
- [ ] `PlanCreate` / `PlanUpdate` / `PlanOut` schema 支持 assignee_id + due_date
- [ ] 前端计划表单支持选择负责人 + 截止日期
- [ ] 计划列表/详情显示负责人姓名和截止日期

### Epic 2: 用例可追溯性增强

#### US-2.1 — 用例追溯到需求功能点（P1）

**作为** QA Leader
**我想要** 看到每个用例追溯到需求文档的哪个功能点
**以便** 在做覆盖率分析时精确定位未覆盖的需求

**验收标准：**
- [ ] `TestCase` 模型新增 `source_req_id: str` 字段（存储 REQ-xxx 标识）
- [ ] AI 生成用例导入时自动写入功能点 ID（从提取的 function_points 匹配）
- [ ] `PlanCaseOut` / 用例详情 API 返回 `source_req_id`
- [ ] 质量追溯矩阵 `/api/v1/trace` 支持按功能点粒度展示覆盖

#### US-2.2 — 导入用例后自动创建测试计划（P2）

**作为** 需求分析者
**我想要** 在导入 AI 生成的用例时自动创建对应的测试计划
**以便** 省去手动建计划→关联用例的重复步骤

**验收标准：**
- [ ] 导入 API `POST /api/v1/requirements/{doc_id}/import` 支持 `create_plan: bool` 参数
- [ ] 当 `create_plan=true` 时，自动创建 `TestPlan(name=需求标题, status=draft)`
- [ ] 所有导入的用例自动关联到新计划
- [ ] 返回新计划的 `plan_id` 和 `plan_name`
- [ ] 前端导入弹窗增加「同时创建测试计划」复选框

### Epic 3: 工程债务清理

#### US-3.1 — npm 安全漏洞修复（P1）

**作为** 平台运维者
**我想要** 修复 npm 依赖的安全漏洞
**以便** 消除已知安全风险

**验收标准：**
- [ ] `npm audit` 显示 0 critical + 0 high
- [ ] `npm run typecheck` 通过
- [ ] `npm run build` 通过

#### US-3.2 — Python 代码质量清理（P2）

**作为** 后端开发者
**我想要** 通过 Ruff linter 的所有检查
**以便** 保持代码风格一致性

**验收标准：**
- [ ] `ruff check app/` 返回 0 违规
- [ ] 自动修复 (`ruff check --fix`) 安全执行
- [ ] 手动处理剩余的语义违规

---

## 优先级排序

| 优先级 | 功能 | 理由 |
|--------|------|------|
| P0 | US-1.1 批量执行 | 执行闭环的核心缺口 |
| P0 | US-1.2 计划指派 | 团队协作的基础能力 |
| P1 | US-2.1 功能点追溯 | 需求覆盖率的精确性保障 |
| P1 | US-3.1 npm audit | 安全合规 |
| P2 | US-2.2 自动建计划 | 体验优化，可降级手动操作 |
| P2 | US-3.2 Ruff 清理 | 代码卫生 |

---

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| Alembic 迁移在 SQLite 上添加 FK 列 | 低 | SQLite 支持 ALTER TABLE ADD COLUMN |
| npm audit fix 引入 breaking changes | 中 | 逐包升级，typecheck+build 把关 |
| Ruff 自动修复改变语义 | 低 | 仅使用 `--fix` 的安全修复类别 |
