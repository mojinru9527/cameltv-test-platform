# Batch 266 PM 计划

> **PM** | Date: 2026-09-19

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 1 | 节点断言：算子 + 新类型 | `executor.evaluate_assertions` | ✅ |
| 2 | 节点 Web 隔离 + 异常收敛 + 可见性语义 | `run_web_cases` / `_run_one_web_case` / `_any_visible` | ✅ |
| 3 | 驱动 payload 可执行化 + 缺定义即失败 | `drill_three_versions._load_executable_cases` | ✅ |
| 4 | 回归测试 | `tests/test_batch266_executor_payload_and_isolation.py` | ✅ |
| 5 | 真实环境实跑取证 | 本机平台 + 节点 + Test5 | ✅（见 QA） |
| 6 | C 条件与看板 | `C-CONDITIONS.md` | ✅ |

风险与处置：本机内存 15.8GB，Docker Desktop + 平台 + 节点 + 逐用例 Chromium 易 OOM → 实跑前 `wsl --shutdown` 释放；僵尸任务需清理（已记入 QA 复盘）。
