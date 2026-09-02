# Batch 209 — 执行链专门批次（C1/C2/C6b）— PRD Summary
> **Product (🟦)** | Date: 2026-09-02 | Status: Approved

## 1. 问题陈述
Batch 207/208 完成 AI 生成与信任链后，执行链仍有三处断裂（ADR-0022 C1/C2、ADR-0023 C6b）：
1. **C1 IR 方言与执行路由不一致**：ActionPlanner/registry 产出 browser/assertion 命令，但 Temporal `execute_commands` activity 把所有命令当 HTTP 执行（无视 driver）→ browser 命令会被静默误跑成 GET base_url+""；`BrowserDriver`（真 Playwright IR 执行器）在场景 run 链路中零引用。
2. **C2 binding 无自动物化**：oracle 需人工绑定；plan 的 observations 与 oracle 的对应关系没有在审批时自动生成 binding，G4 信任门仍要靠手工。
3. **C6b 门控迁移**：无 DB 上下文端点（agent 等）仍只看 env settings，未走项目级 resolve。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| execute_commands 按 driver 分派（api→HTTP；browser→运行时或显式 BLOCKED） | 全当 HTTP | 分派 | 单测 |
| browser 命令无运行时不再静默误跑 HTTP | 误跑 | BLOCKED(no_browser_runtime) | 单测 |
| plan approve/activate 时自动物化 APPROVED oracle 的 binding（observations 匹配） | 无 | 有且幂等 | 单测 |
| agent 等无 DB 端点：有项目上下文时走项目级门控 | env-only | 项目优先 | 单测 |

## 3. 非目标（本次不做）
- 不接真实浏览器 Playwright 到 Temporal 常驻 worker（BrowserDriver 已在 v33 实现；接入需真实 UI 环境，另批）。本批让“browser 命令”在无运行时下显式 BLOCKED，杜绝误跑。
- 不改前端；不新增 DB 表/迁移。

## 4. 用户故事 + 验收标准
- As a 测试工程师, I want 执行器按命令 driver 路由，so that browser 命令不会被当成 HTTP 误请求。
  - 验收：api driver 命令照常 HTTP；browser 命令无运行时 → 步骤 BLOCKED(no_browser_runtime) 且不发 HTTP；assertion 命令不在 execute 阶段执行（由 evaluate_oracles 负责）。
- As a 测试工程师, I want 审批 plan 时自动物化 oracle binding，so that 信任门不再纯手工。
  - 验收：approve/activate 后，plan observations 匹配的 APPROVED oracle 自动生成 ACTIVE binding（幂等）；不匹配的保持未绑定并走 fail-fast。
- As a 平台管理员, I want 无 DB 端点也尊重项目 AI 配置，so that 门控不再只有 env。
  - 验收：带 project 上下文时按 resolve 判定；无 project 回退 env。

## 5. 技术考量
- 判定：执行语义变更/新行为 → **完整批次**。
- 风险：execute 分派改动触碰 v31-v40 运行测试 → 以 driver 分派保持 api 兼容并全量回归把关。
- CI 域：backend + docs/adr + work-logs。

## 6. 上线计划
合入 main（required checks 全绿）→ 真实浏览器运行时接入另批（C1b）。

## 7. 技能使用
cameltv-agent-team；cameltv-bug-guard；karpathy-guidelines。
