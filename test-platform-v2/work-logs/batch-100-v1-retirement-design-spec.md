# Batch 100 — Design Spec（V1 整体退役）

> **Design (🎨)** | Date: 2026-08-06 | Status: 就绪

## 1. 迁移与删除清单

| 项 | 处理 | 理由 |
|----|------|------|
| `test-platform/tests/api-testing/generated/**`（9 文件） | `git mv` → `tests/api-testing/generated/` | CI 每日回归资产（Playwright 自包含） |
| `test-platform/tests/api-testing/specs/cameltv-openapi.yaml` | `git mv` → `tests/api-testing/specs/` | OpenAPI 静态副本（文档引用） |
| `test-platform/web-ui/` | 删除 | V2 前端覆盖（用户规则：覆盖即移除） |
| `test-platform/server/` | 删除 | V2 后端覆盖 |
| `test-platform/cli/` `core/` `config/` | 删除 | CI 已迁移，无消费者；业务地址在交付清单 |
| `test-platform/docker/` `docker-compose.yml` `setup.*` `pyproject.toml` `requirements.txt` `README.md` `CLAUDE.md` `COMMANDS.md` `.env.example` `.dockerignore` `.gitignore` `data/` `platform_tests/` `tools/` | 删除 | v1 部署/自测/文档 |

## 2. 引用更新

| 文件 | 变更 |
|------|------|
| `.github/workflows/api-regression.yml` | `working-directory: tests/api-testing/generated` |
| `.github/workflows/prod-smoke-test.yml` | 同上 |
| `scripts/ci/api-regression.ps1` | `$specDir` 主路径改为 `tests/api-testing/generated`（删除 v1 分支） |
| `test-platform-v2/backend/scripts/migrate_cases.py` | 旧库路径提示改为历史说明 |
| `repo-boundaries.json` | 移除 `deprecated-v1` 仓库条目 |
| `scripts/repo-split/validate_repo_boundaries.py` | 文案去掉 deprecated-v1 |

## 3. 文档状态更新

- `CLAUDE.md`：目录表 v1 行改为「已退役移除」；相关引用更新。
- `COMMANDS.md`：v1 章节标记退役（保留历史说明或精简）。
- `docs/repo-map.md`：§2.2 改为退役说明。
- `docs/生产级验收现状与体育平台承接规划.md`：§6 V1 瘦身状态更新为已完成。
- `docs/测试平台全功能验收文档-环境链接与账号汇总.md` / 交付清单：v1 config 来源标注退役。
- `.claude/skills/cameltv-api-test*`：v1 CLI 描述更新（tp 已移除）。

## 4. 安全

- 删除前将 gitignored `test-platform/.env` 复制到仓库外（`F:/CamelTv-safe-backup/`），业务凭据不丢失。
- 所有删除走 `git rm`（历史可恢复）。

## 5. 设计签核

结论：**通过**。风险控制：先迁后删；`rg -P 'test-platform/(?!v2)'` 非文档 0 命中 + boundary PASS 为出口标准。
