#!/usr/bin/env bash
# AITDE V3.4 — Worker 主机启动模板（持续心跳 + 加入队列）
#
# 真实 Worker 主机（测试网/办公网）在启动时：
#   1. 读取机器身份（hostname + zone + capabilities）
#   2. 持续注册/心跳到 Control Plane（POST /api/v2/workers/heartbeat）
#   3. 加入 Temporal TaskQueue 拉取任务（backend 的 run_worker）
#   4. 撤离/禁用：Temporal 端 drain（worker 不再接新任务）；自身异常不动
#      （离线由 Control Plane 的 last_heartbeat 阈值判定，无需 worker 主动下线）
#
# 依赖: python3 + 仓库后端（含 app/temporal 的 worker 入口）。可从本仓库启动：
#   python -m app.modules.aitde.workflow.gateway --task-queue <Q>
#
# 用法: bash scripts/start-worker.sh [zone] [capabilities...]
#    例: bash scripts/start-worker.sh TEST HTTP,BROWSER
set -euo pipefail
cd "$(dirname "$0")/../../../backend"

ZONE=${1:-TEST}
CAPS=${2:-HTTP,BROWSER}
BACKEND_URL=${BACKEND_URL:-http://localhost:8000/api/v2}
TEMPORAL_TASK_QUEUE=${TEMPORAL_TASK_QUEUE:-worker-test}
WORKER_KEY=${WORKER_KEY:-"worker-$(hostname)"}
API_TOKEN=${API_TOKEN:-}
WORKER_HEARTBEAT_SECONDS=${WORKER_HEARTBEAT_SECONDS:-60}

export ZONE CAPS BACKEND_URL WORKER_KEY API_TOKEN WORKER_HEARTBEAT_SECONDS

echo "[worker] key=$WORKER_KEY zone=$ZONE caps=$CAPS queue=$TEMPORAL_TASK_QUEUE heartbeat=${WORKER_HEARTBEAT_SECONDS}s"

heartbeat_pid=""
worker_pid=""

cleanup() {
  trap - EXIT INT TERM
  for pid in "$heartbeat_pid" "$worker_pid"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done
  for pid in "$heartbeat_pid" "$worker_pid"; do
    if [ -n "$pid" ]; then
      wait "$pid" 2>/dev/null || true
    fi
  done
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# ── 1) 持续心跳（立即发送；瞬时失败按间隔重试）──
python -m app.modules.aitde.workflow.worker_heartbeat &
heartbeat_pid=$!

# ── 2) 加入 Temporal TaskQueue 拉取任务（长驻；Temporal 负责重试/恢复）──
echo "[worker] joining Temporal queue=$TEMPORAL_TASK_QUEUE (Ctrl-C to stop)"
# 需 backend 环境：settings.temporal_enabled=true + TEMPORAL_GRPC_ENDPOINT 可达。
python -m app.modules.aitde.workflow.gateway --task-queue "$TEMPORAL_TASK_QUEUE" &
worker_pid=$!

# 任一受管进程退出都终止整个 Worker 单元，交给 systemd/Compose 重启。
set +e
wait -n "$heartbeat_pid" "$worker_pid"
status=$?
set -e
exit "$status"
