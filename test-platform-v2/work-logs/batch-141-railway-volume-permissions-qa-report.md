# Batch 141 — Railway 卷权限报错加固 QA 报告
> **QA (🔍)** | Date: 2026-08-10 | Verdict: PASS（发布建议 READY）

## 可执行门禁
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:---:|------|
| 后端未定义名引用 | `ruff check app/ --select F821` | 0 | 通过 |
| 受影响模块 Pytest | `pytest tests/test_lanhu_evidence_models.py tests/test_lanhu_evidence_auth.py tests/test_lanhu_latest_version.py tests/test_lanhu_cookie_inject.py` | 0 | 19 passed |
| 后端全量回归 | `pytest -q` | 0 | **1317 passed / 3 skipped / 0 failed** |

## 逐条件验证
| 验收标准 | 结果 | 证据 |
|----------|:---:|------|
| 报错可操作 | ✅ PASS | main.py 捕获 PermissionError，日志提示"Railway 后端服务 Variables 设置 RAILWAY_RUN_UID=0 并重新部署；或 chown -R 10001:10001 /app/storage" |
| 目录权限放宽 | ✅ PASS | mkdir 后尽力 chmod 0o755（OSError 静默，不阻断启动） |
| 文档同步 | ✅ PASS | docs/ops/railway-storage.md 增加权限报错排障小节 |
| 回归 | ✅ PASS | 后端 1317 全量无新增失败（0 failed） |

## 缺陷列表
无。

## 发布建议
状态: **READY** · 必修复: 0 · 建议修复: 0
（部署仍须按 runbook 在 Railway 后端服务 Variables 设 RAILWAY_RUN_UID=0 或 chown /app/storage；代码不替代该部署项）

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1.5h / 实际 1h | 0/0/0/0 | 0 | 外部部署 | Railway 卷权限坑先查官方 Volumes 文档（root 挂载 + RAILWAY_RUN_UID） |

**技能使用**: `cameltv-agent-team` / `cameltv-bug-guard`（部署/网络类避坑）。