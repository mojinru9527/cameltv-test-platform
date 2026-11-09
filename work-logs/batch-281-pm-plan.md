# Batch 281（M1 / TA-007）— PM 计划

> **部门**：🟩 PM · **日期**：2026-11-10

## 里程碑

M1 第 3 批：279 ✅ → 280 ✅ → **281（本批）** → 282 Console。

## WBS

| # | 工作项 | 产出 | 状态 |
|---|--------|------|:----:|
| 1 | run_artifacts 模型 | `aiqe/models/artifact.py` | ✅ |
| 2 | 存储抽象 + 本地 FS | `aiqe/services/artifact_storage.py` | ✅ |
| 3 | Artifact 服务（去重/鉴权/脱敏） | `aiqe/services/artifact_service.py` | ✅ |
| 4 | 迁移 20261113 | `20261113_ta007_run_artifacts.py` | ✅ |
| 5 | 单测 6 | `tests/test_aiqe_artifact_service.py` | ✅ |
| 6 | 全量 + ratchet | 1392 passed / PASS | ✅ |
| 7 | 六件套 + 看板 | work-logs | ✅ |

## 依赖

- batch-279/280 表与服务 ✅；
- `settings.storage_dir` 未显式声明 → 用 `getattr` 回退 `storage/`（D-281-2）。

## 放行

A1–A7 全绿 → Leader APPROVED → PR checks → 合入 → batch-282。
