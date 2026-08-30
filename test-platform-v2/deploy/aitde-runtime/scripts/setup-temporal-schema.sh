#!/bin/bash
# AITDE V3.4 Durable Runtime — Temporal schema setup one-shot（postgres12）
#
# 挂载的 /etc/temporal/config/docker.yaml 使用 postgres12 持久化 + visibility，
# 因此 temporal-sql-tool 的 config-load 不会回退 Cassandra。
# 等价于 auto-setup.sh 的 setup_postgres_schema；这里单独跑，避免 auto-setup
# 内置 temporal-sql-tool 与 server 启动耦合的已知问题。
set -eu -o pipefail

PG_HOST="${POSTGRES_SEEDS:-temporal-postgres}"
PG_PORT="${DB_PORT:-5432}"
PG_USER="${POSTGRES_USER:-temporal}"
PG_PWD="${POSTGRES_PASSWORD:-temporal}"
DBNAME="${DBNAME:-temporal}"
VIS="${VISIBILITY_DBNAME:-temporal_visibility}"
SCHEMA_DIR="/etc/temporal/schema/postgresql/v12"

until nc -z "${PG_HOST}" "${PG_PORT}"; do
  echo "waiting for postgres ${PG_HOST}:${PG_PORT}"
  sleep 2
done
echo "postgres up"

# 创建默认库（幂等：已存在则工具会报错，忽略）
temporal-sql-tool --plugin postgres12 --ep "${PG_HOST}" -u "${PG_USER}" -p "${PG_PORT}" \
  --db "${DBNAME}" --password "${PG_PWD}" create 2>/dev/null || true
temporal-sql-tool --plugin postgres12 --ep "${PG_HOST}" -u "${PG_USER}" -p "${PG_PORT}" \
  --db "${VIS}" --password "${PG_PWD}" create 2>/dev/null || true

# 主库: setup-schema + update-schema
temporal-sql-tool --plugin postgres12 --ep "${PG_HOST}" -u "${PG_USER}" -p "${PG_PORT}" \
  --db "${DBNAME}" --password "${PG_PWD}" setup-schema -v 0.0
temporal-sql-tool --plugin postgres12 --ep "${PG_HOST}" -u "${PG_USER}" -p "${PG_PORT}" \
  --db "${DBNAME}" --password "${PG_PWD}" update-schema -d "${SCHEMA_DIR}/temporal/versioned"

# visibility 库: setup-schema + update-schema
temporal-sql-tool --plugin postgres12 --ep "${PG_HOST}" -u "${PG_USER}" -p "${PG_PORT}" \
  --db "${VIS}" --password "${PG_PWD}" setup-schema -v 0.0
temporal-sql-tool --plugin postgres12 --ep "${PG_HOST}" -u "${PG_USER}" -p "${PG_PORT}" \
  --db "${VIS}" --password "${PG_PWD}" update-schema -d "${SCHEMA_DIR}/visibility/versioned"

echo "schema setup done"
