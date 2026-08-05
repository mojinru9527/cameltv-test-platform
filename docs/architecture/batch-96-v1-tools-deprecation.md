# Batch 96 — V1 开发工具引用审计与废弃批准（C64-1）

> 状态：已审计 + 用户批准废弃（2026-08-05） | 移除计划见 §4 | 实际删除待独立清理批次

## 1. 范围

C64-1 要求：V1（`test-platform/`）B 档开发工具逐项迁移或用户批准废弃后才可删除。用户已授权：「如果没有使用，批准废弃」。

## 2. 工具清单与 V2 引用审计（2026-08-05）

| V1 工具目录 | 定位 | V2 代码/脚本引用 | 结论 |
|------------|------|-----------------|------|
| `tools/mock_server` | 接口 mock | 无（V2 自有 mock OCR provider 与 V1 无关） | **未使用 → 批准废弃** |
| `tools/api_diff` | 接口差异对比 | 无（V2 用 `services/lanhu_evidence/diff_service.py`） | **未使用 → 批准废弃** |
| `tools/api_tester` | 接口测试 CLI | 无（V2 用 apitest 模块） | **未使用 → 批准废弃** |
| `tools/av_checker` | 专项检测 | 无（V2 用 av_check 模块） | **未使用 → 批准废弃** |
| `tools/data_factory` | 造数 | 无 | **未使用 → 批准废弃** |
| `tools/env_check` | 环境检查 | 无（V2 用 preflight/health） | **未使用 → 批准废弃** |
| `tools/load_tester` | 压测 | 无 | **未使用 → 批准废弃** |
| `tools/log_aggregator` | 日志聚合 | 无（V2 用 ELK/日志查询） | **未使用 → 批准废弃** |
| `tools/project_init` | 项目初始化 | 无 | **未使用 → 批准废弃** |
| `tools/report_dashboard` | 报告看板 | 无（V2 用 report 模块） | **未使用 → 批准废弃** |
| `tools/traffic_monitor` | 流量监控 | 无 | **未使用 → 批准废弃** |

> 审计方法：`rg` 全仓检索工具名（含 mock/capture/apidiff/datafactory/logagg/loadtest/envcheck 等关键词），
> 排除 node_modules/venv/work-logs/docs 后，V2 `app/`、`frontend/src/`、`scripts/` 均无 import/exec/CLI 调用；
> 命中的「mock/capture」均为 V2 自身功能或文档词汇（如 `LANHU_OCR_PROVIDER=mock`）。

## 3. 用户批准记录

- 批准人：用户（平台负责人）
- 日期：2026-08-05
- 授权范围：`test-platform/tools/` 下未被 V2 引用的 11 个工具目录批准废弃
- 依据：batch-96 引用审计（§2）

## 4. 移除计划（待独立清理批次执行）

1. 删除 `test-platform/tools/` 下 11 个工具目录（`git rm -r`）。
2. 运行 `scripts/repo-split/validate_repo_boundaries.py --check`（deprecated-v1 仍保留 web-ui/server/cli 等）。
3. 运行后端全量 pytest + 前端 build，确认无隐藏引用。
4. 更新 `repo-boundaries.json` / 覆盖矩阵状态。
5. V1 `web-ui/` 与 `server/` 按覆盖矩阵继续保留（不在本批准范围）。

> ⚠️ 本批只完成审计与批准登记；**实际删除**在独立清理批次执行，移除后若发现遗漏引用以 git 历史恢复。
