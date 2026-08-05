# Batch 98 — PM Plan（CI 迁移 + V1 工具删除）

> **PM (🟨)** | Date: 2026-08-05 | Status: Review

## 切片拆解（每片 30–60 分钟）

| # | 任务 | 描述 | 验收标准 | 涉及文件 |
|---|------|------|---------|---------|
| 1 | CI 回归脚本 | 新增 `scripts/ci/api-regression.ps1`（health / run / collect-elk 三子命令，stdlib PowerShell） | 三子命令本地语法校验通过；无第三方 Python 依赖 | `scripts/ci/api-regression.ps1` |
| 2 | api-regression workflow 迁移 | 重写 `api-regression.yml`：去 V1 安装，token 刷新保留，health+run 走脚本，JUnit artifact 上传，失败时 collect-elk | 文件不再出现 `tp ` 命令；步骤齐全 | `.github/workflows/api-regression.yml` |
| 3 | prod-smoke workflow 迁移 | 重写 `prod-smoke-test.yml`：VPN 探测 + token 刷新 + 实际执行 6 个只读 spec（不再空跑） | 不再出现 `tp ` 命令；`--grep smoke` 移除 | `.github/workflows/prod-smoke-test.yml` |
| 4 | 删除 11 个 V1 工具 | `git rm -r` 11 个 `tools/*` 目录 | 目录不存在；`rg` 0 引用 | `test-platform/tools/{11 目录}` |
| 5 | 清理引用 | `cli/tp.py` 移除工具命令（保留 config/sites）；`server/main.py` 移除 envcheck/api_test/datafactory 路由并删文件 | CLI/server 语法检查通过；`rg` 0 引用 | `test-platform/cli/tp.py`、`test-platform/server/main.py`、`server/routes/{envcheck,api_test,datafactory}.py` |
| 6 | 元数据与文档 | `repo-boundaries.json` deprecated-v1 规则更新；C-CONDITIONS（C64-3 关闭、C96-1 部分关闭）；交付清单/规划文档同步 | audit-cconditions 0 硬错；文档保鲜 exit 0 | `repo-boundaries.json`、`C-CONDITIONS.md`、`docs/production-delivery/*`、`docs/生产级验收现状与体育平台承接规划.md` |
| 7 | QA + 工件 | 门禁执行（pytest/scan/audit/boundary/rg）+ QA/Leader/看板 | 全部 exit 0 / PASS | `test-platform-v2/work-logs/batch-98-*` |

## 依赖与顺序

1 → 2 → 3 → 4 → 5 → 6 → 7。切片 4 依赖 1–3（先迁移后删）；切片 5 依赖 4。

## 范围外（明确不纳入）

- V1 web-ui/server 移除（Batch 99）；Test5 契约补拉（C95-1）；prod 业务 DB/Redis（C64-3，用户确认无法提供）。
