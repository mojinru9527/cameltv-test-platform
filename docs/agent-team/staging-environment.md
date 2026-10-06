# staging 环境登记（C27-* / 迁移演练）

> 2026-08-23：生产已迁移腾讯云（swiftbugs.cn）。旧 Vercel/Railway 即将下线，
> staging 替代为**本地全栈 + 生产只读验证**，不再映射到海外环境。
>
> **staging 未单独启用**：仓库不维护独立 staging 实例，预发布验证由 test / 生产同构实例 + 本地全栈承担（与根 `CLAUDE.md` 环境速览、`docs/agent-team/release-cadence.md` §3 一致）。
> 本文标题中的 "staging" 指**上述替代方案**，不是一台独立环境。

## 1. 环境映射（2026-08-23 更新）

| 用途 | 地址 | 说明 |
|------|------|------|
| 前端（staging 替代） | https://swiftbugs.cn | 腾讯云生产（迁移后；旧 Vercel 已下） |
| 后端 API（staging 替代） | https://swiftbugs.cn/api | 腾讯云生产，`/api/v1/open/health` 200（v2.3.0） |
| 发布控制台（测试发布） | https://release.swiftbugs.cn | 独立 release-console（发布/回滚/备份） |
| 本地全栈（staging 复现） | worktree 前端/后端（独立端口 + SQLite） | 用于需要真实数据/性能测量的 C27 验证 |

## 2. C27 验证结果（Batch 234 全部关闭）

| 项 | 方法 | 状态 |
|----|------|------|
| C27-C1 模块树提取准确率 ≥70% | 本地全栈：构造带标准模块树的需求文档 → 提取 → 比对 | ✅ Closed（Batch 234，2026-08-05）：4 份标注需求文档直建后节点路径集合 25/25，准确率/精确率均 100% |
| C27-C2 图谱 200 节点渲染 <3s | 本地全栈：种 200 实体 → graph API 耗时 + 前端渲染 | ✅ Closed（Batch 234，2026-08-05）：修复隐藏 Tab 首次挂载后，200 节点真实 Chromium 渲染 1029ms（含 canvas 初始化，零页面错误） |
| C27-C3 release_bundle 创建端到端 | 本地全栈：创建 release bundle → 校验清单/资产 | ✅ Closed（Batch 234，2026-08-05）：本地全栈 UI 登录 → 新建发布包 → 详情页，创建 HTTP 200/code=0，零控制台错误 |
| C27-C4 Wiki 基线同步覆盖率 ≥70% | 本地全栈：raw source → 编译 → 覆盖率统计 | ✅ Closed（Batch 234，2026-08-05）：4 个发布包 8 个页面同步 8/8，覆盖率 100%、missing=0 |

> 证据目录：`work-logs/evidence/batch-234/`（`c27-c1-module-accuracy.json`、`c27-c2-graph-200.json` + 截图、`c27-c3-release-bundle.json` + 截图、`c27-c4-wiki-coverage.json`）。
> 四项均由 `C96-1` 汇总，见 `C-CONDITIONS.md`（Batch 234，2026-08-05）；报告 `work-logs/batch-234-graph-lazy-render-qa-report.md`。
> 执行结果如实记录；数据不足的项按 PARTIAL 标注（禁止用本地演示数据冒充真实验收）。
