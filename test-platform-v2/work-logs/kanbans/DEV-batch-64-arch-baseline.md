# Dev Kanban — Batch 64 Architecture Baseline

## 项目信息

| 字段 | 值 |
|------|-----|
| 分支 | feature/batch-64-arch-baseline |
| Base | origin/main at a97b430 |
| Worktree | F:/CamelTv-worktrees/codex-batch-64-arch-baseline |
| Workflow / executor | agent-team / codex |
| Ports | frontend 5192; backend 8124 |
| 创建 | 2026-08-02 |

## 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 六部门工件（PRD/PM/Design/看板） | ✅ | ✅ | ✅ | ✅ | ⏳ | 需求与范围锁定 |
| 2 | 架构解析报告 + ADR-0016 + 文档同步 | ✅ | ✅ | ✅ | ✅ | ⏳ | 资深架构师视角 |
| 3 | 生产交付清单 | ✅ | ✅ | ✅ | ✅ | ⏳ | 无明文 Secret |
| 4 | 仓库边界事实源 + 校验器 | ✅ | ✅ | ✅ | ✅ | ⏳ | TDD：先写 selftest |
| 5 | QA 全量门禁 + 判决 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | 零业务代码回归 |

## 当前位置

```
Batch 64 — 架构解析与仓库拆分基线
├── 已完成: PRD/PM/Design；架构解析报告；ADR-0016；生产交付清单；边界清单+校验器
├── 🔄 进行中: QA 硬门禁与 Leader 判决
├── ⏳ 待审批: 用户 push 授权 → Draft PR → 首轮 checks → 二次执行器确认
└── ⏳ 下一步: Batch 65 起按 C64 条件排期（API-only UI / V1 工具迁移 / 拆仓）
```

## 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 生产发布 | P0 | 生产基础设施未就绪，交付清单只整理不发布 | DevOps owner | 2026-08-02 |
| 真实内网地址 | P1 | DB/Redis/MQ 地址仍为 10.x.x.x 占位 | 运维 | 2026-08-02 |
| V1 工具迁移 | P1 | mock/capture/apidiff/datafactory/logagg 无 V2 等价物，V1 不可整体移除 | 后续批次 | 2026-08-02 |

## 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | test-platform-v2/work-logs/batch-64-arch-baseline-prd-summary.md | ✅ |
| PM 计划 | test-platform-v2/work-logs/batch-64-arch-baseline-pm-plan.md | ✅ |
| 设计规范 | test-platform-v2/work-logs/batch-64-arch-baseline-design-spec.md | ✅ |
| 架构解析报告 | docs/architecture/batch-64-architecture-analysis.md | ✅ |
| ADR-0016 | docs/adr/0016-three-repository-separation.md | ✅ |
| 生产交付清单 | docs/production-delivery/生产环境交付清单.md | ✅ |
| 边界清单 | repo-boundaries.json + scripts/repo-split/ | ✅ |
| QA 报告 | test-platform-v2/work-logs/batch-64-arch-baseline-qa-report.md | ✅ |
