# Dev Kanban — Batch 63 Legacy Issue Closure

## 项目信息

| 字段 | 值 |
|------|-----|
| 分支 | feature/batch-63-legacy-issue-closure |
| Base | origin/main at 9c6263f |
| Worktree | F:/CamelTv-worktrees/codex-batch-63-legacy-issue-closure |
| Workflow / executor | agent-team / codex |
| Ports | frontend 5200; backend 8030 |
| 创建 | 2026-08-02 |

## 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 供应链安全（ecdsa 替换） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | B61-P1-001 |
| 2 | 项目隔离全模块复测 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | B60-P0-003 |
| 3 | 生产保护统一 + 五入口 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | B60-P0-004/P1-019 |
| 4 | 导航/权限/PRD 对账 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | B60-P1-002/009/010 |
| 5 | 前端闭环 + UX 遗留 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | B60-P1-006/008/P2-001/002/006 |
| 6 | 验收资产 + C 条件对账 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | B60-P1-017 + C-CONDITIONS |
| 7 | QA 全量回归 + 判决 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 门禁 + 报告 + Leader |

## 当前位置

```
Batch 63 — 遗留问题汇总解决
├── 已完成: worktree 创建与验证；回归汇总（57–62）；PRD/PM/Design 工件
├── 🔄 进行中: Slice 1 供应链安全（python-jose → PyJWT）
├── ⏳ 待审批: 切片代码与测试
└── ⏳ 下一步: Slice 2 项目隔离全模块复测
```

## 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| Test5/VPN/六契约 | P0 | R2 真实执行无授权 | 用户/Test5 owner | 2026-08-02 |
| AI/OCR/蓝湖凭据 | P0 | 真实 AI 链路无凭据 | 用户 | 2026-08-02 |
| 旧 PG 快照 | P0 | A10 迁移无法执行 | DBA owner | 2026-08-02 |
| 真机性能 | P1 | 无设备 | 用户 | 2026-08-02 |
| 云注册 C58 | P1 | 外部注册未完成 | 用户 | 2026-08-02 |
| DevOps 基础设施 | P0 | test release 无法真实执行 | DevOps owner | 2026-08-02 |

## 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| 回归汇总 | test-platform-v2/work-logs/batch-63-regression-57-62-summary.md | ✅ |
| PRD | test-platform-v2/work-logs/batch-63-legacy-issue-closure-prd-summary.md | ✅ |
| PM 计划 | test-platform-v2/work-logs/batch-63-legacy-issue-closure-pm-plan.md | ✅ |
| 设计规范 | test-platform-v2/work-logs/batch-63-legacy-issue-closure-design-spec.md | ✅ |
