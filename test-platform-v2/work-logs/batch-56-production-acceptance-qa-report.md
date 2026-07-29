---
title: "Batch 56 测试平台全功能生产级验收 QA 报告"
owner: "qa-team"
created: "2026-07-29"
last_reviewed: "2026-07-29"
status: "needs-work"
tags: ["batch-56", "production-acceptance", "real-input", "agent-team", "qa"]
related:
  - "../../docs/work-logs/batch-56-production-acceptance-execution-matrix.md"
  - "batch-56-real-input-manifest.md"
  - "../../docs/测试平台全功能验收文档-环境链接与账号汇总.md"
---

# Batch 56 测试平台全功能生产级验收 QA 报告

## 1. 结论

**最终 Verdict：`NEEDS WORK`，不得生产放行。**

Batch 56 已关闭本地可修复的 Batch 54/55 遗留：全路由重复请求、异步取消、
脑图卸载后 NaN、性能 Mock 数据、seed 首启关系、性能跨项目越权和未鉴权
WebSocket、WebSocket 代理、启动证据错绑、生产 Compose 安全默认值、旧 volume
权限、依赖漂移与容器运行时缺失。固定代码为：

`30c76a4ddeebf485e8285ae1e8b0effc2ff71fcf`

本地平台在该干净提交上完成真实 PostgreSQL、真实登录、真实 R1 文档上传、
RBAC、桌面/移动全路由和容器验收，证据链有效。全平台仍有外部 P0/P1
失败或阻断：体育测试第 6 节点 503、六服务实时 OpenAPI 缺失、测试 API
鉴权声明与实际不一致、运营后台登录未形成浏览器会话，以及真实 AI/OCR、
真机性能、ELK、设计源证据包和旧 PostgreSQL 快照缺失。

## 2. 执行边界

- 体育生产环境仅在 vpn07 下执行，且只使用 GET/HEAD；未登录、未写入、
  未支付、未发布、未重放、未压测。
- 体育测试环境和测试 API 仅在 OpenVPN 下执行。
- 外部地址、账号、密码、Token、Cookie、Authorization 和内部网络信息
  不写入本报告；统一引用 R0/R1 逻辑 ID。
- 本地写操作使用独立 PostgreSQL 和 Batch 56 标识，均完成状态回读与清理。
- E2E 不使用 `page.route`、route fulfill、mock、skip 或虚构业务实体。

## 3. 本地功能验收

| 验收域 | 结果 | 状态 |
| --- | --- | --- |
| 健康与登录 | admin/tester 登录、`/auth/me` 成功；错误密码 401 | PASS |
| 项目隔离 | tester 访问非成员项目返回 403；性能 REST/WS 跨项目返回拒绝 | PASS |
| 真实需求 | 用户端和运营后台两份 R1 文档上传、解析、回读、审计均成功 | PASS |
| AI 提取 | 未配置 Key 时返回明确业务 400，不产生 fallback | BLOCKED |
| 全路由可达性 | desktop 30 路由、mobile 16 路由，真实后端 2/2 passed | PASS（可达性范围） |
| 历史主题/响应式/a11y 专项 | Batch 53/54/55 四组专项 4/4 passed | PASS（历史专项范围） |
| 网络请求 | StrictMode 有效 GET 单次；取消请求无 pageerror；真实错误不被吞掉 | PASS |
| 脑图 | 卸载后无 `translate(NaN,NaN)`，无跨路由异步污染 | PASS |
| 性能真实性 | 无 Mock 设备和随机指标；缺采集器时 devices/start 为 503 | PASS |
| 真机性能 | 无获授权设备代理、ADB/SoloX 和采样窗口 | BLOCKED |
| 性能安全 | Cookie、Origin、成员、权限、项目隔离、重复连接和 URL 无 JWT | PASS |
| 性能传输 | Vite 真实 101；无采集器时 `collector_error` 并清理 | PASS |
| PostgreSQL | Alembic 唯一 head、无 schema 漂移、并发回归 3/3 | PASS |

验收口径补充：C55-5/G56-013 的 P0 仅以 PC `1440×900` 为阻断视口；
tablet `768×1024` 与 mobile `390×844` 降为 P2 非阻断项。Batch 57 已在
真实登录和真实后端下分批完成 11/11 个支持组合：Cyberpunk、Apple、Clay、
xLab、Liquid Glass 各 light/dark，Obsidian Flow dark。每组遍历全部静态和
有效动态路由，以公开 API 创建并清理临时计划/发布包实体，并检查键盘焦点、
Axe serious/critical、页面级溢出、console、失败请求和重复有效 GET。
因此 C55-5/J20/G56-013 已关闭；tablet/mobile 继续作为 C55-5-P2 跟踪。

Batch 57 后续修复补充：计划、执行、报告、调度、缺陷和通知配置的审计日志
现已显式提交；失败执行可在计划详情完成分诊并生成带 case/execution 关联的
缺陷；调度改为真实执行计划并拒绝已有 running run 的重复触发。以上缩小了
G56-012，但尚不能替代完整真实 UI/API/DB/报告/通知正负面旅程。

## 4. 外部真实环境验收

### 4.1 体育生产镜像（vpn07）

- 7 个文档登记端点的 HEAD/TLS 检查通过。
- 浏览器检查仍有一个节点超时；另一个网关节点仅返回极少有效内容。
- 因浏览器可用性未全通过，`B56-R0-PROD-SITES` 判定 `FAIL`。

### 4.2 体育测试节点与 API（OpenVPN）

- 测试节点 1–5 浏览器状态与控制台通过。
- 测试节点 6 浏览器返回 503，`B56-R0-TEST-SITES` 判定 `FAIL`。
- Knife4j v2 可访问；文档中的旧 v3 Swagger 地址为 404。
- 实际网关 `/v3/api-docs` 为 OpenAPI 3.0.3，但只有 15 paths /
  17 operations，不能证明六服务完整契约。
- 11 个安全无参 GET 返回 200；无效 Bearer 仍返回 200，与契约声明的
  security 语义不一致。
- `B56-R0-TEST-OPENAPI` 判定 `FAIL`。

### 4.3 运营后台测试登录（OpenVPN）

- 图形验证码和短信流程接口返回业务成功。
- 浏览器仍停留登录页，未形成 Cookie 或 storage 会话。
- `B56-R0-ADMIN-TEST` 判定 `FAIL`。

## 5. 质量门禁

| 门禁 | 命令/证据摘要 | 结果 |
| --- | --- | --- |
| F821 | `ruff check app/ --select F821` | PASS |
| 后端全量 | 860 collected；857 passed、3 skipped、0 failed | PASS |
| PostgreSQL 专项 | 显式 disposable PostgreSQL；3/3 passed | PASS |
| 前端单测 | 52 files、210 tests | PASS |
| TypeScript | `npm run typecheck` | PASS |
| 前端构建 | `npm run build` | PASS |
| Batch 56 E2E 路由可达性 | clean SHA；desktop/mobile 2/2 passed | PASS（desktop 为 PC 部分证据；mobile 为 P2） |
| 迁移 | current=head；单 head；`alembic check` 无操作 | PASS |
| Compose | production/Secure Cookie/no create_all；config 通过 | PASS |
| Backend 镜像 | hash lock、非 root、Playwright/Chromium/ffprobe/lanhu 探针 | PASS |
| Frontend 镜像 | `npm ci`、Nginx WebSocket 配置与 `nginx -t` | PASS |
| Volume 升级 | 限定命名 volume init；UID 10001 写入探针 | PASS |
| Python 供应链 | Linux `--require-hashes` lock；`pip check` | PASS |
| npm audit | high/critical 0；React Router 2 moderate | RISK |
| 凭据扫描 | staged diff、Playwright JSON/HTML、源码无真实凭据 | PASS |

3 个后端 skip 是显式 opt-in PostgreSQL 集成项；同一批次已在 disposable
PostgreSQL 上单独执行 3/3，通过后未从失败集合中排除任何测试。

## 6. 已修复缺陷

1. 启动器不再复用 5173/8000 未知进程；默认拒绝脏树，listener、绝对
   worktree 路径、提交 SHA 和 clean 状态互相校验。
2. Seed 分别幂等补齐 tester 的全局角色和默认项目成员关系。
3. SoloX 不可用时不再返回 Mock 设备或随机指标；start 保持 pending 并 503。
4. 性能 REST 全部绑定当前项目；WebSocket 在 accept 前完成认证、Origin、
   成员、权限和项目校验，JWT 不再出现在查询串。
5. Vite 与 Nginx 支持 WebSocket Upgrade；重复采集连接在单实例中拒绝。
6. 全指标为空、设备异常或 DB 保存失败时会话进入 failed，不生成假成功报告。
7. React StrictMode 请求使用 AbortSignal；取消异常被消费，真实异常保留。
8. Markmap 在卸载和零尺寸情况下不再执行非有限 fit。
9. Compose 固定 production、Secure Cookie、PostgreSQL 和 migration-only；
   旧 volume 在 backend 前执行限定目录权限初始化。
10. Python 使用 Linux 带哈希锁文件，Node 使用 lockfile，基础镜像使用 digest。

## 7. 未关闭阻断与解除条件

| ID | 优先级 | 阻断 | 解除条件 |
| --- | --- | --- | --- |
| B56-B01 | P0 | 测试节点 6 返回 503 | 服务恢复后按同一浏览器矩阵复测 |
| B56-B02 | P0 | 六服务实时 OpenAPI 不完整 | 提供六服务实时契约或六份可追溯 R1 快照 |
| B56-B03 | P0 | 测试 API 无效 Bearer 仍成功 | 明确公开/受保护边界并使实现与 OpenAPI 一致 |
| B56-B04 | P0 | 运营后台登录不形成浏览器会话 | 修复会话落地与重定向后真实登录复测 |
| B56-B05 | P0 | 真实 AI/OCR 未配置 | 提供授权服务、输出来源和无 fallback 证据 |
| B56-B06 | P1 | 无真机设备代理/SoloX | 部署认证设备代理，锁定运行时并完成真实采样 |
| B56-B07 | P1 | 缺 ELK 只读证据 | 提供索引权限并完成脱敏 trace 关联 |
| B56-B08 | P0 | 缺真实旧库快照 | 提供脱敏快照、基线、SHA 和隔离恢复副本 |
| B56-B09 | P0 | 设计源证据包不可复核 | 提供当前原始或脱敏导出及来源/时间/SHA |
| B56-B10 | P1 | 生产节点浏览器超时/内容不足 | 切回 vpn07 后在批准窗口复测，不扩大写权限 |

## 8. 风险说明

- React Router 仍有 2 个 moderate advisory；high/critical 为 0。自动修复会
  升级到破坏性大版本，未在本批次强制执行。建议单独版本完成兼容迁移。
- 生产性能采集需要宿主设备代理或受限 ADB-over-TCP。当前 Compose 不使用
  `--privileged`，也不宣称真机能力已交付。
- 进程内重复采集已阻断；若未来扩展为多 worker/多副本，应先引入数据库
  lease 或独立采集 worker，不能依赖进程内字典。
- 固定镜像 digest 和 Python lock 提升可复现性；后续安全更新需通过受控
  依赖升级 PR，而不是恢复浮动标签。

## 9. Agent Team 终审

- 前端异步取消修复复核：通过，无新增竞态、循环依赖、重复 GET 或异常吞噬。
- 启动器证据链复核：通过；clean SHA、PID、listener 命令和 PostgreSQL
  环境证据一致。
- 性能/部署终审发现的安全、真实性和部署问题均已转化为代码修复与测试；
  真实外部能力缺口保留为 `BLOCKED`，没有用绿色 E2E 隐藏。

## 10. 交付决定

本分支可以交付其**缺陷修复、生产安全加固和验收证据**，但不能宣称测试平台
全功能已达到生产 `READY`。外部阻断关闭并在正确 VPN 边界复测前，Leader
Verdict 必须保持 `NEEDS WORK`。
