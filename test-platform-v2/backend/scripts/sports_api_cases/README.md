# sports_api_cases — 足球/篮球接口用例真实数据版（Batch 205）

按顺序执行（需 Test5 VPN 已连 + 清残留代理 NO_PROXY=*）：

1. `01_harvest_param_pool.py` — 收割真实 id/名称参数池 → `_tmp_real_param_pool.json`
2. `02_generate_cases.py` — 生成正向(真实参数)+负向(缺参/类型错/越权)用例 → `_tmp_cases_generated.json`
3. `03_execute_cases.py` — 真实执行只读 GET 正向用例 → `_tmp_cases_executed.json`
4. `04_postprocess_envelope.py` — 按真实响应信封自适应断言并重评估 → `_tmp_cases_final.json`
5. `05_write_db.py` — 落库 platform.db（basketball-service + test_case，含备份）

口径：tests/test-case-standards/接口用例必填真实数据规范.md
证据：work-logs/evidence/batch-205/
