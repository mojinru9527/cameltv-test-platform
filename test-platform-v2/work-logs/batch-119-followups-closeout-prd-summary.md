# Batch 119 — PRD Summary（收尾与工具链清理：C118-1 + C104-3/C105-3 + C105-4 + C114-1 + C102-4 前端）

> **Product (🟦)** | Date: 2026-08-07 | Status: Review | **mode: full**
> 判定：含新能力（C114-1 拓扑缺口自动提示、C102-4 前端差异面板）→ 完整批次六件工件。

## 1. 问题陈述

1. **C118-1 历史 HARD 未清**：`scan-common-bugs` 3 个 `except: pass` 静默吞异常（`ai_service.py:324`、`xhr_capture_service.py:74/95`），掩盖真实错误且 Batch 118 已登记。
2. **C104-3/C105-3 契约漂移未收敛**：`frontend/src/types/api.d.ts` 自 batch-106 后未再生成，`package.json` 中 openapi-typescript 为 `^7.4.2`（未锁定），28k 行漂移根因（工具版本差异）未验证。
3. **C105-4 走查证据缺失**：「停用组织后成员入口提示」UI 与组织项目联动截图证据未产出。
4. **C114-1 拓扑缺口不可见**：交互拓扑（38 节点/119 边）与交互用例覆盖矩阵的缺口需人工核对，无自动提示。
5. **C102-4 差异标注仅后端**：batch-118 已交付 `production-diff` 端点，但前端无展示，测试人员无法在平台查看生产 vs 原型差异。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| scan-common-bugs HARD | 3 | 0（本批处理或逐条豁免登记） | 本批 |
| openapi-typescript 版本 | ^7.4.2（未锁定） | 锁定精确版本并重生成 api.d.ts，漂移根因记录 | 本批 |
| C105-4 走查 | 无证据 | 停用组织 UI 截图 + 组织项目联动验证 | 本批 |
| C114-1 缺口提示 | 无 | 拓扑边 vs 用例覆盖矩阵缺口自动提示（后端） | 本批 |
| C102-4 前端面板 | 无 | 需求页生产差异标注面板（复用 production-diff） | 本批 |

## 3. 非目标（本次不做 + 豁免理由）

- **C106-2 邀请链接灰度观察一周**：时间窗口未到（08-13 满周），保持 Open。
- **C117-2 异步多 worker**：依赖外部队列/Redis 基建，保持 Open。
- **外部 Deferred 项**（C101-2/3、C74-2/C95-1/C111-4、C111-1、CP-C2/C84-1、C95-2、C65-3、C63-2、C27-C1~4、batch-18-C7/C21-P1-5）：解除条件未满足，不触碰。
- **C99-1（PERF-OPT）与 C96-1（C27-C1~4 本地全栈验证）**：大项 Epic，保持 Open。
- **C114-1 前端缺口展示**：本批仅后端缺口提示能力，前端提示 UI 转下批（若时间允许则最小化实现）。

## 4. 用户故事 + 验收标准

- **US-1 C118-1**：As a Dev, I want 异常不被静默吞掉 so that 问题可观测。
  验收：Given ai_service/xhr_capture_service 的 except:pass / When 修复后 / Then 改为日志+合理处理，scan-common-bugs HARD=0，相关单测通过。
- **US-2 C104-3/C105-3**：As a Dev, I want api.d.ts 契约稳定 so that 前端类型与后端一致。
  验收：Given package.json 锁定 openapi-typescript 精确版本 / When 重新生成 / Then api.d.ts 更新且漂移根因记录（工具版本差异说明），typecheck/build 通过。
- **US-3 C105-4**：As a 测试工程师, I want 停用组织后的提示与联动有据可查 so that 验收可信。
  验收：Given 停用组织场景 / When 浏览器走查 / Then 截图证据 + 组织项目联动验证记录。
- **US-4 C114-1**：As a 测试工程师, I want 拓扑边与用例覆盖缺口自动提示 so that 交互覆盖无遗漏。
  验收：Given 拓扑边清单 + 交互用例清单 / When 调用缺口提示接口 / Then 输出未覆盖边清单 + 覆盖率，单测覆盖。
- **US-5 C102-4 前端面板**：As a 测试工程师, I want 在需求页看到生产 vs 原型差异 so that 差异追踪无需脚本。
  验收：Given 需求页选择文档/发布包 / When 打开差异面板 / Then 显示 new/matched/missing 清单，vitest 通过。

## 5. 技术考量

- C118-1：三处 except 均为非关键路径（AI 输出补全、XHR 样本补充字段）→ 改为 `logger.warning(...)` + 降级默认值，不改业务行为。
- C104-3：`package.json` devDependency 改为精确版本（如 `7.4.2`），重新 `npm run gen:api`（后端本地 8000 或 OpenAPI 文件）；若本地无法起后端则用 CI 或临时 fastapi 导出，记录漂移对比。
- C114-1：新服务 `interaction_coverage_service`：输入拓扑边/用例清单（复用 batch-113 interaction-paths.json 结构），输出缺口边 + 覆盖率；端点 `GET/POST /interaction-coverage/gaps`。
- C102-4 前端：`requirement` 页新增 ProductionDiffPanel（复用 batch-118 `production-diff` 端点），最小列表 + 徽标。
- C105-4：Playwright 走查生产/本地组织管理页，产出截图证据。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main → Railway 自动部署 | 全平台 | HARD=0、typecheck/build/vitest/pytest 全绿 |
| 部署后复测 | QA | C105-4 截图 + 新端点/面板可用 |

## 7. 技能使用

- `cameltv-agent-team`：六部门流水线（本工件所属）。
- `cameltv-bug-guard`：修复 except:pass 时避坑。
- `cameltv-ui-conventions`：C102-4 前端面板、C105-4 走查。
- `playwright-cli`：C105-4 UI 走查截图。
- `cameltv-api-test`：如涉及接口验证。
