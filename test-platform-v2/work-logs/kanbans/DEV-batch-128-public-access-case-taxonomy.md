# 🗂️ Dev 看板 — Batch 128（公开访问、普通注册与用例分类体系）

| 字段 | 值 |
|------|-----|
| 项目 | 公开访问、普通注册与用例分类体系 |
| 模式 | full |
| 执行器 | codex |
| 分支 | feature/batch-128-public-access-case-taxonomy |
| Worktree | F:/CamelTv-worktrees/codex-batch-128-public-access-case-taxonomy |
| 前/后端端口 | 5191 / 8021 |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | Product / PM / Design / 实现计划 | ✅ | ✅ | ✅ | ✅ | ⏳ | C122-4/C104-5 纳入 |
| 1 | 公开访问契约 + 普通注册策略 | ✅ | ✅ | ✅ | ✅ | ⏳ | 无匿名业务数据 |
| 2 | 游客平台壳 + 登录 Dialog | ✅ | ✅ | ✅ | ✅ | ⏳ | 不挂载 Outlet |
| 3 | 用例 taxonomy + 类型页签 | ✅ | ✅ | ✅ | ✅ | ⏳ | 新静态 endpoint |
| 4 | 脑图端别/模块路径分层 | ✅ | ✅ | ✅ | ✅ | ⏳ | 默认 manual |
| 5 | QA / 浏览器 / 审计 / Leader | ✅ | ✅ | ✅ | ✅ | ⏳ | 1238/397 + 三视口全绿 |
| 6 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 一次总确认 |

## 📍 当前位置

```text
Batch 128
├─ ✅ Slice 0：工件与计划自检
├─ ✅ Slice 1：后端公开访问/注册
├─ ✅ Slice 2：前端游客壳/登录
├─ ✅ Slice 3：用例分类
├─ ✅ Slice 4：脑图
├─ ✅ Slice 5：QA / 浏览器 / Leader
└─ ⏳ Slice 6：用户总确认 → Draft PR → checks → merge
```

## 决策记录

- “默认只有功能用例”按问题语义处理为：默认筛选功能，但显式补齐接口/UI/全部入口。
- 游客只能看能力目录；任何业务页面、项目数据和操作都必须登录。
- 普通注册默认不要求平台邀请码；项目邀请 token 与显式邀请码策略继续兼容。
