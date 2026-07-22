---
title: "Batch 32 本地未提交内容核对"
owner: "dev"
last_reviewed: "2026-07-22"
status: "verified"
tags: ["git", "backup", "worktree", "reconciliation"]
---

# Batch 32 本地未提交内容核对

## 1. 保护范围

- 运行中/脏工作区：`F:\CamelTv`
- 隔离交付工作区：`F:\CamelTv-batch31-audit`
- 独立嵌套仓库：`F:\CamelTv\lanhu-mcp`
- 已验证备份：`F:\CamelTv-safe-backup\20260722-201657`
- 备份验证：父仓库与蓝湖仓库 Git bundle 完整；ZIP 分别包含 9 / 1154 个文件；制品哈希与源文件哈希差异均为 0。

## 2. 父仓库逐文件结论

| 本地路径 | 与 PR #56 对比 | 处理结论 |
|---|---|---|
| `frontend/package-lock.json` | 忽略行尾后完全一致 | PR #56 已覆盖，不重复合入 |
| `frontend/package.json` | 本地缺少显式 `vite.config.ts` 参数 | 保留 PR #56 版本；避免旧生成配置抢占构建 |
| `frontend/src/lib/icons.ts` | 本地缺少 `Focus`、`Move` 导出 | 保留 PR #56 版本；本地版本被审计修复取代 |
| `EvidenceTaskPanel.tsx` | 忽略行尾后完全一致 | PR #56 已覆盖，不重复合入 |
| `VersionCompare.tsx` | 仅回调变量名不同 | 保留 PR #56 的可读性修订 |
| `ui/scroll-area.tsx` | 仅导入空行、尾逗号格式差异 | 保留 PR #56 格式 |
| `ui/toggle-group.tsx` | 仅导入顺序、尾逗号格式差异 | 保留 PR #56 格式 |
| `ui/toggle.tsx` | 仅等价格式差异 | 保留 PR #56 格式 |
| `backend/test_all_apis.py` | 本地临时脚本，含硬编码测试密码并会对全部 POST/PUT/PATCH/DELETE 发请求 | 仅保存在外部备份；禁止合入和执行 |

结论：父仓库脏文件中没有一项需要覆盖 PR #56 的唯一生产逻辑。所有内容均已进入可恢复备份，因此迁移过程无需修改、清理或切换 `F:\CamelTv`。

## 3. `lanhu-mcp` 结论

`lanhu-mcp` 是独立 Git 仓库，父仓库只记录 gitlink，且当前没有 `.gitmodules` 映射。后端 `lanhu_provider.py` 会直接从该目录导入 `lanhu_mcp_server`，知识中心的蓝湖需求提取、Wiki 导入和降级预览也依赖它，因此不能删除。

其 README、服务脚本、提取脚本、浏览器状态和截图均保持原状，只进入独立 bundle/ZIP；迁移提交仅补充 `.gitmodules`，使全新 clone 能按父仓库固定的 `c9f4a43124c1e10c442a487c54c456b1ad32d65e` 初始化依赖。该提交在上游仍可读取，当前本地脏内容不会被更新或覆盖。

## 4. 安全约束

- 不在 `F:\CamelTv` 执行 checkout、reset、clean、stash、commit 或 add。
- 不停止或重启从该目录运行的服务。
- 所有迁移代码只在 `F:\CamelTv-batch31-audit` 修改并通过 PR 合入。
- 最终用备份中的 `source-fingerprint.csv` 复核源文件 SHA-256。
