# Batch 117 — PRD（AI 生成前端轮询闭环 + 覆盖缺口报告）

> **Product (🟦)** | Date: 2026-08-07 | Status: Review

```markdown
mode: full
豁免理由: 无（含前端交互改造 + 后端报告能力，走完整六部门流水线）。
非目标: 外部依赖项（iOS/Test5/runner）与 C104-3/C99-1 等继续跟踪。
```

## 1. 问题陈述

1. **C116-2**：C102-1 后端异步端点已交付，前端仍直连同步端点（大文档 502 未对用户缓解）。
2. **C116-3**：C103-6 覆盖缺口报告缺失（截断 retry 已有）。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| C116-2 | 前端直连同步生成 | 前端改调 async 端点 + 轮询（2s），大文档不 502，结果落库 |
| C116-3 | 无缺口报告 | 生成结果附 coverage_report（功能点×用例覆盖矩阵，缺口列清单），单测 |

## 3. 用户故事 + 验收标准

- As a **需求承接人**, I want 前端生成不再因大文档超时失败。
  - Given 大文档，When 点生成，Then 走 async+轮询，完成展示结果。
- As a **QA**, I want 覆盖缺口报告，so that 遗漏可见。
  - Given 生成结果，Then coverage_report 含功能点/模块覆盖矩阵与缺口。

## 4. 技术考量

- 前端：api/requirement.ts 增 async 端点封装 + `fetchAiTask` 轮询 helper；index.tsx/ReviewPage.tsx 生成/提取改走 async+poll。
- 后端：`coverage_report.py`（功能点×用例矩阵）；generate-async _job 结果附 coverage_report。
- 技能：`cameltv-bug-guard`（前端副作用/异步清理）、`test-case-design`。

## 5. 范围

**纳入**：前端 async 轮询（提取/生成）、后端覆盖缺口报告 + 单测、证据。

## 6. 上线计划

| 阶段 | 内容 | 出口标准 |
|------|------|---------|
| S1 | 工件 + 覆盖缺口报告（后端+单测） | 单测 |
| S2 | 前端 async 轮询（api + index/ReviewPage） | typecheck/build + vitest |
| S3 | QA/Leader + 一次总确认 | 审计 0 硬错 |