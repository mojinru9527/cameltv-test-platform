# Batch 78 — PRD Summary（开发机 Python 环境修复，C77-2）

> **Product (🟦)** | Date: 2026-08-04 | Status: Approved

mode: light
豁免理由: 内部开发环境工具 + 可复现脚本，不涉及产品行为/接口/配置/依赖变更；按 SKILL.md「批次模式」判定为轻量批次，PM/Design 工件省略，QA/Leader/看板照常。

## 1. 问题陈述

Batch 77 暴露开发机 Python 3.12 基础被卸载：`%LOCALAPPDATA%\Programs\Python\Python312` 目录完整（Lib/site-packages 中 fastapi/sqlalchemy/pytest 等依赖俱在）但 `python.exe` 缺失，导致本地 pytest 无法执行，两个后端 venv（`.venv`/`venv`）同步失效。后果：本地受影响模块测试被阻塞，只能依赖 CI 兜底（Batch 77 因此发生一次可本地避免的返工）。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量 |
|------|------|------|------|
| python.exe | 缺失 | 存在且可运行 | `python -c "import sys"` |
| 依赖导入 | 失败 | fastapi/sqlalchemy/pydantic 可导入 | `python -c "import ..."` |
| .venv | 损坏 | 可用 | `backend\.venv\Scripts\python.exe -m pytest --version` |
| 本地 pytest | 不可用 | 可执行 | 运行 `tests/test_auth.py` 冒烟 |
| 可复现性 | 无脚本 | `setup-dev-python.ps1` 幂等 | 脚本二次运行 exit 0 |

## 3. 非目标（本次不做）

- **不重装依赖**：site-packages 完好，仅原位修复解释器；除非 venv 仍坏才 `-RebuildVenv`。
- **不改系统 PATH/默认解释器**：仅 per-user 原位安装，不动全局配置。
- **不处理 C77-1 剩余 HARD**：下批再消化。

## 4. 用户故事 + 验收标准

- As 开发者, I want 一条命令修复/校验开发机 Python, so that 本地 pytest 恢复可用。
  - 验收：Given `pwsh scripts/git/setup-dev-python.ps1` / When 运行 / Then exit 0 且 python + 依赖 + pytest 可用；二次运行仍 0（幂等）。
- As QA, I want 环境修复可复现, so that 换机/重装不再靠手工。
  - 验收：Given 新机器 / When 运行脚本 / Then 自动下载安装 Python 3.12 并校验依赖。

## 5. 技术考量

- 官方安装器静默 per-user 安装：`python-3.12.10-amd64.exe /quiet InstallAllUsers=0 TargetDir=<existing dir>`，原位补回 `python.exe`，site-packages 不动。
- venv 的 pyvenv.cfg home 指向同一目录 → 基础修复后 `.venv` 自动复活；`-RebuildVenv` 兜底。
- 下载地址 `https://www.python.org/ftp/python/{ver}/python-{ver}-amd64.exe`。
