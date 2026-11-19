# 外部 Runner 真实 E2E（Test 环境）

- Run：`99496744-1740-44e8-b41e-47f7903d9623`（`EXT-RUNNER-20261119T074106Z`），状态 **COMPLETED/PASS**
- Runner：`android-oneplus6t-9f0564ba`，独立进程 + 节点 token；能力心跳 `VERIFIED`
- 节点 1：HTTP 直连 Camel Test5 `/account-service/ee/client/general` → PASSED（断言 200）
- 节点 2：`external_e2e` 调用真实 adb Android 冒烟（OnePlus 6T / `com.camelrn`）→ PASSED
- Artifacts：3 个（截图/UI/result.json，sha256 已对账）

## 链路

1. `POST /api/v1/ai/agents/register` 签发节点 token；
2. `register_manifest` + `mark_verified`（`aiqe:http` / `aiqe:external_e2e` / `device.android`）；
3. `launch_run(graph_override=...)` 创建 Run/ExecutionJob（Preflight 通过）；
4. Runner 进程 `aiqe_local_runner.py`：
   - 启动/每 5s `POST /api/v1/aiqe/nodes/{node_id}/heartbeat`；
   - claim → 执行 HTTP + adb external_e2e → 上传证据 → report；
5. 平台回写 NodeRun/Run 终态，Artifact 落库。

## Artifacts

- `SCREENSHOT` `d9608fd3-cee8-4ef3-b6f4-ade26ec1a284` size=208217 sha256=`6998e93311dadadd0f08711c4d3713342078d775c5c5937c0e029103c6d23766`
- `DOM_SNAPSHOT` `993e13d5-e84c-4e70-89f6-5b857410493e` size=22581 sha256=`b73bfb8dec11e3a4d2733d5d009f32a72f10687c3941de6a4b790c38d2f4e8bc`
- `RUNNER_LOG` `46413ffe-cb70-488c-8d18-1b152f76a595` size=212 sha256=`02c1bc00dd7234f6b969bb60988808e0f8669d34e9c748c4e336d000e8e48598`

## 说明

- 控制面为本地 Test 平台（最新 main + 心跳接口），Runner 是独立进程；
- HTTP 目标与 Android 设备均为真实环境/真机；未创建/修改 Camel Test5 业务数据。
