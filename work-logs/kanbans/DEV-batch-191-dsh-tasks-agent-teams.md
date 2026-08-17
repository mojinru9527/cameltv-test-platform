# DEV-batch-191-dsh-tasks-agent-teams 看板

> 项目：/dsh-tasks 支持 AgentTeams 团队模式（B1 方案） | 批次模式：full
> 执行器：DeepSeek_Harness（agent-team workflow）| worktree：`F:\CamelTv-worktrees\DeepSeek_Harness-batch-191-dsh-tasks-agent-teams`

## 当前位置

📍 Batch 191 → Dev 实现（T1–T7 完成，T8 前端 + T9 vitest 完成，T10 文档完成，T11 冒烟进行中，T12 门禁收尾）

## 交付切片进度

| # | Slice（PM 任务） | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|------------------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | T1 配置（dsh_team_* 5 项 + .env.example） | ✅ | ✅ | ✅ | ⏳ | ⏳ | db13ee6 |
| 2 | T2 模型 + Alembic 20260817_b191_dsh_team_mode | ✅ | ✅ | ✅ | ⏳ | ⏳ | db13ee6；SQLite/PG 双兼容 + 幂等守卫（create_all 已建列场景） |
| 3 | T3 Schema + API（mode/batch_mode 校验、team_json 出参） | ✅ | ✅ | ✅ | ⏳ | ⏳ | f190f14（T3/T4/T5 合并提交） |
| 4 | T4 dsh_runner 团队路由（node profile / sdk cordis / 1800s 超时 / workspace 字段） | ✅ | ✅ | ✅ | ⏳ | ⏳ | f190f14 + 242f31a 修正（single 留空） |
| 5 | T5 persona + team.cordis.yml + agent-team profile 模板 | ✅ | ✅ | ✅ | ⏳ | ⏳ | f190f14 |
| 6 | T6 service 团队分支 + 轮询线程（独立 SessionLocal） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 89d1c09 |
| 7 | T7/T9 后端测试扩展（schema/service/runner/sandbox/persona） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 56 用例全绿 |
| 8 | T8/T9 前端（模式选择/批次下拉/类型徽标/进度树/轮询/vitest） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 含 team-progress.tsx |
| 9 | T10 文档（ADR-0018/README/backend CLAUDE.md/C-CONDITIONS） | ✅ | ✅ | 🔄 ⬅️ | ⏳ | ⏳ | C191-1/C191-2 建议登记 |
| 10 | T11 真实冒烟（node mini 团队 / python-sdk 判定） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 环境限制如实记录 |
| 11 | T12 门禁（ruff/pytest/typecheck/build/vitest/Alembic 单头）+ 看板 | 🔄 | 🔄 | 🔄 | ⏳ | ⏳ | **当前位置** |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

## 验收记录

- [x] Alembic：upgrade head / downgrade -1 / 全新库全链路 / heads 单头全部通过（SQLite）
- [x] 后端 DSH 专项 56 用例全绿（test_dsh_tasks / test_dsh_runner / test_dsh_sandbox / test_agent_team_persona）
- [x] team.cordis.yml = minimal 12 行 + agent-teams 插件行（YAML 解析验证）
- [x] 设计 §8.2 P0-1 反向回填：team_json before validator 兜底损坏 JSON（app/schemas/dsh.py）
- [x] C172-1 不回归：团队任务走 ws-{uuid} 隔离/并发闸门/文本配额（test_dsh_sandbox 新增 3 用例）
- [x] baseline 漂移还原：diff-classifier-baseline.json 未提交（非本批范围）
- [ ] 全量 pytest（记录基线 vs 本分支失败集合、退出码）
- [ ] 前端 typecheck / build / vitest（npm ci 后）
- [ ] T11 冒烟证据 / C191-1 判定
- [ ] 用户一次总确认（推送+PR+合入）

## 批次记录

- 产出：T1–T10 代码+测试+文档；提交 db13ee6 / 8e2d4d0 / 89d1c09 / T7-T9 提交（见 git log）
- 审批：待 QA/Leader 走查
- 耗时：进行中

## 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| python-sdk bundle 加载未实测（R-2） | P2 | SDK bundled runtime 能否加载 npm bundle 插件未知 → C191-1 deferred 路径（node 先交付） | QA/Leader | 2026-08-17 |
| running 团队任务取消延后 | P3 | C191-2 登记，下批实现执行中终止 | Leader | 2026-08-17 |
| 前端依赖安装 | P3 | worktree 无 node_modules，npm ci 进行中（pnpm-lock 缺失，用 npm ci） | Dev | 2026-08-17 |

## 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [batch-191-dsh-tasks-agent-teams-prd-summary.md](../batch-191-dsh-tasks-agent-teams-prd-summary.md) | ✅ |
| PM 计划 | [batch-191-dsh-tasks-agent-teams-pm-plan.md](../batch-191-dsh-tasks-agent-teams-pm-plan.md) | ✅ |
| 设计规范 | [batch-191-dsh-tasks-agent-teams-design-spec.md](../batch-191-dsh-tasks-agent-teams-design-spec.md) | ✅ |
| 设计文档 | [2026-08-17-dsh-tasks-agent-teams-design.md](../../docs/superpowers/plans/2026-08-17-dsh-tasks-agent-teams-design.md) | ✅ |
| QA 报告 | [batch-191-dsh-tasks-agent-teams-qa-report.md](../batch-191-dsh-tasks-agent-teams-qa-report.md) | ⏳ |

## ���μ�¼����β��
- Leader �о���APPROVED������������ C191-1/C191-2 ȷ�ϵǼǡ�R-1 ð����ά����
- QA ���飺PASS��02253b9 �ջ���488/488 vitest��
- �����Ź�����PRD/PM/Design/QA/Leader + ���壨12 �ύ��
