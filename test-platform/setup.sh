#!/usr/bin/env bash
# ============================================================
# 体育平台测试平台 — 一键搭建（macOS / Linux）
# 用法:  在 test-platform/ 目录下执行  bash setup.sh
# ============================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "==> 1/5 创建独立 venv (test-platform/.venv)"
PY="$(command -v python3.12 || command -v python3 || command -v python)"
"$PY" -m venv .venv
VENVPY="$ROOT/.venv/bin/python"

echo "==> 2/5 升级 pip 并安装依赖"
"$VENVPY" -m pip install --upgrade pip
"$VENVPY" -m pip install -r requirements.txt

echo "==> 3/5 以可编辑方式安装本平台 (提供 tp 命令)"
"$VENVPY" -m pip install -e .

echo "==> 4/5 安装 Playwright Chromium"
"$VENVPY" -m playwright install chromium

echo "==> 5/5 准备 .env"
[ -f .env ] || { cp .env.example .env; echo "    已生成 .env，请填写凭据"; }

cat <<'EOF'

============== 安装完成 ==============
激活 venv:  source .venv/bin/activate
自检:       tp config show --site camel1 --env prod

仍需手动完成的外部依赖:
  1) Docker Desktop —— Mock Server(WireMock) 需要:  docker pull wiremock/wiremock
  2) mitmproxy CA 证书 —— 抓 camel1.to 的 HTTPS 必需:
       先跑  tp capture --site camel1 --env prod  启动 mitmproxy,
       浏览器访问 http://mitm.it 下载安装证书到系统信任区。
  3) 填写 .env 中各站点/环境凭据与 UPSTREAM_PROXY。
EOF
