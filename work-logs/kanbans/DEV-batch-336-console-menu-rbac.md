# 🗂️ 看板：Batch 336（执行中心菜单 + RBAC）

| 字段 | 值 |
|------|-----|
| 批次 | batch-336（full） |
| 分支 | feature/batch-336-console-menu-rbac |
| 基线 | origin/main `03f778798` |
| 范围 | Console 菜单 + `menu:aiqe_runs` 权限 + 路由守卫 |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | 后端 seed 菜单 + tester 分配 | ✅ |
| 2 | 后端 AIQE API 统一门禁 | ✅ |
| 3 | 前端导航 + 命令面板 | ✅ |
| 4 | 前端路由守卫 + 403 页 | ✅ |
| 5 | 后端测试 6 条 / 前端测试 4 条 | ✅ |
| 6 | 全量回归（后端/前端） | 🔄 |
| 7 | PR / required checks / 合入 | 🔄 |

## 下一步

batch-337：Profile / Workflow 审批页面。
