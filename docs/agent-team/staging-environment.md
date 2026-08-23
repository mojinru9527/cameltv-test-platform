# staging 环境登记（C27-* / 迁移演练）

> 2026-08-23：生产已迁移腾讯云（swiftbugs.cn）。旧 Vercel/Railway 即将下线，
> staging 替代为**本地全栈 + 生产只读验证**，不再映射到海外环境。

## 1. 环境映射（2026-08-23 更新）

| 用途 | 地址 | 说明 |
|------|------|------|
| 前端（staging 替代） | https://swiftbugs.cn | 腾讯云生产（迁移后；旧 Vercel 已下） |
| 后端 API（staging 替代） | https://swiftbugs.cn/api | 腾讯云生产，`/api/v1/open/health` 200（v2.3.0） |
| 发布控制台（测试发布） | https://release.swiftbugs.cn | 独立 release-console（发布/回滚/备份） |
| 本地全栈（staging 复现） | worktree 前端/后端（独立端口 + SQLite） | 用于需要真实数据/性能测量的 C27 验证 |

## 2. C27 验证计划

| 项 | 方法 | 状态 |
|----|------|------|
| C27-C1 模块树提取准确率 ≥70% | 本地全栈：构造带标准模块树的需求文档 → 提取 → 比对 | 待执行（需标注语料） |
| C27-C2 图谱 200 节点渲染 <3s | 本地全栈：种 200 实体 → graph API 耗时 + 前端渲染 | 待执行 |
| C27-C3 release_bundle 创建端到端 | 本地全栈：创建 release bundle → 校验清单/资产 | 待执行 |
| C27-C4 Wiki 基线同步覆盖率 ≥70% | 本地全栈：raw source → 编译 → 覆盖率统计 | 待执行 |

> 执行结果如实记录；数据不足的项按 PARTIAL 标注（禁止用本地演示数据冒充真实验收）。
