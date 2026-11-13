# 🗂️ 看板：Batch 342（Workflow 写 API + 审批权限）

| 字段 | 值 |
|------|-----|
| 批次 | batch-342（full） |
| 分支 | feature/batch-342-workflow-write |
| 基线 | origin/main `80b28a01d` |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | POST/PATCH workflows + 校验 | ✅ |
| 2 | 新权限 `aiqe:workflow:approve`（seed） | ✅ |
| 3 | 审批端点改用独立权限 | ✅ |
| 4 | 路由基线 +2 | ✅ |
| 5 | 后端测试 7 条 + 337 回归 | ✅ 15 passed |
| 6 | 全量 / PR / checks / 合入 | 🔄 |
| 7 | Test 部署 + 审批权限实测 | ⏳ |

## 下一步

- 合入后部署 Test，验证：创建→编辑→审批（管理员）→二次编辑 409；
- batch-343：TC-004 业务 Web 反爬处置（唯一剩余阻塞）。
