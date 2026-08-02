#!/usr/bin/env bash
# ============================================================
# Test5 验收执行器（Ubuntu WSL2）安装脚本
# Batch 66 / ADR-0017 / test-platform-v2/docs/operations/test5-runner-isolation.md
#
# 职责：在 Ubuntu WSL2 内安装 OpenVPN 并准备 Test5 验收执行环境。
# 原则：真实 CA / 凭据不入库；本脚本只接受本地文件与环境变量。
#
# 用法（在 WSL2 Ubuntu 内执行）:
#   bash scripts/executor/wsl2-executor-setup.sh \
#       --ovpn /mnt/c/Users/26029/Desktop/test5.ovpn \
#       --auth-user <VPN用户名>
# 凭据: 脚本会交互式读取 VPN 密码并写入 /opt/test5-runner/test5.auth (chmod 600)
# ============================================================
set -euo pipefail

OVPN_SRC=""
AUTH_USER=""
OVPN_DEST="/etc/openvpn/client/test5.conf"
AUTH_FILE="/opt/test5-runner/test5.auth"

usage() {
    echo "Usage: $0 --ovpn <path-to-test5.ovpn> --auth-user <vpn-username>"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ovpn) OVPN_SRC="$2"; shift 2 ;;
        --auth-user) AUTH_USER="$2"; shift 2 ;;
        *) usage ;;
    esac
done

[[ -n "$OVPN_SRC" && -n "$AUTH_USER" ]] || usage
[[ -f "$OVPN_SRC" ]] || { echo "ERROR: .ovpn not found: $OVPN_SRC"; exit 1; }

echo "==> [1/5] 检查 tun 设备"
if [[ ! -e /dev/net/tun ]]; then
    echo "tun 缺失，尝试创建 /dev/net/tun"
    sudo mkdir -p /dev/net
    sudo mknod /dev/net/tun c 10 200
    sudo chmod 600 /dev/net/tun
fi
ls -l /dev/net/tun

echo "==> [2/5] 安装 openvpn 与工具"
sudo apt-get update -qq
sudo apt-get install -y -qq openvpn ca-certificates curl iproute2

echo "==> [3/5] 准备运行目录与 OpenVPN 配置"
sudo mkdir -p /opt/test5-runner
sudo cp "$OVPN_SRC" "$OVPN_DEST"
sudo chmod 600 "$OVPN_DEST"

echo "==> [4/5] 写入凭据文件（不入库）"
read -r -s -p "VPN 密码: " VPN_PASS
echo
echo "$AUTH_USER" | sudo tee "$AUTH_FILE" >/dev/null
echo "$VPN_PASS" | sudo tee -a "$AUTH_FILE" >/dev/null
sudo chmod 600 "$AUTH_FILE"
unset VPN_PASS

# 让 auth-user-pass 指向本地凭据文件（若 .ovpn 未指定）
if ! grep -q "auth-user-pass" "$OVPN_DEST"; then
    echo "auth-user-pass $AUTH_FILE" | sudo tee -a "$OVPN_DEST" >/dev/null
else
    sudo sed -i "s|^auth-user-pass.*|auth-user-pass $AUTH_FILE|" "$OVPN_DEST"
fi

echo "==> [5/5] 启动 OpenVPN（后台守护）"
sudo openvpn --config "$OVPN_DEST" --daemon
sleep 3
ip -4 addr show | grep -E "10\." || echo "WARN: 尚未看到 10.x 地址，请检查连接日志"

cat <<'EOF'

===== 安装完成 =====
验证命令:
  ip route                    # 应看到 10.0.0.0/8 经 tun 的路由
  ping -c 2 <Test5内网IP>     # V2: Test5 内网连通
  curl -I https://camelive-g3-test5.elelive.cn  # V3: Test5 域名连通

连接日志: sudo tail -f /var/log/openvpn/*.log  （或 journalctl -u openvpn）
重连:     sudo pkill -f "openvpn --config $OVPN_DEST"; sudo openvpn --config "$OVPN_DEST" --daemon
===== V1–V5 完整验证见 scripts/executor/README.md =====
EOF
