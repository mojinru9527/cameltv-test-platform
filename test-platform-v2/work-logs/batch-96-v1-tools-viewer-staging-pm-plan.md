# Batch 96 — PM Plan（V1 工具审计 / viewer / staging / diff 基线）

> **PM (🟨)** | Date: 2026-08-05

## 开发任务

### Slice 1: C64-1 工具引用审计 + 批准/移除计划（0.5d）
- 审计 `test-platform/tools/` 11 工具在 V2 的引用（rg，排除 docs/work-logs）
- 产出：`docs/architecture/batch-96-v1-tools-deprecation.md`（矩阵 + 批准 + 移除计划）

### Slice 2: viewer 只读角色/账号（TDD，0.5d）
- config viewer_username/password；seed viewer 角色（_VIEWER_MENUS/_VIEWER_ACTIONS）+ 用户 + 项目成员
- `test_viewer_role.py`：查看 200 / 建用例 403 / 建缺陷 403

### Slice 3: C64-3 澄清 + staging 登记（0.25d）
- 生产环境交付清单 §3 澄清（业务 DB/Redis/MQ = 被测系统）
- `docs/agent-team/staging-environment.md`（test 环境为 staging 替代 + C27 排期）

### Slice 4: batch-18-C8 diff 标注基线（0.5d）
- `test_diff_classifier_baseline.py`：10 组标注对 + 显著差异召回/误报指标 + evidence JSON

### Slice 5: QA 门禁 + C 条件 + 交付
- pytest 全量 / ruff / scan / audit；C31-2/C31-3/batch-18-C8 关闭，C64-1（B 档）In-Progress
