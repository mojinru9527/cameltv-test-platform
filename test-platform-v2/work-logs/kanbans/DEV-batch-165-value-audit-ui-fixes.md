# 🗂️ Dev 部门项目看板 — batch-165-value-audit-ui-fixes

> **用途**：追踪 batch-165 多切片进度。Dev 启动前先读本看板。
> 关联 PRD：[work-logs/batch-165-value-audit-ui-fixes-prd-summary.md](../batch-165-value-audit-ui-fixes-prd-summary.md)

## 📋 项目信息
| 字段 | 值 |
|------|-----|
| 项目名称 | CamelTv 测试平台（test-platform-v2） |
| 执行器 | codex（Agent Team） |
| 分支 | feature/batch-165-value-audit-ui-fixes |
| 看板创建 | 2026-08-13 |

## 🎯 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 全平台功能价值与冗余评估文档 | ✅ | ✅ | ✅ | ✅ | ⏳ | docs/platform-feature-value-and-redundancy-audit.md |
| 2 | 隐藏专项测试/性能监控（菜单+路由+命令面板+访客目录+seed） | ✅ | ✅ | ✅ | ✅ | ⏳ | 本地实测通过 |
| 3 | 知识中心 tab 修复 | ✅ | ✅ | ✅ | ✅ | ⏳ | 1280/1024 无裁切+点击切换通过 |
| 4 | 接口测试模块修复（资产分页/参数展示/用例编辑入口） | ✅ | ✅ | ✅ | ✅ | ⏳ | 20 行/页+编辑抽屉实测通过 |
| 5 | UI 自动化可见性增强（用例/脚本+运行概览） | ✅ | ✅ | ✅ | ✅ | ⏳ | 用例/脚本页签实测通过 |

## 📍 当前位置
```
Batch #165 — 全部切片完成，待用户一次总确认
├── 已完成: Slice1 评估文档 + Slice2 隐藏 + Slice3 知识tab + Slice4 接口测试 + Slice5 UI自动化
├── ✅ QA: 前端 461 用例/后端 1429 用例/typecheck/build/lint/ruff/alembic 全绿
├── ⏳ 待审批: 用户一次总确认（推送+PR+合入）
└── ⏳ 下一步: 确认后 push → Draft PR → audit-ai-pr -RequireSuccessfulChecks → 合入 main
```

## ⚠️ 阻塞与风险
| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 生产凭据过期 | P3 | production.env 登录 401，无法在线复现知识 tab；改用本地复现 | 无 | 2026-08-13 |
| 批次体量 | P2 | 5 切片含前后端改动，QA 需跑双端硬门禁 | 无 | 2026-08-13 |
