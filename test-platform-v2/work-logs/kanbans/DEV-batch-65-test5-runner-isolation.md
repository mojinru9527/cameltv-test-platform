# Dev Kanban — Batch 65 Test5 Runner Isolation

## 项目信息

| 字段 | 值 |
|------|-----|
| 分支 | feature/batch-65-test5-runner-isolation |
| Base | origin/main at c090aa9 |
| Worktree | F:/CamelTv-worktrees/codex-batch-65-test5-runner-isolation |
| Workflow / executor | agent-team / codex |
| Ports | frontend 5201; backend 8031 |
| 创建 | 2026-08-02 |

## 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 六部门工件（PRD/PM/Design/看板） | ✅ | ✅ | ✅ | ✅ | ⏳ | 需求与范围锁定 |
| 2 | Test5 执行器隔离方案 + ADR-0017 + README | ✅ | ✅ | ✅ | ✅ | ⏳ | 方案批次 |
| 3 | 外部前置条件清单 | ✅ | ✅ | ✅ | ✅ | ⏳ | 7 类 12+ 项 |
| 4 | QA 门禁 + Leader 判决 + C 条件 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | 零业务代码回归 |

## 当前位置

```
Batch 65 — Test5 验收执行器隔离 + 外部前置条件清单
├── 已完成: 方案文档；ADR-0017；前置条件清单；六部门工件
├── 🔄 进行中: QA 硬门禁与 Leader 判决
├── ⏳ 待审批: 用户 push 授权 → Draft PR → 首轮 checks → 二次确认
└── ⏳ 下一步: batch-66 执行器搭建与 V1-V5 实测；按清单解锁外部条件
```

## 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| Test5 授权窗口 | P0 | 执行器实测需 Test5 授权窗口与内网信息 | 用户/Test5 owner | 2026-08-02 |
| WSL2 tun 支持 | P1 | `/dev/net/tun` 未验证，方案含 mknod 与容器/VM 回退 | batch-66 实测 | 2026-08-02 |
| AI/OCR/蓝湖凭据 | P0 | 验收前置条件清单登记中 | 用户 | 2026-08-02 |

## 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | test-platform-v2/work-logs/batch-65-test5-runner-isolation-prd-summary.md | ✅ |
| PM 计划 | test-platform-v2/work-logs/batch-65-test5-runner-isolation-pm-plan.md | ✅ |
| 设计规范 | test-platform-v2/work-logs/batch-65-test5-runner-isolation-design-spec.md | ✅ |
| 执行器方案 | test-platform-v2/docs/operations/test5-runner-isolation.md | ✅ |
| ADR-0017 | docs/adr/0017-test5-runner-network-isolation.md | ✅ |
| 前置条件清单 | docs/production-delivery/外部前置条件清单.md | ✅ |
| QA 报告 | test-platform-v2/work-logs/batch-65-test5-runner-isolation-qa-report.md | ✅ |
