# Batch 112 — Design Spec（response_structure 断言引擎 + 4 端点校准 + 批量/UI 定时验证）

> **Design (🎨)** | Date: 2026-08-07 | Status: 就绪

## 0. 技术体系确认

后端：FastAPI + SQLAlchemy + httpx（`api_execution_service.py` 既有断言引擎扩展，不改路由/模型/Schema）。
脚本：repo 根 `scripts/sports/*.py`（psycopg2 + httpx），与 Batch 110/111 同目录约定。
前端：本批无 React 改动（仅走查既有链路，无 UI 交付）。

## 1. response_structure 断言引擎规格

### 1.1 断言规则结构（与生成器 `_response_structure_assertions` 对齐）

| 字段 | 取值 | 语义 |
|------|------|------|
| type | `response_structure` | 触发引擎分支 |
| path | `status` / `data` / `data.records` / `data.records[0].id` / `data.team` | 点号路径，兼容 `[0]` 下标与空 `[]`（跳过） |
| assert | `exists` / `not_empty` / `is_object_or_array` / `len_lte` / `hint` | 判定类型 |
| expected | len_lte 上限 / 其他 | 期望值 |
| note | 提示文案 | 仅 hint 使用 |

### 1.2 求值语义（事实源：`scripts/sports/execute-interface-cases.py::_assert_structure`，97/97 已验证）

| 类型 | 规则 | 结果 |
|------|------|------|
| exists | 路径存在（键在 dict 或下标在 list 内） | 通过；envelope 键缺失 → 失败 |
| exists / is_object_or_array / not_empty | `path == "data"` 或 `path.startswith("data.")` 且节点缺失 | **warning（passed=True）**——动态数据 200 信封豁免，不判失败 |
| is_object_or_array | 节点存在且为 dict/list | 通过；其他类型 → 失败 |
| not_empty | 节点存在且非空（`""`/`[]`/`{}`/`None`） | 通过；空值 → 失败 |
| not_empty | 路径含 `records[` / `[0]`（记录字段） | 以键存在为准，值可为空 → 通过 |
| len_lte | 节点为 list 且 `len <= expected` | 通过；超界 → 失败 |
| hint | 信息性提示 | 不参与判定（passed=True，带 warning 标记） |

> 说明：`data.*` 动态豁免是 Batch 110 B110-5 既定口径（search/query 部分时段空 data），
> 引擎必须与脚本侧一致，避免平台与脚本双口径。

### 1.3 实现落点

- `api_execution_service._run_assertions`（`backend/app/services/api_execution_service.py:322-355`）：
  增加 `elif atype == "response_structure": r = _assert_response_structure(rule, response_data)`。
- 新增 `_assert_response_structure(rule, data)`：路径解析复用 `_split_path`/`_resolve_segment`
  （`:718-768`），缺失哨兵复用 `_JSONPATH_MISSING`（`:700`）。
- 结果 dict 增加可选 `warning` 字段（动态数据豁免时 `passed=True + warning`），UI 兼容（未知字段不破坏展示）。

## 2. 4 端点校准规格（生产实测基线 2026-08-07）

| 端点 | 根因 | 校准动作 | 校准后预期 |
|------|------|---------|-----------|
| `/account-service/login/anonymous/web` | 契约=formData `appCode` + 必填 `clientip` 头；用例发 JSON 无头 | api_headers=`Content-Type: application/x-www-form-urlencoded` + `clientip`；api_body=`appCode=...`（URL 编码） | code=0 / success=true，信封 `{code,msg,detail,success}` |
| `/account-service/ee/ads/activity/get` | 契约必填 `Accept-Language`/`deviceId`/`X-Real-IP` | api_headers 补三头；body 保留真实参数 | status=200 + data |
| `/camel-service/ee/search/query` | 契约必填 `Accept-Language` | api_headers 补 `Accept-Language: en`；query 保留真实参数 | status=200 + data |
| `/camel-service/ee/news/get` | 生产全 id 业务 400（服务端缺陷）；用户端实际走 `get_visible` | 重指向 `/camel-service/ee/news/get_visible`（同真实 id）；缺陷 B112-1 登记 | status=200 + data（get_visible 实测正常） |

校准流程（`scripts/sports/calibrate-interface-cases.py`）：
1. 直连生产库，按 module 选 4 端点 `batch:110` api 用例（先读旧断言/请求做 before 快照）。
2. 以真实请求参数（含校准头/表单）生产实跑取响应，推导响应结构断言元数据。
3. 复用 `api_case_generation_service.generate_cases_from_real_sample` 重新生成用例，
   按真实响应 `_fix_assertion_paths` 修正路径，保留 `batch:110` + 追加 `batch:112`/`calibrate:batch-112` 标签。
4. 幂等替换该 module 旧用例（DELETE + INSERT，与 generate-interface-cases.py 同条件）。
5. 实跑校验每条用例（status + 结构断言），输出 `evidence/batch-112/calibration-summary.json`
   （before/after + 逐端点 passed/failed + 响应摘要）。

## 3. 批量执行重跑规格（run-batch-execution.py 增强）

- 新增 `--label`（默认 `batch-111` 保持兼容）：证据目录 `evidence/{label}/`、任务名 `体育平台-批量执行-{label}`。
- 回填核对后追加按端点聚合明细：`SELECT split_part(api_endpoint,'?',1) ep, last_run_status, COUNT(*) ...
  GROUP BY ep, last_run_status` → `evidence/batch-112/batch-execution-summary.json` 增 `by_endpoint` 数组。
- 本批运行 `--label batch-112`，目标 passed=170/failed=0。

## 4. UI 定时回归规格（setup-ui-schedule.py 增强，C111-3）

- 新增 `--label`（默认 `batch-111`）：证据文件 `evidence/{label}/ui-schedule-summary.json`。
- 触发后轮询 `GET /api/v1/ui-tests/runs/{run_id}`（用户 Bearer 鉴权，`backend/app/api/v1/ui_test.py:159`）：
  每 10s 一次，最长 10 分钟；终态（success/fail）后写入 `status/result/stdout 摘要/finished_at`。
- 复用既有 job/schedule 幂等逻辑：job「体育平台-P0-每日生产只读回归」已存在则复用，否则创建；
  schedule 同。触发 run 后核对 P0 spec 10/10（stdout 摘要含 passed 计数）。

## 5. 设计 QA 走查发现

本批无前端 UI 改动；设计走查聚焦「平台断言执行链路」：

### ⚪ P3-1 断言结果 UI 不展示 warning
平台 CaseDrawer 断言列表按 passed/failed 渲染；warning 字段为新增，前端暂不展示。
**建议**：本批不阻塞（引擎语义正确即可）；C112-1 知识中心批次顺带评估断言 warning 展示。

## 6. 设计签核

结论：**通过**（无 P0/P1 阻断项；warning 展示为 P3 建议，登记不阻塞）。
