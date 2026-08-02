# Batch 66 — 执行器 V1–V5 验证记录（收尾）

> **QA (🔍)** | Date: 2026-08-02 | Verdict: PASS

## 结论

WSL2 Test5 验收执行器 V1–V5 验证矩阵**全部通过**，执行器隔离方案（ADR-0017）正式成立。
主机 vpn07 管 AI、执行器 OpenVPN 管 Test5，互不干扰。

## 环境事实

| 项 | 值 |
|---|-----|
| 执行器 | Ubuntu WSL2（用户 mjr），OpenVPN 2.7.0 |
| VPN 账号 | mojinru（凭据仅存 WSL `/opt/test5-runner/test5.auth`，chmod 600） |
| VPN 服务器 | router-2f.elelive.cn = 183.6.11.153（已写入 WSL hosts 直连，绕过 Clash fake-ip） |
| 隧道 | tunx / 10.7.7.5，网关 10.7.7.1，内网路由齐备 |
| Test5 g3 | camelive-g3-test5.elelive.cn = 192.168.50.170（写入 WSL hosts） |

## V1–V5 证据

| # | 场景 | 命令/动作 | 结果 |
|---|------|-----------|------|
| V1 | 主机 AI（vpn07 开） | `curl -I https://api.deepseek.com` | HTTP 401（链路通，正常鉴权） |
| V2 | 执行器 Test5 内网 | `ping -c 2 192.168.50.170` | 0% 丢包（228ms，隧道转发延迟） |
| V3 | 执行器 Test5 域名 | `curl -I https://camelive-g3-test5.elelive.cn` | HTTP 200 OK（openresty 真实响应） |
| V4 | 并行 | 主机 AI 5 次 + 执行器 Test5 5 次（双 Job 并发） | 401×5 + 200×5，双方正常 |
| V5 | 反向 | 关闭 vpn07，执行器单独跑 Test5 | 用户手动：200 + 0% 丢包；Agent 复核：OpenVPN UP + 200 + 0% |

## 门禁

| 检查 | 结果 |
|------|:----:|
| 脚本语法 | ✅ `sh -n` 通过 |
| 密钥/CA 入库 | ✅ 0 命中（凭据仅本地） |
| git diff --check | ✅ |
| 零业务代码 | ✅（仅 scripts/docs/work-logs） |

## 遗留与待办

- 其余 5 个 Test5 节点 IP：网关 DNS REFUSED，待 Test5 owner 提供后补 WSL hosts（C66-4）。
- 隧道延迟 ~228ms：VPN 服务器侧转发路径所致（直连 183.6.11.153 仅 33ms），功能正常，性能优化留后续。
- 旧《双 VPN 切换手册》删除：C65-2 继续跟踪。
- 本批修复：安装脚本 `grep` 增加 sudo（root 600 配置文件读取权限）、隧道地址检查改为精确匹配 `inet 10.7.`。
