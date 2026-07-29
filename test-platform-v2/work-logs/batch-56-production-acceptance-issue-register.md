---
title: "Batch 56 生产级验收缺陷登记"
owner: "qa-team"
created: "2026-07-29"
last_reviewed: "2026-07-30"
status: "active-needs-work"
tags: ["batch-56", "production-acceptance", "issue-register", "real-input"]
related:
  - "batch-56-production-acceptance-qa-report.md"
  - "../../docs/work-logs/batch-56-production-acceptance-execution-matrix.md"
  - "evidence/batch-56-production-acceptance/README.md"
  - "batch-56-production-acceptance-leader-verdict.md"
---

# Batch 56 生产级验收缺陷登记

## 1. 登记口径

本登记以 Batch 56 QA 报告的 `NEEDS WORK` 结论为准。`FAIL` 表示已在授权
边界内执行且实际结果不满足预期；`BLOCKED` 表示缺少外部服务、授权、设备或
可追溯输入，未执行的主路径不计为通过。

外部地址、账号、密码、Token、Cookie、Authorization、内部网络信息和原始
生产数据不进入仓库。下表仅使用 Batch 56 真实输入清单中的逻辑 ID。

## 2. 未关闭 P0/P1

| ID | 优先级 | 状态 | 外部输入 | 实际问题 | 责任边界 | 成功标准 |
| --- | --- | --- | --- | --- | --- | --- |
| `B56-B01` | P0 | `FAIL` | `B56-R0-TEST-SITES` | OpenVPN 边界内节点 1–5 通过，节点 6 浏览器返回 503 | 测试环境所有者 / QA | 服务恢复；在同一授权网络和浏览器矩阵复测节点 6，页面、关键内容、控制台和网络均满足预期 |
| `B56-B02` | P0 | `FAIL` | `B56-R0-TEST-OPENAPI`、`R0-OAS-SIX-LIVE` | 实际网关仅 15 paths / 17 operations，不能证明六服务完整契约 | 六服务负责人 / QA | 提供六份当前实时契约，或六份带来源、采集时间、SHA-256 和脱敏记录的 R1 快照；六份均可解析并完成覆盖对账 |
| `B56-B03` | P0 | `FAIL` | `B56-R0-TEST-OPENAPI` | 声明受保护的测试 API 对无效 Bearer 仍返回成功，安全声明与实现不一致 | API/安全负责人 / QA | 明确公开与受保护接口清单；OpenAPI 与实现一致；受保护接口拒绝无效凭据，合法最小权限凭据成功，公开接口不虚假声明鉴权 |
| `B56-B04` | P0 | `FAIL` | `B56-R0-ADMIN-TEST` | 验证码和短信接口返回业务成功，但浏览器未形成 Cookie/storage 会话且停留登录页 | 运营后台负责人 / QA | 真实浏览器登录后建立预期会话并跳转到受保护页面；刷新仍有效，注销后会话失效；全程保留脱敏网络证据 |
| `B56-B05` | P0 | `BLOCKED` | `B56-R0-AI` | 已确认只允许脱敏文本和脱敏图片外发，但真实 API Key 和本地 OCR 运行时尚未配置 | AI/OCR 服务负责人 / QA | 使用获授权、可追溯 provider 完成最小脱敏输入；记录真实调用和输出来源；AI/OCR 主断言不依赖规则 fallback 或 mock |
| `B56-B06` | P1 | `BLOCKED` | `R0-MEDIA-DEVICE` | 无获授权设备代理、ADB/SoloX 固定运行时和采样窗口 | 性能/设备负责人 / QA | 部署经鉴权设备代理并锁定采集版本；在授权设备和窗口完成真实启动、采样、停止、持久化与清理，指标可回溯到设备 |
| `B56-B07` | P1 | `BLOCKED` | `B56-R0-ELK`、`R0-ELK-READONLY` | 已给出执行时刻向前 15 天的数据查询范围和向后 15 天的执行授权窗口；仍缺 ELK 入口、只读身份、索引/服务名和当前 trace 证据 | 可观测性负责人 / QA | 在批准时间窗用只读权限完成平台 traceId 到日志的脱敏关联；记录索引范围、查询时间和可复核结果 |
| `B56-B08` | P0 | `BLOCKED` | `B56-R0-LEGACY-PG`、`R0-LEGACY-PG` | 无旧 PostgreSQL 脱敏快照，用户已选择正式豁免；批准人、批准日期和风险接受说明尚未签署 | 产品/数据库风险负责人 / QA | 形成范围明确的豁免记录；签署后状态记为 `WAIVED` 而非 `PASS`，并保留未来真实迁移前补测触发条件 |
| `B56-B09` | P0 | `BLOCKED` | `B56-R0-USER-DESIGN`、`B56-R0-ADMIN-DESIGN` | 已提供 3 个用户端 PC 页面和 APP_UI/WEB_UI 蓝湖入口；用户页面可加载，但蓝湖需要登录/权限，运营后台设计源仍未确认 | 产品/设计负责人 / QA | 登录后确认项目权限和版本，采集页面树、截图/OCR、来源时间与 SHA-256；补充或确认当前运营后台设计源 |
| `B56-B10` | P1 | `FAIL` | `B56-R0-PROD-SITES` | 新提供的 3 个用户端核心页面在 PC 视口可加载，但未在本轮切换 vpn07 或覆盖全部登记节点，不能替代原失败集合复测 | 生产环境所有者 / QA | 在批准窗口和 vpn07 边界内仅用 GET/HEAD 复测；全部登记节点可加载有效业务内容且无阻断性控制台/网络错误 |

## 3. 状态治理

- `B56-B01`～`B56-B10` 全部保持未关闭；没有一项因本地测试、HTTP 200、
  mock、历史报告或代码存在而自动关闭。
- 任一状态变化都必须附当前输入、执行时间、固定代码 SHA、预期/实际、
  脱敏证据索引和清理说明。
- 关闭全部 P0/P1 仍不是单独的生产放行依据；执行矩阵 A01–A12 与 R0/R1
  P0/P1 原子结果也必须满足 `READY` 规则。
