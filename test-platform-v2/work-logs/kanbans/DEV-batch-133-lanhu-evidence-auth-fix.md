# 🗂️ Dev 看板 — Batch 133（蓝湖证据采集会话失效/失败状态修复）

| 字段 | 值 |
|------|-----|
| 模式 | full |
| 执行器 | codex |
| 分支 | fix/batch-133-lanhu-evidence-auth-fix |
| Worktree | F:/CamelTv-worktrees/codex-batch-133-lanhu-evidence-auth-fix |
| 前/后端端口 | 5221 / 8051 |
| 基线 | origin/main |
| PRD | `../batch-133-lanhu-evidence-auth-fix-prd-summary.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | Product / 根因定位 | ✅ | ✅ | ✅ | ✅ | ⏳ | 418=会话失效 + stage done 冒充已完成 |
| 1 | 后端 418 分类 + 会话失效重试 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ | LanhuAuthError + 刷新重试一次 |
| 2 | 后端蓝湖重新登录接口 + Cookie 安全存储 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 账号密码换 Cookie，不存明文 |
| 3 | 前端失败状态修复 + 重新登录入口 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 失败展示 error_message，不再"已完成" |
| 4 | QA / 浏览器 / Leader | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 双端门禁 + 证据 |
| 5 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 未获总确认不得 push |

## 当前结论
- 418 是蓝湖会话失效（LANHU_COOKIE 过期），需识别为会话错误并支持用户重新登录后自动重试。
- 失败任务不得以 stage=done 的"已完成"掩盖真实 status。
