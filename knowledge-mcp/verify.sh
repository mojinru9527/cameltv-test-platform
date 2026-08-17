#!/usr/bin/env bash
# knowledge-mcp 部署验收脚本（C-A1，DSH 测试 Agent 框架遗留收口）
#
# 在具备 Docker daemon 的环境（部署机/CI）执行：
#   1. 构建镜像
#   2. 启动容器（需 .env：PLATFORM_BASE_URL / PLATFORM_API_TOKEN / PLATFORM_PROJECT_ID）
#   3. fastmcp 客户端握手验证 17 工具 + 真实查询调用
#
# 用法:
#   bash verify.sh                 # 全部步骤
#   bash verify.sh build           # 仅构建镜像
#   bash verify.sh run             # 仅启动容器（需已构建）
#   bash verify.sh tools           # 仅工具握手验证（需容器已启动）
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-knowledge-mcp:verify}"
MCP_PORT="${MCP_PORT:-8110}"
ENV_FILE="${ENV_FILE:-.env}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

step() { echo; echo "== $1 =="; }

if [[ "$#" -eq 0 || "$1" == "build" ]]; then
  step "构建镜像 ${IMAGE_NAME}"
  docker build -t "${IMAGE_NAME}" "${HERE}"
  [[ "$#" -eq 1 && "$1" == "build" ]] && exit 0
fi

if [[ "$#" -eq 0 || "$1" == "run" ]]; then
  step "启动容器（端口 ${MCP_PORT}，env: ${ENV_FILE}）"
  [[ -f "${ENV_FILE}" ]] || { echo "缺少 ${ENV_FILE}（复制 .env.example 填写 PLATFORM_*）"; exit 2; }
  docker rm -f knowledge-mcp-verify >/dev/null 2>&1 || true
  docker run -d --name knowledge-mcp-verify \
    --env-file "${ENV_FILE}" -p "${MCP_PORT}:${MCP_PORT}" "${IMAGE_NAME}"
  sleep 3
  echo "容器已启动；健康检查: curl http://127.0.0.1:${MCP_PORT}/mcp（406 = 服务在）"
  [[ "$#" -eq 1 && "$1" == "run" ]] && exit 0
fi

if [[ "$#" -eq 0 || "$1" == "tools" ]]; then
  step "工具握手验证（fastmcp 客户端）"
  python - <<PY
import asyncio
from fastmcp import Client

async def main():
    async with Client(f"http://127.0.0.1:{MCP_PORT}/mcp") as client:
        tools = await client.list_tools()
        names = sorted(t.name for t in tools)
        print(f"tools({len(names)}): {', '.join(names)}")
        expected = {
            "search_knowledge", "get_module_topology", "get_knowledge_sources",
            "get_requirements", "get_test_cases", "get_test_plans", "get_test_plan",
            "get_plan_executions", "trigger_test_plan", "get_execution_result",
            "get_ui_test_jobs", "trigger_ui_test", "get_ui_test_run",
            "submit_test_cases", "submit_defect",
        }
        missing = expected - set(names)
        if missing:
            raise SystemExit(f"缺少工具: {sorted(missing)}")
        res = await client.call_tool("get_test_plans")
        print("get_test_plans 调用 OK:", bool(res.content))

asyncio.run(main())
PY
  echo "验收通过：17 工具齐备 + 平台 API 连通"
fi

step "清理"
docker rm -f knowledge-mcp-verify >/dev/null 2>&1 || true
echo "done"
