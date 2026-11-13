# 🗂️ 看板：Batch 341（缺陷修复回归 API）

| 字段 | 值 |
|------|-----|
| 批次 | batch-341（full） |
| 分支 | feature/batch-341-regression-api |
| 基线 | origin/main `7fb0af008` |

| # | 项 | 状态 |
|---|----|:----:|
| 1 | regression_service（create/get/list） | ✅ |
| 2 | 3 个 API + 路由注册 | ✅ |
| 3 | 路由基线同步 | ✅ |
| 4 | 后端测试 7 条 | ✅ |
| 5 | 全量回归 / PR / checks / 合入 | 🔄 |
| 6 | Test 实例验证（TC-008 实跑） | ⏳ batch-343 |

## 下一步

- 合入后与 batch-340 一起部署 Test，跑 TC-AIQE-008（缺陷→回归→新 Run→旧 Run 保留）；
- batch-342：Workflow 写 API + 独立审批权限点。
