# 🗂️ Dev 部门项目看板 — Batch 172 DSH Harness 集成

## 📋 项目信息
| 字段 | 值 |
|------|-----|
| **项目名称** | DeepSeek Harness 集成 A/B/C |
| **关联 PM 计划** | [batch-172-dsh-harness-integration-pm-plan.md](../batch-172-dsh-harness-integration-pm-plan.md) |
| **关联 PRD** | [batch-172-dsh-harness-integration-prd-summary.md](../batch-172-dsh-harness-integration-prd-summary.md) |
| **总预估工时** | 16h |
| **已用批次** | 1 批 |
| **看板创建** | 2026-08-14 |
| **最后更新** | 2026-08-14 |

## 🎯 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | DSH 运行时抽象 + 配置 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ | **当前位置** |
| 2 | A: AI 用例生成 harness 模式 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 3 | B: Agent 工作台执行型 Agent | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 4 | C: DSH 任务执行模块 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 5 | 文档 + 全量回归 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |

## 📍 当前位置
```
Batch 172 — Slice 1: DSH 运行时抽象 + 配置
├── 已完成: PRD/PM/Design 工件
├── 🔄 进行中: config.py DSH_* 设置 + dsh_runner 抽象服务
├── ⏳ 待审批: —
└── ⏳ 下一步: Slice 2 A: ai_service harness 模式
```

## ⚠️ 阻塞与风险
| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| dsh Python SDK 生产依赖锁版本 | P2 | `deepseek-harness-sdk` 锁版本进 requirements；未锁前 runtime=python-sdk 不可用于生产 | PM/Dev | 2026-08-14 |
| Windows 本地 PTY | P2 | 官方 SDK 持久 PTY 仅 POSIX；本地用 node runtime 规避 | Dev | 2026-08-14 |

## 🔗 相关工件
| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | batch-172-dsh-harness-integration-prd-summary.md | ✅ |
| PM 计划 | batch-172-dsh-harness-integration-pm-plan.md | ✅ |
| 设计规范 | batch-172-dsh-harness-integration-design-spec.md | ✅ |
| QA 报告 | batch-172-dsh-harness-integration-qa-report.md | ⏳ |
| Leader 判决 | batch-172-dsh-harness-integration-leader-verdict.md | ⏳ |
