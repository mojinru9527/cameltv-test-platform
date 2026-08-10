# 🗂️ Dev 看板 — Batch 134（lanhu 自动登录 + 安全清理）

| 字段 | 值 |
|------|-----|
| 模式 | full |
| 执行器 | codex |
| 分支 | fix/batch-134-lanhu-autologin-secure |
| Worktree | F:/CamelTv-worktrees/codex-batch-134-lanhu-autologin-secure |
| 前/后端端口 | 5223 / 8053 |
| 基线 | origin/main |
| PRD | `../batch-134-lanhu-autologin-secure-prd-summary.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | Product / 根因定位 | ✅ | ✅ | ✅ | ✅ | ⏳ | runtime.login 缺失 → 自动登录不可用 |
| 1 | lanhu-mcp lanhu_login + _save_cached_cookie | ✅ | ✅ | ✅ | ⏳ | ⏳ | Playwright SSO，失败返回空串 |
| 2 | 子模块指针更新 + 推送 | ✅ | ✅ | ✅ | ⏳ | ⏳ | c9f4a43 → 3cfd2ef，main/分支已推送 |
| 3 | 后端钩子测试 + extract_doc 明文清理 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ | 导入优先/源码回退 |
| 4 | C-CONDITIONS（关 C133-1，加 C134-1） | ✅ | ✅ | ⏳ | ⏳ | ⏳ | 已更新 |
| 5 | QA / Leader | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 后端门禁 + 钩子证据 |
| 6 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 未获总确认不得 push |

## 当前结论
- lanhu-mcp 已提供 lanhu_login/_save_cached_cookie 并推送；父仓库指针待随批更新。
- 自动登录尽力而为，失败回退粘贴 Cookie。
