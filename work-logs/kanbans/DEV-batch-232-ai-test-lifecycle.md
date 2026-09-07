# Dev 看板 - Batch 232 AI Test Lifecycle

## 项目信息

| 字段 | 值 |
|------|----|
| 项目名称 | AI 测试全链路 |
| 关联 PM 计划 | [batch-232-ai-test-lifecycle-pm-plan.md](../batch-232-ai-test-lifecycle-pm-plan.md) |
| 关联 PRD | [batch-232-ai-test-lifecycle-prd-summary.md](../batch-232-ai-test-lifecycle-prd-summary.md) |
| 总预估工时 | 12h |
| 已用批次 | 1 |
| 看板创建 | 2026-09-07 |
| 最后更新 | 2026-09-07 |

## 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | VersionTask-Mission 与场景分类模型 | 已完成 | 已完成 | 已完成 | 待开始 | 待开始 | 三类用例缺一即拒绝 AI 结果 |
| 2 | 缺陷与复验关联 | 已完成 | 已完成 | 已完成 | 待开始 | 待开始 | 缺陷关联单次执行，复验沿用 parent run |
| 3 | 生命周期聚合 API | 已完成 | 已完成 | 已完成 | 待开始 | 待开始 | 单接口聚合阶段、证据、缺陷和复验 |
| 4 | Mission 概览真实工作台 | 已完成 | 已完成 | 已完成 | 待开始 | 待开始 | 相关 Vitest 25/25，typecheck/build 通过 |
| 5 | QA、Leader、PR 与生产发布 | 已完成 | 已完成 | 打回 | 待开始 | 待开始 | Mission 9101 Gate 4/5；`B232-TEST5-001` 待复验；未推送/未发布 |
| 6 | AI 缓存复用与成本遥测 | 已完成 | 已完成 | 已完成 | 待开始 | 待开始 | 同操作重复请求去重；OpenAI/DeepSeek usage 落库；调试抽屉显示真实命中率 |

## 当前位置

```text
Batch 232 - AI Test Lifecycle
├── 已完成: Slice 1-4 编码与相关自测
├── 已完成: 平台全量质量门禁、16 页/视口浏览器验收和真实证据链展示
├── 已打回: Mission 9101 UI 自动化业务失败，Gate 4/5
├── 已完成: 缓存公共前缀、请求去重、供应商 usage 落库与调试展示
├── 未开始: push、Draft PR、required checks、main 合入和生产发布
└── 下一步: 完成本批门禁与 PR；Mission 9101 仍须修复 B232-TEST5-001 后复验
```

## 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 生产真实任务重建 | P1 | 必须在本批发布后，使用真实环境和需求文档执行 | QA/业务测试 | 2026-09-07 |
| Test5 UI 资源错误 | P1 | Google GSI 403、图片代理 503/504、NBA CDN HTTP2 错误导致 UI 用例失败 | 体育前端/基础设施 | 2026-09-07 |

## 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | `work-logs/batch-232-ai-test-lifecycle-prd-summary.md` | 已完成 |
| PM 计划 | `work-logs/batch-232-ai-test-lifecycle-pm-plan.md` | 已完成 |
| 设计规范 | `work-logs/batch-232-ai-test-lifecycle-design-spec.md` | 已完成 |
| 实现计划 | `docs/superpowers/plans/2026-09-07-ai-test-lifecycle.md` | 已完成 |
| QA 报告 | `work-logs/batch-232-ai-test-lifecycle-qa-report.md` | NEEDS WORK |
| Leader 判决 | `work-logs/batch-232-ai-test-lifecycle-leader-verdict.md` | 打回 |
