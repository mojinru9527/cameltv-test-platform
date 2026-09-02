# Batch 210 — 收尾（C1b/C2b + 测试基建）— PRD Summary
> **Product (🟦)** | Date: 2026-09-02 | Status: Approved

## 1. 问题陈述
- **C1b**：真实浏览器执行仍未被注入场景 run 链路（`register_browser_runner` 空置；BrowserDriver 已实现但未接线）。
- **C2b**：DB/EVENT/LOG oracle 在 plan 无显式 observation 时仍只能人工绑定。
- **测试基建噪音**：全量 pytest 每批 6 项环境/基线失败（lanhu-mcp 子模块缺失 5 项、notification_channel 夹具缺失 1 项）——本地无子模块开发体验差且掩盖真实回归。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| 本地全量 backend pytest 失败数 | 6 | 0 |
| BrowserDriver 通过 register_browser_runner 可被场景 run 调用（能力检测） | 无接线 | 有 adapter + 测试 |
| C2b：无 observation 时按 oracle_type/单命令兜底物化 | 无 | 保守兜底 + 测试 |

## 3. 非目标
- 不要求真实 Playwright/凭据在 CI 常驻运行（能力检测降级仍 BLOCKED，但提示 browser_runner_available=false）。
- 不改 lanhu-mcp 子模块内容。

## 4. 用户故事/验收
- 本地开发者（无 lanhu-mcp 子模块）跑全量 pytest 得到 0 失败（相关测试明确 skip 并给出原因）。
- 配置了 Playwright 的运行时，场景 browser 命令可被 BrowserDriver adapter 执行；未配置时 BLOCKED 且原因含 capability。
- DB oracle 且 plan 单一 data/api 命令时自动补 DB_COLUMN binding。

## 5. 技术考量
完整批次（新接线+行为）；后端 + deploy 测试域；无迁移/无 API 路由变更。
