#!/usr/bin/env bash
# migrate-tencent-production.sh — 腾讯云生产迁移：Supabase → 本地 PostgreSQL + Alembic 校验
#
# 用法:
#   SUPABASE_DATABASE_URL="postgresql://postgres.<ref>:<pwd>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres" \
#     ./migrate-tencent-production.sh --env-file ../config/runtime/production.env
#
# 步骤: 1) pg_dump 全库备份 Supabase  2) pg_restore 恢复到本地 postgres 容器
#       3) alembic upgrade head 应用迁移  4) 校验单头 + 核心表行数
#
# 可选参数:
#   --env-file PATH      运行时 profile（默认 ../config/runtime/production.env）
#   --supabase-url URL   覆盖 SUPABASE_DATABASE_URL 环境变量
#   --project-name NAME  compose 项目名（默认 cameltv-tp-production）
#   --dump-dir PATH      本地 dump 目录（默认 /tmp/cameltv-pg）
#   --skip-dump          跳过备份（复用已有 dump）
#   --skip-restore       跳过恢复
#   --skip-alembic       跳过 Alembic
#   --help               显示帮助

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/../config/runtime/production.env}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-cameltv-tp-production}"
DUMP_DIR="${DUMP_DIR:-/tmp/cameltv-pg}"
PG_IMAGE="${PG_IMAGE:-postgres:16-alpine}"
SUPABASE_URL="${SUPABASE_DATABASE_URL:-}"
DO_DUMP=1
DO_RESTORE=1
DO_ALEMBIC=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --supabase-url) SUPABASE_URL="$2"; shift 2 ;;
    --project-name) COMPOSE_PROJECT_NAME="$2"; shift 2 ;;
    --dump-dir) DUMP_DIR="$2"; shift 2 ;;
    --skip-dump) DO_DUMP=0; shift ;;
    --skip-restore) DO_RESTORE=0; shift ;;
    --skip-alembic) DO_ALEMBIC=0; shift ;;
    --help|-h)
      sed -n '2,20p' "$0"
      exit 0 ;;
    *) echo "未知参数: $1" >&2; sed -n '2,20p' "$0" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }
warn() { printf '\033[1;33m[警告]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[失败]\033[0m %s\n' "$*" >&2; exit 1; }

# 安全解析 KEY=VALUE（跳过注释/空行，不做 shell source，避免密码特殊字符被解释）
load_env() {
  local f="$1" line key val
  while IFS= read -r line; do
    line="${line%%$'\r'}"
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || continue
    key="${line%%=*}"
    val="${line#*=}"
    export "$key=$val"
  done < "$f"
}

# ── 前置检查 ──
command -v docker >/dev/null 2>&1 || fail "未找到 docker，请先安装 Docker + Compose 插件"
[[ -f "$ENV_FILE" ]] || fail "找不到 env-file: $ENV_FILE"
load_env "$ENV_FILE"
POSTGRES_USER="${POSTGRES_USER:-cameltv}"
POSTGRES_DB="${POSTGRES_DB:-cameltv_production}"

if [[ "$DO_DUMP" -eq 1 && -z "$SUPABASE_URL" ]]; then
  fail "缺少 Supabase 连接串：请设置环境变量 SUPABASE_DATABASE_URL 或 --supabase-url"
fi

log "env-file: $ENV_FILE"
log "compose 项目: $COMPOSE_PROJECT_NAME  (postgres 用户=$POSTGRES_USER, 库=$POSTGRES_DB)"

mkdir -p "$DUMP_DIR"

# ── 1) 备份 Supabase ──
DUMP_FILE="$DUMP_DIR/cameltv-prod-$(date +%Y%m%d-%H%M%S).dump"
if [[ "$DO_DUMP" -eq 1 ]]; then
  log "1/4 从 Supabase 全库备份 → $DUMP_FILE"
  docker run --rm -v "$DUMP_DIR:/dump" "$PG_IMAGE" \
    pg_dump "$SUPABASE_URL" -Fc -f "/dump/$(basename "$DUMP_FILE")"
  [[ -s "$DUMP_FILE" ]] || fail "备份文件为空，停止迁移（请勿在空库上继续恢复）"
else
  DUMP_FILE="$(ls -1t "$DUMP_DIR"/cameltv-prod-*.dump 2>/dev/null | head -n1 || true)"
  [[ -n "$DUMP_FILE" && -s "$DUMP_FILE" ]] || fail "--skip-dump 但 $DUMP_DIR 下没有可用的 dump 文件"
  log "1/4 跳过备份，复用 $DUMP_FILE"
fi

# ── 2) 恢复进本地 postgres 容器 ──
if [[ "$DO_RESTORE" -eq 1 ]]; then
  log "2/4 恢复进本地 postgres 容器（pg_restore --clean --if-exists）"
  PG_CONTAINER="$(docker compose --project-name "$COMPOSE_PROJECT_NAME" --env-file "$ENV_FILE" ps -q postgres 2>/dev/null || true)"
  [[ -n "$PG_CONTAINER" ]] || fail "postgres 容器未运行。请先按迁移手册启动 compose 项目（或至少 postgres 服务）"
  docker cp "$DUMP_FILE" "$PG_CONTAINER":/tmp/cameltv-prod-restore.dump
  docker compose --project-name "$COMPOSE_PROJECT_NAME" --env-file "$ENV_FILE" \
    exec -T postgres \
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/cameltv-prod-restore.dump
else
  log "2/4 跳过恢复"
fi

# ── 3) Alembic 迁移 ──
if [[ "$DO_ALEMBIC" -eq 1 ]]; then
  log "3/4 执行 alembic upgrade head"
  docker compose --project-name "$COMPOSE_PROJECT_NAME" --env-file "$ENV_FILE" \
    run --rm --no-deps backend python -m alembic upgrade head
  log "3/4 当前迁移版本（期望单头）:"
  docker compose --project-name "$COMPOSE_PROJECT_NAME" --env-file "$ENV_FILE" \
    run --rm --no-deps backend python -m alembic current
else
  log "3/4 跳过 Alembic"
fi

# ── 4) 校验 ──
log "4/4 校验核心表行数"
for t in users projects sys_organization test_cases test_plans test_plan_executions; do
  rows="$(docker compose --project-name "$COMPOSE_PROJECT_NAME" --env-file "$ENV_FILE" \
    exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
    "SELECT count(*) FROM $t" 2>/dev/null || echo "N/A")"
  printf '  %-24s %s\n' "$t" "$rows"
done

log "迁移完成。备份文件: $DUMP_FILE"
log "下一步：按迁移手册 §8 冒烟验证，确认后再切换 DNS 与下线旧环境。"
