# Batch 277b-4 — 控制面无浏览器开关：PRD-lite

> **部门**：🟦 Product（lite） · **日期**：2026-11-09 · **Executor**：DeepSeek Harness
> **批次模式**：light（代码 + 文档） · **分支**：feature/batch-277b-4-browserless-control-plane（基线 `313eaa1f1`）

## 1. 问题

P0-4 要求控制面镜像无 Chromium，但除 `/uitest` 外还有三处控制面浏览器依赖（蓝湖证据截图、XHR 采集、Playground）。直接删 Dockerfile 会静默打断它们。采用用户确认的方案 **b) 控制面开关 + 显式降级**。

## 2. 成功指标

| 指标 | 阈值 | 结果 |
|------|------|:----:|
| `CONTROL_PLANE_BROWSER_ENABLED` 开关 | 1 | ✅ |
| 四处浏览器入口显式失败/降级（不静默） | 4/4 | ✅ |
| Dockerfile 无 `playwright install` | 0 命中 | ✅ |
| 镜像 ENV 默认 node + 无浏览器 | 2 | ✅ |
| 单测 | ≥6 | ✅ 7 |
| 镜像构建 + inspect | 1 | ⏳ 网络/子模块受限，发布窗口执行 |

## 3. 非目标

- 不把蓝湖截图/XHR/Playground 迁到节点（后续批次）；
- 不改生产（本次只改 main，部署在窗口内）；
- 不伪造 P0-4 evidence JSON。

## 4. DoD

- [x] 开关 + 4 处降级 + Dockerfile + 单测；
- [x] 本地 `/uitest` node E2E（277b-3 已通过）；
- [ ] 无 Chromium 镜像 inspect（发布窗口）；
- [ ] 真实生产节点复验。
