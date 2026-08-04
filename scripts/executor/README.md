# Test5 验收执行器（WSL2）— 使用说明

> 关联：ADR-0017、`test-platform-v2/docs/operations/test5-runner-isolation.md`
> 状态：batch-66 搭建中；**实测窗口 2026-08-03 11:00–18:00**（已登记）

## 0. 前置（Windows PowerShell，一次性）

```powershell
# 确认 WSL2 与发行版
wsl -l -v

# 若没有 Ubuntu 发行版（当前机器已有 docker-desktop）：
wsl --install -d Ubuntu
```

> 备选：若 Ubuntu 安装受阻，可用已运行的 Docker Desktop 走容器执行器（同属 WSL2 后端），
> 回退记录写入 batch-66 QA/Leader（C66-3）。

## 1. 安装执行器（WSL2 Ubuntu 内）

```bash
# 仓库路径在 WSL 内通常挂载于 /mnt/f/CamelTv-worktrees/codex-batch-66-wsl2-executor
cd /mnt/f/CamelTv-worktrees/codex-batch-66-wsl2-executor
bash scripts/executor/wsl2-executor-setup.sh \
    --ovpn /mnt/c/Users/26029/Desktop/test5.ovpn \
    --auth-user <VPN用户名>
```

- 脚本自动：检查/创建 tun、安装 openvpn、部署配置、写入凭据文件（`/opt/test5-runner/test5.auth`，
  chmod 600，不入库）、后台启动。
- 您的 `test5.ovpn` 放在本机任意位置（如桌面），**不要提交进仓库**。

## 2. 验证矩阵 V1–V5（2026-08-02 全部通过并登记）

| # | 场景 | 命令/动作 | 预期 | 登记 |
|---|------|-----------|------|:----:|
| V1 | 主机 AI（vpn07 开） | `curl -I https://api.deepseek.com` | 401（链路通） | ✅ 2026-08-02（401） |
| V2 | 执行器内 Test5 内网 | `ping -c 2 192.168.50.170` | 通 | ✅ 2026-08-02（0% 丢包） |
| V3 | 执行器内 Test5 域名 | `curl -I https://camelive-g3-test5.elelive.cn` | 200 | ✅ 2026-08-02（HTTP 200） |
| V4 | 两者同时运行 | 主机 AI 5 次 + 执行器 Test5 5 次并行 | 双方正常 | ✅ 2026-08-02（401×5 + 200×5） |
| V5 | 反向验证 | 关 vpn07，仅执行器跑 Test5 验收 | Test5 正常 | ✅ 2026-08-02（用户手动 + Agent 复核：200 + 0%） |

> g3 节点内网 IP = `192.168.50.170`（经 VPN 网关 10.7.7.1 DNS 解析）；其余 5 个节点
> （camel-to-test5 等）网关 DNS 返回 REFUSED，待 Test5 owner 提供后补 hosts。

## 3. 执行器日常使用

```bash
# 启动
sudo openvpn --config /etc/openvpn/client/test5.conf --daemon
# 停止
sudo pkill -f "openvpn --config /etc/openvpn/client/test5.conf"
# 日志
sudo tail -f /var/log/openvpn/*.log
```

## 4. 安全约束

- OpenVPN 真实 CA、账号密码**不入库**；凭据只存在于 WSL 本地 `/opt/test5-runner/test5.auth`。
- 执行器产物（报告/日志）回传共享目录，验收结果按 C63-2 登记，不伪造证据。

## 5. Test5 契约拉取（batch-74 新增）

网关：`camel-api-gateway05.svc.elelive.cn`（内网，OpenVPN 下经 VPN DNS 10.7.7.1 解析）。
2026-08-04 实测：六节点 + 网关均解析到 `192.168.50.170`（VPN DNS 重试可稳定；hosts 补录可选）。
网关暴露 10 个路由服务（`GET /actuator/gateway/routes`）。

```bash
bash scripts/executor/fetch-test5-contracts.sh
```

产物：`test-platform-v2/tests/api-testing/specs/test5-contracts/{service}.openapi.json` + `manifest.json`
（服务/URL/spec/版本/路径数/SHA-256/拉取时间）。契约只读拉取，不含凭据；
`admin-service`（302 需登录）、`konfi-service`（需 token）、`gateway-service`（无文档）
在 manifest 中如实登记，不伪造。
