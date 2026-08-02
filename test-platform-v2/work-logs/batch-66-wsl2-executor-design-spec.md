# Batch 66 — Design Spec（WSL2 执行器安装脚本）

> **Design (🎨)** | Date: 2026-08-02 | Status: 已验收（无 UI）

## 0. 技术体系确认

- 无前端/后端业务代码变更；交付物为 bash 脚本 + 文档。
- 目标环境：Ubuntu WSL2（tun 设备、openvpn、curl、iproute2）。

## 1. 脚本行为设计（wsl2-executor-setup.sh）

| 步骤 | 行为 | 失败处理 |
|------|------|---------|
| 参数校验 | `--ovpn` 文件存在、`--auth-user` 非空 | 打印 usage，exit 1 |
| tun 检查 | `/dev/net/tun` 缺失则 mkdir + mknod + chmod 600 | 创建失败报错退出 |
| 安装 | `apt-get update && install openvpn ca-certificates curl iproute2` | set -e 退出 |
| 配置部署 | 复制 .ovpn → `/etc/openvpn/client/test5.conf`（chmod 600） | 退出 |
| 凭据 | 交互读取密码，写入 `/opt/test5-runner/test5.auth`（chmod 600），修正 `auth-user-pass` 指向 | 退出 |
| 启动 | `openvpn --config ... --daemon`（不依赖 systemd） | 提示查日志 |
| 验证提示 | 输出 ip route / ping / curl 命令 | — |

## 2. 安全设计

- 真实 CA/凭据只存在于用户本机与 WSL 本地文件；脚本与 README 零 Secret；
- `unset VPN_PASS` 避免变量残留；
- 凭据文件 600 权限。

## 3. 验证矩阵（窗口内登记）

V1 主机 AI / V2 执行器内网 ping / V3 执行器域名 curl / V4 并行 / V5 反向，
登记表在 `scripts/executor/README.md` §2，结果回填 QA 报告（窗口后补）。

## 4. 设计 QA 走查

- ⚪ P3-01：脚本非完全幂等（重复运行会重启 OpenVPN）→ README 注明重连命令，可接受。
- ⚪ P3-02：Ubuntu 发行版未装 → README 第 0 步 + Docker 回退（C66-3）。

## 5. 签核

**通过**（无 P0/P1）。
