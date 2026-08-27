# sports_api_cases — 足球/篮球接口用例真实数据版（Batch 205）

按顺序执行（需 Test5 VPN 已连 + 清残留代理 NO_PROXY=*）：

1. `01_harvest_param_pool.py` — 收割真实 id/名称参数池 → `_tmp_real_param_pool.json`
2. `02_generate_cases.py` — 生成正向(真实参数)+负向(缺参/类型错/越权)用例 → `_tmp_cases_generated.json`
3. `03_execute_cases.py` — 真实执行**只读 GET** 正向用例（首轮）→ `_tmp_cases_executed.json`
4. `03b_execute_cases_httpx.py` — **Q4 全量执行**（含负向+写操作；httpx keep-alive 连接池 + 连接/DNS 错误重试，超时不重试）→ `_tmp_cases_executed.json`
5. `04_postprocess_envelope.py` — 按真实响应信封自适应断言并重评估 → `_tmp_cases_final.json`
6. `05_write_db.py` — 首轮落库 platform.db（basketball-service + test_case）
7. `06_update_db.py` — Q4 后按 case_id UPDATE 已落库用例的执行结果（不重复插入）

口径：`tests/test-case-standards/接口用例必填真实数据规范.md`
证据：`work-logs/evidence/batch-205/`

**执行注意**：urllib 逐请求做 DNS 解析，在快速连续请求下会触发本地 DNS 打挂（getaddrinfo failed，一次 801 条误失败）；Q4 改用 httpx keep-alive 复用连接后 network_err 降到 31（慢接口超时），结果可信。写操作（save/bet/sub 等）在 Test5 未登录返回 status:400「Please login first」，写接口鉴权生效——经有效登录态执行写操作需单独批次。
