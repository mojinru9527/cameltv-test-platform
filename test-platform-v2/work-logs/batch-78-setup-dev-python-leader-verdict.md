# Batch 78 — Leader Verdict（开发机 Python 环境修复，C77-2）

> **Leader (🎯)** | Date: 2026-08-04 | Decision: **APPROVED**（待用户 push 授权 + 二次确认后合入）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | mode: light，仅环境修复 + 可复现脚本；未扩范围 |
| 证据 | PASS | 脚本本机实测：python/deps/.venv/pytest 全绿；幂等 exit 0 |
| 诚实性 | PASS | 如实记录安装器"已注册即跳过"坑与 embeddable 绕行方案 |
| 风险 | 低 | per-user 原位修复，未改系统 PATH/默认解释器，未重装依赖 |

## 关键决策（已批准）

1. **原位修复而非重装**：site-packages 完好，仅补回解释器文件（python.exe/python3.dll/python312.dll/vcruntime），依赖零损失。
2. **可复现脚本**：`setup-dev-python.ps1` 覆盖"全新安装 / 已注册跳过 / 文件缺失"三态，幂等。
3. **本地 pytest 恢复强制**：C78-1 登记——后续批次本地受影响模块 pytest 必须执行并记录退出码，禁止再以环境阻塞为由跳过。

## 抽检通过

- ✅ [setup-dev-python.ps1](scripts/git/setup-dev-python.ps1) — 首次修复成功 + 复跑 exit 0
- ✅ `python -c "import fastapi, sqlalchemy, pydantic, pytest, alembic, httpx"` — exit 0
- ✅ `backend\.venv\Scripts\python.exe -m pytest tests/test_api_task_worker.py -q` — 14 passed
- ✅ `git diff --name-only` — 仅声明文件

## 判决

**APPROVED**。可进入 push → Draft PR → 首轮 checks → 用户二次确认 → 合入流程。

## 下一批次 Leader 条件

- **C78-1（P2）**：后续批次本地受影响模块 pytest 必须执行并记录退出码；开发机环境已修复，禁止再以环境阻塞为由跳过。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| Python312 目录完整但 python.exe 缺失（注册表残留 + 文件被删） | 官方安装器静默跳过 → embeddable 包原位补回解释器文件 | setup-dev-python.ps1 |
| venv pyvenv.cfg 指向修复目录 → 基础恢复后 .venv 自动复活 | 脚本校验 .venv 健康，可选 -RebuildVenv 兜底 | setup-dev-python.ps1 |
| 本地 pytest 曾因环境不可用而由 CI 兜底（Batch 77 返工诱因） | 环境恢复 + C78-1 强制本地执行 | C-CONDITIONS.md |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4h / 实际 2h | 0/0/0/2 | 2 | 工具链 | 环境类脚本先单步验证参数绑定 |

**技能使用**: `cameltv-agent-team` 轻量批次流水线；`setup-dev-python.ps1` 本批交付工具。
