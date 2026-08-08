# Batch 123 — Design Spec（知识中心可用性 + 体育模块关联图谱）

> **Design (🎨)** | Date: 2026-08-08 | Status: 就绪

## 0. 技术体系确认
前端 shadcn/ui + Radix + Tailwind + CVA（Token 走语义类）；后端 FastAPI + SQLAlchemy。走 `cameltv-ui-conventions`。

## 1. 知识源详情弹窗规范
- 交互载体：`Sheet`（右侧抽屉，`sm:max-w-xl lg:max-w-2xl`）替代大 Dialog；内容多时抽屉内滚动。
- 分段：概要（标题/类型/状态/知识域/保鲜度/验证时间）→ 溯源链路（项目→模块→来源）→ 元数据（JSON 折叠）→ 原始内容（`max-h-[40vh]` 内滚动）→ 切片列表（卡片，`max-h` 内滚动）。
- 空态：无切片展示「该知识源暂无切片」。

## 2. wiki 编译 / 差异对比交互规范
- **编译**：点「编译」→ 行内按钮 loading → 下方出现任务状态条（进行中 spinner / 成功 / 失败+错误文案）；成功后自动刷新页面列表并**直接展示本次生成的页面**（可点击打开 markdown 内容）。
- **差异对比**：发起后任务状态卡片（轮询）；成功 → 差异项列表（维度/严重级/证据/左右值），点击展开详情抽屉；失败 → 错误文案；空差异 → 「未发现差异」空态。

## 3. 图谱语义关系 + 体育模块关联（核心）
### 3.1 关系类型扩展
| 关系 | 含义 | 来源 |
|------|------|------|
| `contains` | 层级包含 | 既有 |
| `tested_by` | 用例覆盖接口/模块 | Batch 122 用例 module/api_endpoint |
| `navigates_to` | 用户端跳转（如 首页→赛事详情） | 用例 steps/交互拓扑 |
| `configures` | konfi/运营后台配置影响用户端 | 用例「关联:」标签 |
| `links_to_admin` | 用户端功能 ↔ 运营后台管理页 | 功能地图 admin↔client 映射 |
| `evolves_from` | 版本演化 | 发布包 |

### 3.2 模块关联导入
- 输入：Batch 122 `work-logs/evidence/batch-122/cases/**/*.json`（闭环/关联:标签/模块路径/入口）+ 功能地图 §4 konfi 映射。
- 生成实体：`requirement`（模块）、`module`（入口+一级模块）、`test_case`（用例）、`api`（接口）。
- 生成关系：用例→接口 `tested_by`；用例→关联模块 `navigates_to/configures/links_to_admin`；闭环链路（下注→结算→流水）`evolves_from`/`navigates_to`。
- 幂等：按 `from_entity_key+relation_type+to_entity_key` 去重；evidence 记录来源用例 id。
- 图谱前端：按关系类型着色/筛选（沿用 GraphTab 现有 EDGE_DASHES），支持按 入口/模块 过滤。

## 4. 实体溯源规范
- 实体列表行：展示 `来源`（来源类型 Badge + 来源标题截断）。
- 实体详情：展示来源文档引用/切片（source_ref、chunk 标题），可点击溯源。
- 来源缺失的实体：展示「来源待补」标记，不伪装。

## 5. 项目球决策
- 默认改为「体育模块关联球」：按入口聚合模块节点，边=用例关联标签产生的 `links_to_admin/configures/navigates_to`。
- 若实现后价值不足 → 从知识中心导航移除（保代码不删，路由隐藏）。

## 6. 设计 QA 走查点（P0–P3）
- P0：弹窗在 1366×768 与 390×844 下均完整可读可滚动。
- P1：编译/对比 任务进行中、成功、失败三态文案与图标明确。
- P2：图谱节点过多时性能（limit+分层）。
- P3：项目球价值验证。

## 7. 设计签核
结论：**通过**（规范可落地；P3 项目球以走查证据定去留）。
