# Batch 78 — QA 报告（开发机 Python 环境修复，C77-2）

> **QA (🔍)** | Date: 2026-08-04 | Verdict: **PASS**

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|-------|------|------|------|
| 9 | 9 | 0 | 0 |

## 可执行门禁（命令、退出码与日志摘要）

**CI 分类**：变更域 = `scripts/git/` + `test-platform-v2/work-logs/` + `C-CONDITIONS.md` → 文档/工具域，前后端重测试跳过；本批交付物为 PowerShell 脚本，以实际执行为验证。

| 检查项 | 命令 | 退出码 | 结果 |
|--------|------|:------:|------|
| 脚本语法 | `[Parser]::ParseFile(setup-dev-python.ps1)` | 0 | ✅ |
| 本机修复执行 | `pwsh setup-dev-python.ps1 -BackendPath <backend>`（首次） | 1→修复 | ✅ 已恢复 python.exe + python3.dll + vcruntime |
| 幂等复跑 | 同上（第二次） | 0 | ✅ "OK: python.exe + 依赖已可用" |
| 依赖导入 | `python -c "import fastapi, sqlalchemy, pydantic, pytest, alembic, httpx"` | 0 | ✅ |
| pip | `python -m pip --version` | 0 | ✅ pip 25.0.1 |
| .venv 复活 | `backend\.venv\Scripts\python.exe -c "import fastapi; import bcrypt"` | 0 | ✅ |
| pytest 冒烟 | `.venv python -m pytest tests/test_api_task_worker.py -q` | 0 | ✅ 14 passed |
| C 条件门禁 | `audit-cconditions.ps1 -RequireLatestBatch` | 0 | ✅ 见 Leader |

## 逐条件验证（PRD-lite 成功指标）

### M1: python.exe 恢复
✅ 官方安装器因"产品已注册"静默跳过（已知坑），改从官方 embeddable 包原位补回 `python.exe`/`pythonw.exe`/`python312.dll`/`python3.dll`/`vcruntime140*.dll`；`python -c` 运行正常。

### M2: 依赖导入
✅ fastapi/sqlalchemy/pydantic/pytest/alembic/httpx/bcrypt 全部可导入（site-packages 原本完好，仅缺解释器文件）。

### M3: .venv 复活
✅ 后端 `.venv` 的 pyvenv.cfg 指向本目录，基础修复后自动可用；bcrypt C 扩展（依赖 python3.dll）通过。

### M4: 本地 pytest
✅ `tests/test_api_task_worker.py` 14 passed in 4.54s —— 本地测试能力恢复。

### M5: 可复现性
✅ `setup-dev-python.ps1` 二次运行 exit 0（幂等）。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| D1 | P3 | 脚本健康检查函数参数名不匹配（$Py vs -Path），首次自测返回假 | 脚本内修复 | Closed |
| D2 | P3 | 官方安装器对"已注册但文件缺失"的产品静默跳过 | 已绕过并写入脚本注释（embeddable 修复路径） | Closed |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4h / 实际 2h | 0/0/0/2 | 2 | 工具链 | 环境类脚本先单步验证参数绑定；安装器坑预写在脚本内 |

**技能使用**: `cameltv-agent-team`（轻量批次）；`setup-dev-python.ps1`（本批交付工具，本机实测）。

## 发布建议

状态: **READY**   必修复: 0   建议修复: 0
