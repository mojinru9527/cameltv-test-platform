# Batch 54 五主题生产级加固问题台账

更新日期：2026-07-28
基线：`origin/main@67bc7eca712e1194c23abe6dc8ad7828118e4f7b`
范围：`test-platform-v2/frontend`
目标：在保留 Batch 53 黑曜主题成果的前提下，清零其残余 UI 债务，并把同一生产门禁应用到其余五套主题与共享组件。

## 1. 主题范围与旧名称映射

生产主题以 `src/lib/themes.ts` 为唯一事实源。五套非黑曜主题为：

| Canonical ID | 生产名称 | 旧称/别名 |
|---|---|---|
| `cyberpunk` | Cyberpunk Terminal | 无 |
| `apple` | Apple Minimal | `crystal`、`blue` |
| `clay` | Clay Studio | `column`、`warm`、`nature` |
| `xlab` | X-Lab | `dark-minimal` |
| `liquid-glass` | Liquid Glass Panoramic | `liquid` |

`column` 不是第六套独立主题；它迁移到 `clay`。黑曜主题 `obsidian-flow` 继续作为第六套生产主题与回归基准。

## 2. Batch 53 继承结论

以下条目已在 Batch 53 关闭，本批次只做回归，不重复开发：真实后端链路、黑曜主题的响应式/Axe/触控、导航名称、图表数据替代、确认弹窗、表单错误焦点、请求竞态、原生 `confirm` 清零。

## 3. Batch 54 问题与状态

| ID | 级别 | 问题 | 修复/验收结果 | 状态 |
|---|---|---|---|---|
| UI54-P0-01 | P0 | UI registry 只注册黑曜，兼容 Provider 把其余主题折叠为 `default` | 六主题进入统一 registry；Provider 保留 canonical ID；旧别名有确定迁移表 | 已修复 |
| UI54-P0-02 | P0 | Cyberpunk、X-Lab、Liquid Glass 的 light 声明与实际深色画布不一致 | 三套主题补齐真实浅色 canvas/surface/text/sidebar/glass token | 已修复 |
| UI54-P0-03 | P0 | 五主题缺少生产级对比度证据 | 扩展为五主题×light/dark×390/768/1440 的 30 单元，每单元遍历工作台/用例/集成/图谱/Theme Lab；另含 5 个 200%/横屏用例，共 35/35 | 已修复 |
| UI54-P0-04 | P0 | 44px coarse-pointer 契约仅在黑曜 CSS | 契约下沉全局共享层；Button/Input/Select/Menu/Tab/Checkbox 统一有效热区 | 已修复 |
| UI54-P0-05 | P0 | focus CSS 使用无效 `ring-width/ring-color/ring-offset` | 改为标准 `outline`、`outline-offset`、`box-shadow`；静态扫描为 0 | 已修复 |
| UI54-P1-01 | P1 | 63 个 TSX 文件约 950 处固定状态色绕过主题 | 迁移至 success/warning/danger/info/accent 语义 token；生产 TSX 固定 hue 门禁为 0 | 已修复 |
| UI54-P1-02 | P1 | 30 个 TSX 文件、110 处 9–11px 业务文字 | 全部迁移到最小 `text-xs`（13px）；Theme Lab 与全局生产 CSS 同步不低于 12px | 已修复 |
| UI54-P1-03 | P1 | 15 个 AsyncState 默认 spinner，慢加载结构跳动 | AsyncState 首次加载默认结构化 Skeleton，保留 `aria-busy` 和可读名称 | 已修复 |
| UI54-P1-04 | P1 | DataTable/用例页 50–100 行缺少性能与局部滚动契约 | 始终提供命名、可聚焦滚动区；50+ 行启用 `content-visibility` 隔离且不丢 DOM 行 | 已修复 |
| UI54-P1-05 | P1 | Report/Trace/Performance 共六张图缺少统一摘要与结构化替代 | 新增共享 `ChartFrame`；图表配对标题、文字摘要、可展开数据表 | 已修复 |
| UI54-P1-06 | P1 | 接口分组执行逐条请求 | 改为一次创建批量执行任务；单次操作只发一个 mutation | 已修复 |
| UI54-P1-07 | P1 | AI 产物“批量”审核/导入在循环中逐条请求 | 后端无批量审核路由时，UI 改为诚实的单选处理；每次操作恰好一个 mutation，不再伪装批量 | 已修复 |
| UI54-P1-08 | P1 | mindmap / API 用例初始请求未完整取消，失败被吞掉 | 透传 AbortSignal，effect cleanup 主动 abort，非预期失败给出 toast | 已修复 |
| UI54-P1-09 | P1 | Badge solid 背景与状态文字在多主题下仅 1.26–4.28:1 | 改为 muted status surface + status text；Liquid Glass 不再覆盖 tone 背景；多页面 Axe 复验 0 | 已修复 |
| UI54-P1-10 | P1 | Theme Lab 未进入真实 Provider，存在 8px、低对比、无效 ARIA 和 768px 全局溢出 | 接入 ThemeProvider；提升文本 token；修正按钮前景、ARIA、44px 与命名局部表格滚动；35 项矩阵全绿 | 已修复 |
| UI54-P1-11 | P1 | 固定白/灰表面及固定渐变未被静态门禁覆盖 | 迁移到 card/muted/status token；门禁覆盖 from/via/to 与 white/black/gray/slate | 已修复 |
| UI54-P1-12 | P1 | Progress 无可访问名称，AI 产物伪单选仍以 Checkbox/批量文案呈现 | Progress 默认提供名称；AI 产物改为逐行审核/导入、结构 Skeleton 和可取消初始请求 | 已修复 |
| UI54-P2-01 | P2 | dataset/project/testplan/testcase/schedule/release/system 空状态无恢复动作 | 初始空态提供创建动作；筛选空态提供清除筛选；权限不足不展示越权动作 | 已修复 |
| UI54-P2-02 | P2 | 父导航显示 disclosure 图标但实际直接导航、子项常显 | 明确采用“父项即导航”模型，移除误导性 disclosure 图标 | 已修复 |
| UI54-P2-03 | P2 | BundleDetail 移动端头部、400px 输入、四列统计和多主 CTA | 头部/动作可换行，输入流式宽度，统计 2→4 列，单一主 CTA，次要操作降级 | 已修复 |
| UI54-P2-04 | P2 | Theme Lab 产品路由未加载自身样式 | 路由组件直接导入样式；独立入口与产品入口一致 | 已修复 |
| UI54-P2-05 | P2 | 结构性 Emoji/字符图标依赖平台字体 | 替换为 Lucide 图标或明确文字标签；代表字符静态扫描为 0 | 已修复 |
| UI54-P2-06 | P2 | `transition-all` 引发无关属性动画 | 共享组件与主题 CSS 改为显式属性列表；静态门禁为 0 | 已修复 |
| UI54-P2-07 | P2 | Clay/Liquid 装饰过载和非交互卡片手型 | Clay 恢复边界并收敛 pill/行阴影；Liquid 限制 blur/shadow；移除非交互 cursor 强制 | 已修复 |
| UI54-P2-08 | P2 | 静态治理仅扫描 `.tsx`，遗漏 `.ts` 中的固定灰阶 | 扩展到生产 `.ts/.tsx`；缺陷状态默认样式迁移至 semantic token | 已修复 |
| UI54-P2-09 | P2 | raw color allowlist 含业务严重度文件且使用 Windows 路径，Linux CI 会失配 | 业务严重度/置信度迁移到状态 token；allowlist 仅保留主题预览、图表和黑曜隔离壳，并统一 `/` 路径 | 已修复 |
| UI54-P2-10 | P2 | Theme Lab 自定义 Dialog 缺少焦点圈定和关闭后焦点恢复 | 增加 Tab 圈定、Escape 关闭和触发器焦点恢复；五主题自动化逐一验证 | 已修复 |
| UI54-P2-11 | P2 | 首屏同步 bootstrap 与 TypeScript 主题目录双处维护存在漂移风险 | 保留无闪烁所需同步 bootstrap，并新增目录/默认值/alias 完整一致性阻断测试 | 已修复 |

## 4. 允许项与边界

- 图谱、性能曲线、AI 严重度预览允许使用稳定的数据可视化调色板，但必须进入带理由的静态 allowlist，并提供文字/表格替代；业务状态文字不得直接使用固定色板。
- `ui-concepts` 是独立概念演示入口，不属于产品路由；其历史 9–11px 视觉稿不计入生产门禁。`theme-lab` 属于产品路由，已纳入。
- AI 产物真正的多条原子批量审核需要后端新增批量路由。在此之前前端采用单选处理，避免 N+1 和“部分成功”假象。

## 5. 发布判定

P0/P1 必须全部关闭；P2 不允许以“历史问题”跳过。最终发布证据必须包含：类型检查、生产构建、全量 Vitest、五主题多页面 35 项浏览器门禁、Batch 53 黑曜回归、真实后端 skipped=0、静态债务扫描、运行时错误清单和实际 skipped 数量。证据详见同目录 QA Report。
