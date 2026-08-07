# Batch 112 — PM Plan（response_structure 断言引擎 + 4 端点校准 + 批量全绿 + C111-3）

> **PM (🟨)** | Date: 2026-08-07

## 规格摘要

**原始需求**: PRD §1（引擎缺口/4 端点基线失效/C111-2·C111-3 闭环）
**目标时间**: 1 开发日（切片 30–60 分钟）
**执行器**: codex（用户确认）

## 开发任务

### [ ] Task 1: 批次工件 + 看板 + response_structure 断言引擎（TDD）
**描述**: 写 PRD/PM/Design/看板；`api_execution_service._run_assertions` 增加 `response_structure` 分支，
实现 `_assert_response_structure`（exists/not_empty/is_object_or_array/len_lte + `data.*` 动态豁免 warning +
hint 信息提示）；语义对齐 `scripts/sports/execute-interface-cases.py::_assert_structure`。
**验收标准**: 新增 `tests/test_api_execution_response_structure.py` 全绿（含 envelope 缺失失败、
data 动态豁免通过、records 路径解析、len_lte 边界、hint 提示）；既有 `test_apitest_generation.py` 无回归；
`ruff check app --select F821` 通过。
**涉及文件**: - `backend/app/services/api_execution_service.py` — 断言引擎
            - `backend/tests/test_api_execution_response_structure.py` — 新增测试
**参考**: PRD §4 / 设计规范 §3

### [ ] Task 2: 4 端点用例校准脚本 + 生产校准
**描述**: 新增 `scripts/sports/calibrate-interface-cases.py`：直连生产库，对 4 个端点模块
（login/anonymous/web、ads/activity/get、search/query、news/get）按生产实测校准：
login → formData + clientip 头；ads/search → 补 Accept-Language/deviceId/X-Real-IP；news/get → 重指向
news/get_visible（同真实 id）；重新生成用例（真实响应基线）并替换旧用例，保留 batch:110 标签。
运行后输出证据 JSON（before/after + 实跑校验）。
**验收标准**: 校准后 4 端点生产实跑恢复成功响应；证据 JSON 落盘 `evidence/batch-112/calibration-summary.json`。
**涉及文件**: - `scripts/sports/calibrate-interface-cases.py` — 新增
            - `scripts/sports/generate-interface-cases.py` — 复用生成逻辑（不改）
**参考**: PRD §4 / 设计规范 §4

### [ ] Task 3: 批量执行重跑（170 条）全绿 + 回填核对
**描述**: `run-batch-execution.py` 增加 `--label` 参数（证据目录/任务名），并补充按端点聚合的
passed/failed 明细输出；运行生产批量执行 170 条，核对 last_response_json/last_run_status。
**验收标准**: task passed=170/failed=0；`evidence/batch-112/batch-execution-summary.json` 含端点明细。
**涉及文件**: - `scripts/sports/run-batch-execution.py` — 增强
**参考**: PRD §4 / 设计规范 §4

### [ ] Task 4: C111-3 UI 定时回归触发 + 报告核对
**描述**: `setup-ui-schedule.py` 增加 `--label` + 触发后轮询 `GET /ui-tests/runs/{run_id}`，
运行状态/结果写入证据；核对 P0 spec 10/10。
**验收标准**: `evidence/batch-112/ui-schedule-summary.json` 含 run 状态与结果摘要；QA 核对 10/10。
**涉及文件**: - `scripts/sports/setup-ui-schedule.py` — 增强
**参考**: PRD §4 / 设计规范 §4

### [ ] Task 5: QA 硬门禁 + QA 报告 + Leader + 一次总确认
**描述**: 执行后端 pytest/ruff、脚本 py_compile；审计 C 条件（C111-2/C111-3 关闭、B112-1 登记、
C112-1/C112-2 新增）；写 QA/Leader；展示变更摘要做一次总确认 → push → Draft PR。
**验收标准**: 工件齐全；audit-cconditions 0 硬错；用户总确认后推送。
**涉及文件**: - `work-logs/batch-112-*-qa-report|leader-verdict.md`
            - `C-CONDITIONS.md`

## 质量要求

- [ ] TDD：断言引擎先写失败测试再实现
- [ ] 后端 pytest（test_api_execution_response_structure + test_apitest_generation + test_api_task_worker）记录退出码（C78-1）
- [ ] `ruff check app --select F821`（受影响模块）
- [ ] 脚本 py_compile 0 错误
- [ ] 无调试残留；无硬编码密钥（生产密码/DB URL 走参数/env，不入库）
- [ ] 双 404 约定（C86-1）适用于新增断言（本批无裸 status_code==404）
- [ ] 生产操作 confirm_prod 显式；只读守卫与只读口径维持
