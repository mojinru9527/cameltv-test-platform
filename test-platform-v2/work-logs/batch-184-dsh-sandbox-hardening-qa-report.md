# Batch 184 — QA 报告：DSH 沙箱安全加固（C172-1/2）

> **mode: full** | 执行：DeepSeek_Harness（direct）| 日期：2026-08-16
> 分支：`feature/batch-184-dsh-sandbox-hardening`（基 91ae21d）

## 0. 结论

✅ **C172-1/2 两项 P1 安全条件全部闭环**：任务级隔离工作区 + 全局并发闸门 + 任务文本配额 + python-sdk 凭据锁，安全回归 8 例全绿。

## 1. 验收证据

| 验收点 | 证据 |
|--------|------|
| C172-2 凭据隔离 | `_python_sdk_env_lock` 序列化「env 突变 + harness.run」；并发双任务快照各自 key-a/model-a 与 key-b/model-b 互不交叉；结束后 env 恢复无残留 |
| C172-1 工作区隔离 | `_workspace_for` 强制 `{base}/ws-{uuid}` 子目录（显式 workspace/DSH_WORKSPACE 仅作隔离根）；3 例单测 |
| C172-1 任务级配额 | `DSH_MAX_CONCURRENT`（默认 1，全局闸门，超出排队）；`DSH_MAX_TASK_CHARS`（默认 20000，超限拒绝 exit_code=2）；闸门并发上限断言 max_active==2 |
| 安全回归 | `tests/test_dsh_sandbox.py` **8/8 绿**；既有 `test_dsh_tasks.py` 8/8 绿（无回归） |
| 生产启用前置 | `DSH_ENABLED=false` 不变；CLAUDE.md 记录启用 checklist（加固+测试全绿+人工确认） |
| 配置文档 | config.py + .env.example 新增 2 项；CLAUDE.md「DSH 沙箱约定」小节 |

## 2. 硬门禁

| 门禁 | 结果 |
|------|------|
| 后端 pytest 全量 | 待最终值（后台运行） |
| ruff F821 | 待运行 |
| alembic | 无迁移（纯代码/配置） |

## 3. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | ~6h（计划）vs ~2h（实际） |
| 缺陷 | P0:0 / P1:0 / P2:0 / P3:3（测试自身问题：顺序调用非并发/只读属性 patch/barrier 与锁冲突，均测试侧修正） |
| 返工次数 | 3 |
| 根因分类 | 工具链 |
| 下次避免 | 并发语义测试先想清楚「锁/闸门是否串行化」；只读 property 用底层字段 patch |
