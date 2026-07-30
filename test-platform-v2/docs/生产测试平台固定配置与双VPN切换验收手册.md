---
title: "生产测试平台固定配置与双 VPN 切换验收手册"
owner: "qa-team"
created: "2026-07-29"
last_reviewed: "2026-07-29"
status: "paused"
expires: "2027-01-29"
tags: ["production", "runtime-profile", "vpn07", "openvpn", "acceptance"]
related:
  - "../config/runtime/production.env.example"
  - "../scripts/start-platform-environment.ps1"
  - "../../docs/测试平台全功能验收文档-环境链接与账号汇总.md"
  - "../work-logs/batch-56-production-acceptance-issue-register.md"
---

# 生产测试平台固定配置与双 VPN 切换验收手册

> **暂停使用（2026-07-29）**：用户已暂停本手册。当前 production 服务器尚未
> 采购，且双 VPN 切换不作为 Batch 57 操作流程。除非用户后续明确重新启用，
> 不按本文初始化 production、不执行网络切换，也不运行 production 启动命令。

## 1. 结论

可以在一次验收中安全切换两套网络，但必须按**互斥阶段**执行：

```text
NEUTRAL
  → TEST_OPENVPN（vpn07 TUN/全局代理关闭）
  → NEUTRAL
  → PROD_VPN07（OpenVPN 断开）
  → NEUTRAL 或保持 PROD_VPN07
```

禁止状态：

```text
vpn07 TUN = ON  且  OpenVPN tunnel = ON
```

禁止在 API/UI 任务、后台执行、文件下载或浏览器导航进行中切换网络。每次切换
先让当前阶段的任务结束并保存证据，再进入 `NEUTRAL`。

本地测试平台 `http://localhost:5173` 通过 loopback 访问，可以在两个阶段
保持运行；但它发往被测系统的出站请求必须等新网络状态校验通过后才能继续。

## 2. 两类“环境”不要混淆

| 类型 | 本手册中的实例 | 作用 |
| --- | --- | --- |
| 测试平台自身运行实例 | local、production | 决定测试平台自己的 URL 和数据库 |
| 被测系统目标环境 | 体育测试、体育生产、运营后台测试、ELK 等 | 决定一次验收请求应走 OpenVPN 还是 vpn07 |

删除测试平台自身的 `test` profile，不会删除 `/environment` 页面中被测系统的
test/staging/prod 配置。

## 3. 生产测试平台固定配置填写单

### 3.1 非敏感信息

以下信息可以在聊天中逐项确认：

| 序号 | 字段 | 示例格式 | 你的值 | 状态 |
| ---: | --- | --- | --- | --- |
| P01 | 最终 HTTPS URL | `https://<正式域名>` | 服务器采购后提供 | DEFERRED |
| P02 | 部署宿主机/集群逻辑名称 | 主机别名或集群名，不写密码 | 服务器采购后提供 | DEFERRED |
| P03 | TLS 终止位置 | Nginx / LB / Ingress | 基础设施设计后提供 | DEFERRED |
| P04 | 对外前端端口 | 通常 `443` | 基础设施设计后提供 | DEFERRED |
| P05 | PostgreSQL 主机逻辑名称 | 主机名或服务名 | 数据库采购后提供 | DEFERRED |
| P06 | PostgreSQL 端口 | 通常 `5432` | 数据库采购后提供 | DEFERRED |
| P07 | PostgreSQL 数据库名 | 建议 `cameltv_production` | 数据库采购后提供 | DEFERRED |
| P08 | PostgreSQL 用户名 | 最小权限应用用户 | 数据库采购后提供 | DEFERRED |
| P09 | 备份保存位置/保留期 | 逻辑位置 + 天数 | 基础设施设计后提供 | DEFERRED |
| P10 | 发布与回滚窗口 | 日期、时区、时长 | 首次部署前提供 | DEFERRED |

### 3.2 敏感信息

以下值不要发到聊天、截图、工单正文或 Git：

- PostgreSQL 密码；
- `DATABASE_URL` 完整连接串；
- `SECRET_KEY`；
- 初始管理员/测试员密码；
- AI、ELK、设计源等 Token、Cookie 或账号密码。

只写入受 Git 忽略的：

```text
test-platform-v2/config/runtime/production.env
```

### 3.3 首次初始化

在 Batch 57 worktree 根目录执行：

```powershell
Set-Location F:\CamelTv-worktrees\codex-batch-57-environment-targets-and-acceptance

$profile = "test-platform-v2/config/runtime/production.env"
$example = "test-platform-v2/config/runtime/production.env.example"

if (-not (Test-Path -LiteralPath $profile)) {
    Copy-Item -LiteralPath $example -Destination $profile
}

git check-ignore --quiet $profile
if ($LASTEXITCODE -ne 0) {
    throw "production.env 未被 Git 忽略，停止填写。"
}
```

然后只在本机编辑 `production.env`。必须满足：

```dotenv
PLATFORM_TARGET=production
PLATFORM_FRONTEND_URL=https://最终生产域名
COMPOSE_PROJECT_NAME=cameltv-tp-production
FRONTEND_PORT=对外映射端口
BACKEND_PORT=8000

ENVIRONMENT=production
DATABASE_URL=postgresql://应用用户:URL编码后的密码@数据库主机:5432/cameltv_production
AUTO_CREATE_TABLES=false
POSTGRES_USER=应用用户
POSTGRES_PASSWORD=真实密码
POSTGRES_DB=cameltv_production
ALLOWED_ORIGINS=https://最终生产域名
CSRF_ALLOWED_ORIGINS=https://最终生产域名
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
COOKIE_PATH=/api

SECRET_KEY=独立强随机值
ADMIN_USERNAME=admin
ADMIN_PASSWORD=独立强随机值
TESTER_USERNAME=tester
TESTER_PASSWORD=独立强随机值
```

约束：

- `PLATFORM_FRONTEND_URL`、`ALLOWED_ORIGINS`、`CSRF_ALLOWED_ORIGINS` 必须完全一致；
- `DATABASE_URL` 中的数据库名必须等于 `POSTGRES_DB`；
- 使用本仓库 Compose 自带 PostgreSQL 时，数据库主机写 `postgres`；使用外部
  PostgreSQL 时，写 P05 确认的生产数据库主机；
- 生产库不得指向 local SQLite 或任何测试数据库；
- 密码中存在 `@`、`:`、`/`、`#`、`%` 时，`DATABASE_URL` 中必须 URL 编码；
- `AUTO_CREATE_TABLES` 必须为 `false`，表结构只由 Alembic 管理；
- `COOKIE_SECURE` 必须为 `true`，入口必须真实使用 HTTPS。

### 3.4 不泄密的静态检查

```powershell
$profile = "test-platform-v2/config/runtime/production.env"

if (Select-String -LiteralPath $profile -Quiet -Pattern "change-me|example\.com") {
    throw "production.env 仍含示例值。"
}

docker compose `
  --env-file $profile `
  -f test-platform-v2/deploy/docker-compose.yml `
  config --quiet

pwsh test-platform-v2/scripts/start-platform-environment.ps1 `
  -Target production -Action status
```

这些命令不得改为输出完整 Compose config，因为展开后的结果可能含敏感值。

只有数据库备份、迁移窗口、TLS 和回滚负责人都确认后才允许启动：

```powershell
pwsh test-platform-v2/scripts/start-platform-environment.ps1 `
  -Target production -Action start -ConfirmProduction
```

## 4. 网络状态定义

| 状态 | vpn07 TUN/全局代理 | OpenVPN | 允许的验收 |
| --- | --- | --- | --- |
| `NEUTRAL` | OFF | Disconnected | 不访问体育测试/生产，只做切换和本地整理 |
| `TEST_OPENVPN` | OFF | Connected | 体育测试节点、测试 OpenAPI、测试 API、运营后台测试 |
| `PROD_VPN07` | ON | Disconnected | 体育生产只读 GET/HEAD、生产页面浏览 |
| `CONFLICT` | ON | Connected | 禁止执行；立即回到 `NEUTRAL` |

当前 Windows 主机已确认能同时出现以下两个适配器，因此不能只看客户端窗口：

- vpn07：名称 `vpn07`，描述 `Meta Tunnel`；
- OpenVPN：描述匹配 `OpenVPN|TAP-Windows Adapter|ovpn-dco`。

## 5. 通用互斥检查

在每个阶段开始前运行：

```powershell
$vpn07Up = @(
    Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq "vpn07" -and $_.Status -eq "Up" }
).Count -gt 0

$openVpnUp = @(
    Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Status -eq "Up" -and
            $_.InterfaceDescription -match "OpenVPN|TAP-Windows Adapter|ovpn-dco"
        }
).Count -gt 0

if ($vpn07Up -and $openVpnUp) {
    throw "CONFLICT：vpn07 与 OpenVPN 同时处于 Up，禁止发起验收请求。"
}

[pscustomobject]@{
    vpn07_tun_up = $vpn07Up
    openvpn_tunnel_up = $openVpnUp
}
```

此检查只输出布尔状态，不输出 IP、路由、账号或内部域名。

## 6. 切换到体育测试环境：`TEST_OPENVPN`

### 6.1 停止当前生产阶段

1. 等待所有生产页面导航、GET/HEAD、下载和截图结束。
2. 在测试平台确认没有运行中的 API/UI/性能任务。
3. 保存本阶段证据索引；关闭生产验收浏览器上下文。

### 6.2 关闭 vpn07

在 vpn07 客户端中依次：

1. 关闭 TUN 模式；
2. 关闭全局/系统代理；
3. 等待 `vpn07` Meta Tunnel 不再为 `Up`。

不使用任务管理器强杀 vpn07，也不修改 Windows 路由表。客户端进程可以保留，
但 TUN 和系统代理必须关闭。

检查 Windows 系统代理：

```powershell
$internet = Get-ItemProperty `
  "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"

if ($internet.ProxyEnable -eq 1 -or $internet.AutoConfigURL) {
    throw "vpn07 的系统代理/PAC 仍启用，不能进入 OpenVPN 测试阶段。"
}
```

### 6.3 进入 `NEUTRAL`

1. OpenVPN 此时也应为 Disconnected。
2. 执行通用互斥检查，预期两个布尔值均为 `False`。
3. 清理 DNS：

```powershell
Clear-DnsClientCache
```

4. 完全关闭上一阶段浏览器，后续使用新的浏览器上下文，避免复用旧 DNS、
   HTTP/2、Cookie 和连接池。

### 6.4 启动 OpenVPN

1. 打开 OpenVPN Connect；
2. 连接唯一的项目 VPN profile；
3. 等待 OpenVPN 适配器处于 `Up`；
4. 再次执行通用互斥检查，预期：

```text
vpn07_tun_up       = False
openvpn_tunnel_up  = True
```

### 6.5 目标连通性检查

把主机名只赋给当前 PowerShell 会话，不提交到 Git：

```powershell
$testHost = Read-Host "输入本次测试环境主机名（不要带协议和路径）"
$testPort = 443

$probe = Test-NetConnection -ComputerName $testHost -Port $testPort
if (-not $probe.TcpTestSucceeded) {
    throw "OpenVPN 已连接，但测试目标端口不可达。"
}
```

如果系统 DNS 返回 `198.18.0.0/15`，说明 vpn07 Fake-IP 仍在参与解析，必须
回到 `NEUTRAL`，不能继续。

### 6.6 连续完成测试环境验收

在同一个 `TEST_OPENVPN` 阶段集中执行：

1. `B56-B01`：体育测试节点浏览器矩阵；
2. `B56-B02`：六服务 OpenAPI；
3. `B56-B03`：公开/受保护接口鉴权边界；
4. `B56-B04`：运营后台真实登录和会话；
5. 需要测试 ELK 时，按 ELK 所属网络边界在本阶段执行。

不要在这些步骤之间恢复 vpn07。

## 7. 从测试环境切回生产：`PROD_VPN07`

### 7.1 结束 OpenVPN 阶段

1. 等待测试 API、登录、导入和浏览器请求全部完成；
2. 保存脱敏证据；
3. 注销运营后台测试会话；
4. 在 OpenVPN Connect 中 Disconnect；
5. 等待 OpenVPN 适配器不再为 `Up`。

### 7.2 再次进入 `NEUTRAL`

```powershell
Clear-DnsClientCache
```

执行通用互斥检查，必须两个布尔值均为 `False`。关闭测试阶段浏览器上下文。

### 7.3 恢复 vpn07

在 vpn07 客户端中：

1. 开启 TUN 模式；
2. 开启验收要求的全局流量模式；
3. 等待 `vpn07` Meta Tunnel 处于 `Up`；
4. 执行通用互斥检查，预期：

```text
vpn07_tun_up       = True
openvpn_tunnel_up  = False
```

### 7.4 生产目标连通性检查

```powershell
$prodHost = Read-Host "输入本次生产只读目标主机名（不要带协议和路径）"
$prodPort = 443

$probe = Test-NetConnection -ComputerName $prodHost -Port $prodPort
if (-not $probe.TcpTestSucceeded) {
    throw "vpn07 已开启，但生产目标端口不可达。"
}
```

只有检查通过后，才创建新的生产验收浏览器上下文并执行 `B56-B10`。
生产阶段只允许批准范围内的 GET/HEAD 和公开页面浏览，不登录、不写入、
不发布、不支付、不压测。

## 8. 失败与回滚

### 8.1 切换到 OpenVPN 失败

1. Disconnect OpenVPN；
2. 保持 vpn07 TUN/系统代理关闭；
3. 清理 DNS；
4. 执行通用互斥检查；
5. 保持 `NEUTRAL` 并记录 `BLOCKED`，不得尝试双开；
6. 如需继续生产验收，重新按第 7 节完整恢复 vpn07。

### 8.2 切换到 vpn07 失败

1. 关闭 vpn07 TUN/系统代理；
2. 确认 OpenVPN 仍为 Disconnected；
3. 清理 DNS；
4. 保持 `NEUTRAL` 并记录 `BLOCKED`；
5. 不得为了“临时能访问”同时开启 OpenVPN。

### 8.3 发现冲突态

如果通用检查抛出 `CONFLICT`：

1. 停止所有新请求；
2. 先在两个客户端中都 Disconnect/OFF；
3. 清理 DNS；
4. 关闭浏览器上下文；
5. 两个适配器均非 Up 后，重新进入目标阶段。

## 9. 证据记录

每个阶段记录：

| 字段 | 要求 |
| --- | --- |
| Session ID | 如 `B57-NET-TEST-001` / `B57-NET-PROD-001` |
| 开始/结束时间 | 使用 Asia/Shanghai |
| 网络状态 | 只记录 `TEST_OPENVPN` / `PROD_VPN07`，不记录隧道 IP |
| 代码 SHA | 当前测试平台 Git SHA |
| 用例/缺陷 ID | B56-B01～B10 |
| 预期/实际 | 脱敏描述 |
| 清理结果 | 会话、测试数据、浏览器上下文是否清理 |
| 证据引用 | 受控存储逻辑路径，不写 Cookie、Token、Authorization |

截图中不得出现 vpn07/OpenVPN 配置、账号、内部 IP、Token、Cookie 或生产数据。

## 10. 现有 OpenVPN 自动连接能力的边界

平台的 `openvpn_service.py` 可以在被测环境类型为 `test` 时启动 OpenVPN，
但它目前：

- 不知道 vpn07 是否启用；
- 不会关闭 vpn07 TUN/系统代理；
- 不会在测试结束后 Disconnect OpenVPN；
- 不会恢复 vpn07；
- 不能判断是否仍有运行中的验收任务。

因此在完成网络状态机前：

```dotenv
OPENVPN_AUTO_CONNECT_ENABLED=false
```

保持默认关闭。由操作者按本手册切换并验证网络后，再从测试平台发起任务。

## 11. 后续一键切换方案

可以增加一个 `Test|Production|Neutral` 网络切换器，但必须满足：

1. 先停止新任务并等待当前请求结束；
2. 先进入 `Neutral`，绝不从一个隧道直接叠加另一个；
3. 使用 vpn07 官方支持的 CLI/API 控制 TUN；没有官方接口时保留人工确认，
   不使用坐标点击或强杀进程；
4. OpenVPN 通过稳定的 Connect/Disconnect 接口控制；
5. 检查适配器、系统代理、DNS 和目标 TCP；
6. 任一步失败自动回到 `Neutral`；
7. 只写无秘密的状态清单；
8. 恢复阶段必须知道切换前状态，避免误开 vpn07。

目前尚未确认 vpn07 的受支持 CLI/API，所以本手册采用“人工开关 + 自动校验”
模式。取得 vpn07 控制接口文档后，才能安全实现真正的一键自动切换。

## 12. 建议的输入顺序

1. 先补 P01～P10 的生产测试平台非敏感信息；
2. 在本机填写 ignored `production.env` 的秘密；
3. 提供 vpn07 官方 CLI/API 文档，或确认只能人工开关；
4. 提供 OpenVPN profile 的逻辑名称和是否需要交互认证；
5. 提供测试节点、生产节点的逻辑清单和批准窗口；
6. 先进行一次不访问业务系统的网络切换演练；
7. 再执行 OpenVPN 测试阶段；
8. 最后恢复 vpn07 并执行生产只读阶段。
