# Runner 出口防火墙 / 网络实验室证据 — 提供方式

## 1. 当前主机基线（2026-11-19）

| 项 | 值 |
|---|---|
| Host | `MJR`（Windows 11 家庭版） |
| 当前用户 | 非管理员 |
| 默认路由 | 以太网 192.168.1.2 → 192.168.1.1；WLAN 192.168.3.70 → 192.168.3.1 |
| Windows Firewall | Domain 关闭、**Private 开启**、Public 关闭；`DefaultOutboundAction = NotConfigured`（即默认放行） |
| 出站 Block 规则 | 仅 3 条 codex sandbox 规则（loopback udp/tcp、outbound） |

**结论**：当前 Runner 主机没有“出站 allowlist”，因此不能声称已限制外联；需要先定义并落地策略，
再采集 allowed/denied 两组实测证据。

## 2. 需要提供的三样东西

1. **策略定义**：允许访问的目标清单（域名/IP + 端口 + 协议）、是否默认拒绝、DNS 解析方式、
   是否允许重定向/直连 IP。
2. **策略落地配置导出**：
   - Windows：`netsh advfirewall export "C:\evidence\fw.wfw"` + `Get-NetFirewallRule | Export-Csv`
   - Linux：`iptables-save` / `nft list ruleset` / `ufw status verbose`
   - 云：安全组 + NACL 的 JSON/截图（含出站规则）
3. **从 Runner 主机实测**（同一时刻、同一条命令）：
   - 允许目标：`Invoke-WebRequest https://<allowed>` → 200
   - 非允许目标：`Test-NetConnection example.com -Port 443` / `curl --max-time 5 https://example.com`
     → 超时/拒绝
   - 记录：时间、Runner 标识、源 IP、目标、结果、防火墙策略版本。

## 3. 三种落地方式（任选其一）

### A. 就在本机（Windows Firewall，需要管理员 + 维护窗口）

```powershell
# 基线
netsh advfirewall export "C:\evidence\fw-before.wfw"

# 允许 Runner 只访问 Camel Test5（示例：python.exe + 目标 IP/端口）
New-NetFirewallRule -DisplayName "AIQE Runner allow camel-test5" -Direction Outbound `
  -Program "C:\...\python.exe" -RemoteAddress 192.168.50.170 -RemotePort 443 -Action Allow

# 默认拒绝该 Runner 的其余出站（Block 优先于 Allow，需按进程/端口精确设计）
New-NetFirewallRule -DisplayName "AIQE Runner deny other" -Direction Outbound `
  -Program "C:\...\python.exe" -Action Block

# 实测 allowed / denied，再导出
netsh advfirewall export "C:\evidence\fw-after.wfw"
```

风险：`-Action Block` 会影响该进程全部出站；建议在维护窗口、仅对专用 Runner 进程执行，
并保留 `fw-before.wfw` 一键回滚（`netsh advfirewall import`）。当前会话不是管理员，需你授权/执行。

### B. 网络实验室 / 云安全组（推荐生产）

提供安全组/NACL 的出站规则导出 + 从 Runner 到 allowed/denied 目标的实测截图/日志；
Runner 身份（hostname、内网 IP、所属节点）一并记录。

### C. 补偿控制（无网络防火墙时）

在 Runner 上起一个**本地 egress 代理**，代理只放行 allowlist，AIQE HTTP 节点统一走代理；
提供代理配置、deny 日志、allowed/denied 实测。可在本机完成，但不是网络层强制，需注明残余风险。

## 4. 交付物模板

- Runner 标识：hostname / IP / node_id / OS
- 策略版本与 allowlist（含审批人）
- 配置导出文件（hash）
- 实测日志：allowed 成功 + denied 失败，时间与源 IP
- 对应 AIQE Run/Artifact（或独立证据包路径）
