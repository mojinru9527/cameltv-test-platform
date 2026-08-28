# Batch 206 — QA 报告：C205-1/2/3 修复（超时配置化 + 写操作矩阵 + 参数精修尝试）

> **QA (🟩)** | Date: 2026-08-28 | Executor: DeepSeek_Harness | 分支 `fix/batch-206-c205-fixes`

## 1. 目标
关闭 Batch 205 遗留 C 条件：
- **C205-2**：平台 API 执行超时配置化（慢接口不误判超时）
- **C205-3**：写操作经有效登录态执行，记录成功/拒绝矩阵
- **C205-1**：13 条 GET 用例参数精修，复跑归零 status:400

## 2. 结果

### ✅ C205-2（代码）
- `config.py` 新增 `api_execution_timeout_seconds`（默认 30，env `API_EXECUTION_TIMEOUT_SECONDS` 可调）
- `api_execution_service.py:DEFAULT_TIMEOUT` 改读 `settings.api_execution_timeout_seconds`
- 新增 `tests/test_batch206_c205_timeout_config.py`（4 测试）+ 57 个执行相关测试全绿

### ✅ C205-3（写矩阵，用户登录态 uid+token）
- 用 Test5 用户 `+86 18476944071` 登录 → `token=52e0c438...`、`uid=11025728`
- 写接口鉴权：`{uid, token}` header
- 执行 camel/basketball 全部 POST：**56 成功 / 59 拒绝 / 7 错误**
- 金融/删除类：`forecast/bet`(400 拒绝)、`article/buy`(400 拒绝) → **无真实下单/购买**
- ⚠️ 真实写入副作用（Test5 测试数据）：`gen_stream`(生成推流 URL)、`forecast/settle/done/cancel`(结算预测)、`faq/delete`、`stop_push/set_logo/set_hd/cancel_hd/del_stream` —— **用户已确认可接受**

### ⚠️ C205-1（部分，未完全解决）
- 定位 54 条候选，10 条参数已更新（`init_language?types=en`、`home_favorite?day=..&uid=11025728`）
- 但**复跑仍 400**（httpx 直连验证）：这些端点（init_language/home_favorite/names/season/recent/article/read/news/get）的正确业务参数**无法从现有信息确定**（需特定业务数据/枚举/格式）
- `article/read` 需 articleId，Test5 无文章数据 → 无可修
- **结论**：C205-1 非代码问题，参数语义需业务方提供确切值，**标记未完全解决**（C205-1 保持 Open）

## 3. 处置
- C205-2 代码合入（本分支）；C205-3 证据 `_tmp_c205_3_matrix.json`
- C205-1 保持 Open（需业务方提供确切参数语义）

## 证据
- `work-logs/evidence/batch-206/c205_3_matrix.json`（写矩阵）
- `tests/test_batch206_c205_timeout_config.py`
