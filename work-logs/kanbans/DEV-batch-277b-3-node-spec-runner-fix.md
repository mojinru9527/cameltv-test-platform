# 🗂️ 看板：Batch 277b-3 — 节点 spec 执行器修复

| 项 | 值 |
|----|-----|
| 批次 | batch-277b-3（light fix） |
| 分支 | fix/batch-277b-3-node-spec-runner-fix |
| 基线 | origin/main `e7d744952` |

## 进度

| # | 项 | 状态 |
|---|----|:----:|
| 1 | `_playwright_root` 指向 backend/tests/playwright | ✅ |
| 2 | spec 命名保留 `.spec.ts` | ✅ |
| 3 | 子进程 UTF-8 解码 | ✅ |
| 4 | `--project/--reporter` | ✅ |
| 5 | 真实 Chromium 冒烟 1/1 | ✅ |
| 6 | 本地 `/uitest` 全链路 done | ✅ |
| 7 | 单元测试隔离 + 12/12 | ✅ |
| 8 | PR / checks / merge | 🔄 |

## 下一步

- 浏览器依赖（lanhu/xhr/playground）决策；
- 本地无 Chromium 镜像构建；
- 生产窗口（104 表 DROP 已获同意）。
