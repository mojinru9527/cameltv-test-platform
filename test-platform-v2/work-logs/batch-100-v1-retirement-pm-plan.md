# Batch 100 — PM Plan（V1 整体退役）

> **PM (🟨)** | Date: 2026-08-06 | Status: Review

## 切片拆解

| # | 任务 | 描述 | 验收标准 | 涉及文件 |
|---|------|------|---------|---------|
| 1 | 迁移测试资产 | `git mv` generated/ + specs/ → `tests/api-testing/` | 文件就位；路径引用更新 | `test-platform/tests/api-testing/**` → `tests/api-testing/**` |
| 2 | 更新 CI 路径 | workflows + 脚本指向新路径 | `rg 'test-platform/tests'` 0 命中 | `.github/workflows/*.yml`、`scripts/ci/api-regression.ps1` |
| 3 | 删除 V1 其余 | `git rm -r` 剩余 v1 目录与文件（含 migrate_cases 旧库提示更新） | `test-platform/` 不存在；`rg -P 'test-platform/(?!v2)'` 非文档 0 | `test-platform/**`（除已迁移） |
| 4 | 边界与脚本 | repo-boundaries 移除 deprecated-v1；validator 文案；.gitignore 核对 | boundary PASS | `repo-boundaries.json`、`scripts/repo-split/validate_repo_boundaries.py`、`.gitignore` |
| 5 | 文档与技能 | CLAUDE/COMMANDS/repo-map/规划/交付清单/技能 更新 | 关键文档无「维护模式」v1 指引 | `CLAUDE.md`、`COMMANDS.md`、`docs/**`、`.claude/skills/*` |
| 6 | C-CONDITIONS | C64-1 关闭 + batch-100 登记 | audit 0 硬错 | `C-CONDITIONS.md` |
| 7 | QA + Leader | 门禁 + 工件 | 全绿 | `test-platform-v2/work-logs/batch-100-*` |

## 依赖与顺序

1 → 2 → 3 → 4 → 5 → 6 → 7。先迁后删；删除前备份 gitignored `.env`。

## 范围外

- V1 旧数据迁移（旧库快照 DEFERRED）；V2 业务代码改动；体育平台承接（Batch 101+）。
