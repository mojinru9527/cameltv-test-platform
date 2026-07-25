# Batch 43 — PRD Summary
> **Product (🟦)** | Date: 2026-07-25 | Status: Draft

## 1. 问题陈述

test-platform-v2 经历 42 个 batch 的快速迭代后，已具备 24 个前端页面、34 个后端数据模型、50+ 服务模块。但在高速交付中：
- **各模块缺乏端到端功能验收**：很多页面只在 Dev 本地跑通过，没有系统性地逐功能点验证；
- **逻辑漏洞积累**：边界条件、异常路径、空状态、权限边界等未系统覆盖；
- **C-CONDITIONS 积压**：32 个 Open 条件中，有 P1 项长期未被归位（C27-C1/C3/C4、C31-2 等）；
- **上次批量验收是 batch-34**（约 3 周前），其间 batch 35-42 新增了大量代码。

**用户痛点**：测试人员在使用平台时可能遇到未预期的行为；开发人员不知道自己写的功能在生产环境实际表现如何。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 核心模块功能验收通过率 | 未知 | ≥90% (每个模块≥80%检查点PASS) | batch-43 结束 |
| 发现的 P0/P1 缺陷数 | 未知 | 全部修复或记录为 C-condition | batch-43 QA 报告 |
| C-CONDITIONS 归位 | 32 Open | ≥8 个 Close（P1 优先） | batch-43 Leader Verdict |
| 逻辑漏洞覆盖 | 未知 | 每个核心模块≥3 条异常路径已验证 | batch-43 QA 报告 |
| 前端硬门禁 | 未知 | typecheck + build 零错误 | 每 Slice |

## 3. 非目标（本次不做）

- ❌ **新功能开发**：不新增产品特性，这纯粹是验收/修复 batch
- ❌ **需要 staging 环境的验证**：C27-C1/C2/C4（准确率/性能/覆盖率）依赖 staging，本次不覆盖
- ❌ **需要物理设备的验证**：CP-C1/CP-C2（Android/iOS 真机）排除
- ❌ **生产环境验证**：C31-3 已确认无法提供生产地址/账号，本次不追
- ❌ **大规模重构**：发现架构级问题时记录为 C-condition，不在此 batch 重构
- ❌ **文档新鲜度检查**：`cameltv-doc-check` 留给月度 cron
- ❌ **蓝湖 MCP / deploy / tests 目录**：不在 test-platform-v2 scope 内

以下 C-CONDITIONS 明确排除（附理由）：
- C27-C1/C2/C4：依赖 staging 环境 → 转为 batch-44 条件
- CP-C1/CP-C2：需物理设备 → 保持 Open，加注 BLOCKING
- C31-3：安全策略限制 → 标记 Closed-wontfix
- batch-18-C6/C7/C8/C9/C11/C14：P2/P3 孤儿 → 下批次归位
- C24-C1/C2/C3：5 主题视觉 → 纳入 Design 走查

## 4. 用户故事 + 验收标准

### 验收策略：按模块分层

将 24 个前端页面分为三层：

**🔴 Tier 1 — 核心链路（7 模块，必须全量验收）**：
测试用例 → 测试计划 → API 测试 → UI 测试 → 执行调度 → 测试报告 → 缺陷管理

**🟡 Tier 2 — 支撑模块（9 模块，重点抽检）**：
需求管理、知识中心、数据集、环境管理、集成管理、通知中心、版本使命、项目设置、系统管理

**⚪ Tier 3 — 辅助模块（8 模块，门禁级别检查）**：
登录、工作台、Agent 工作台、性能测试、发布包、脑图、链路追踪、特殊页面

### US-1: 核心链路端到端验证（Tier 1）
As a 测试工程师, I want to walk through the complete test lifecycle (用例→计划→执行→报告→缺陷), so that I am confident every step works without logic gaps.

验收：
- Given 平台已部署 / When 依次操作：创建用例→加入计划→API执行→查看报告→提单缺陷 / Then 每个步骤成功且数据一致
- Given 异常输入（空标题、超长文本、非法ID）/ When 提交 / Then 有明确错误提示而非 500/白屏

### US-2: 支撑模块功能完整性验证（Tier 2）
As a 平台管理员, I want key support modules verified for correctness, so that I can trust the platform's auxiliary capabilities.

验收：
- Given 需求管理 / When CRUD 操作 + 蓝湖导入 / Then 状态流转正确
- Given 知识中心 / When 知识入库→检索→图谱展示 / Then 数据一致、UI 不崩溃
- Given 通知中心 / When 触发各类事件 / Then 通知送达、格式正确

### US-3: 全模块逻辑查漏补缺
As a QA engineer, I want to systematically check every module for logic gaps (empty states, error handling, edge cases, permission boundaries), so that users don't encounter unexpected behaviors.

验收：
- Given 每个模块 / When 检查加载态/空态/错误态/边界值 / Then 每态有合理 UI 反馈
- Given RBAC 权限矩阵 / When 切换不同角色 / Then 菜单/按钮/API 均按权限展示

### US-4: C-CONDITIONS 归位
As a Product owner, I want to close or re-assign the most impactful Open C-conditions, so that technical debt is visible and managed.

验收：
- Given 32 Open C-conditions / When batch-43 结束 / Then ≥8 个已 Close（P1 优先）
- Given 剩余 Open 条件 / When Leader Verdict / Then 每个有明确的归位计划

## 5. 技术考量

| 依赖 | 状态 | 风险 |
|------|------|------|
| Docker Desktop | 当前未运行 | 低 — 可用 `uvicorn` + `npm run dev` 本地验证 |
| test 环境 (*.elelive.cn) | 非内网不可达 | 中 — API 测试模块依赖外部 Swagger；用本地 spec 替代 |
| Alembic 迁移 | 未知是否一致 | 中 — 需运行 `alembic upgrade head` + `alembic check` |

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| Slice 1-3: Tier 1 验收+修复 | Dev+QA | 7 核心模块 ≥90% 检查点 PASS |
| Slice 4-5: Tier 2 抽检+修复 | Dev+QA | 9 支撑模块 ≥80% 检查点 PASS |
| Slice 6: Tier 3 门禁+收尾 | Dev+QA+Leader | typecheck+build 零错误，C-conditions 归位 |
