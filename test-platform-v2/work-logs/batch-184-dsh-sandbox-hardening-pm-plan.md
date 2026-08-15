# Batch 184 — PM 计划：DSH 沙箱安全加固（C172-1/2）

> 配套 PRD：`batch-184-dsh-sandbox-hardening-prd-summary.md`

## 任务清单

| # | 任务 | 验收标准 | 执行 |
|---|------|---------|------|
| T0 | 工件 PRD/PM/Design/看板 | 四件落库、mode:full | 主代理 ✅ |
| T1 | config 新增 `dsh_max_concurrent` / `dsh_max_task_chars` | 配置可读、.env.example 同步 | 主代理 ✅ |
| T2 | dsh_runner 加固：并发闸门 + 长度配额 + 强制隔离工作区 + python-sdk 凭据锁 | test_dsh_sandbox 8 例绿 | 主代理 ✅ |
| T3 | 安全回归测试（工作区隔离/配额/闸门/凭据隔离/超时回归） | 8/8 绿；既有 test_dsh_tasks 8 绿 | 主代理 ✅ |
| T4 | 文档：CLAUDE.md 沙箱约定 + 生产启用前置 | 文档落库 | 主代理 ✅ |
| T5 | 全量回归 + 门禁 | pytest 无新增失败；ruff F821；alembic 单头 | 主代理 |
| T6 | QA/Leader 工件 + C172-1/2 关闭 + C184-1 登记 | 工件齐全；audit 通过 | 主代理 |
| T7 | 总确认 → push → Draft PR → audit → 合入 | required checks 全绿 | 主代理 |

## 风险提示

- python-sdk 锁序列化：默认 DSH_MAX_CONCURRENT=1 已安全；node 路径并发不受锁影响。
- 工作区语义变化：DSH_WORKSPACE 由「共享工作区」变为「隔离根」——向下兼容（原目录仍是根），任务数据不再互见（预期安全收益）。
