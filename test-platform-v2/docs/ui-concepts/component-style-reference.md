# 测试平台组件与风格参考库

更新日期：2026-07-18

## 研究边界与来源

- 用户指定清单：[NameThatUI · Web](https://namethatui.com/?platform=web)、[LearnUI · Web](https://learnui.qiaomu.ai/?platform=web#dictionary)。两个页面在当前企业网络策略下无法直接读取，因此本文件不复述或冒充站点原文；条目名称来自用户给出的清单，解释和落地规则按通用产品设计规范归纳。
- 交互规范校验：[Material Progress Indicators](https://m2.material.io/components/progress-indicators)、[Material Snackbars](https://m2.material.io/components/snackbars/android)、[W3C Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/)、[MDN `::backdrop`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Selectors/%3A%3Abackdrop)、[MDN Easing Functions](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Easing_functions)、[Nielsen Norman Group Skeleton Screens](https://www.nngroup.com/articles/skeleton-screens/)。
- 风格校验：[Apple Liquid Glass](https://developer.apple.com/documentation/TechnologyOverviews/liquid-glass)、[Apple 官网](https://www.apple.com/)、[xAI Grok](https://x.ai/grok)、[ClickHouse](https://clickhouse.com/clickhouse)、[ClickStack 品牌主题说明](https://clickhouse.com/blog/whats-new-in-clickstack-january-2026)。

## 一、组件与交互记录

### 1. Progress Ring、Spinner、Progress Bar

| 模式 | 表达的信息 | 测试平台落点 | 使用规则 | 不应使用 |
|---|---|---|---|---|
| Progress Ring | 已知进度、紧凑的单个完成率 | 测试计划完成率、覆盖率、产物生成率 | 必须显示百分比或数值；适合一个核心指标 | 多指标并排比较、超长任务明细、只靠颜色表达状态 |
| Spinner | 未知进度、短时局部等待 | 发送 API 请求、加入执行队列、按钮提交 | 300 ms 内不出现；约 0.3–5 s 的局部动作使用；按钮同时禁用防重复提交 | 整页加载、可计算进度的长任务、表格中央无限旋转 |
| Progress Bar | 已知或阶段性的线性进度 | 回归批次、执行流水线、报告生成、上传 | 优先展示总进度和当前阶段；长任务同时给出阶段文案、已用时间和取消/后台运行入口 | 为同一批次中的每个微小步骤都放一条进度条 |

统一规则：可测量时用 Ring/Bar，不可测量且很短时才用 Spinner；任务超过 5 秒应补充阶段、剩余量或后台通知。Material 建议同类活动在全产品中保持同一种进度表达，并优先显示一组流程的总体进度。

### 2. Text Scramble / Decode Effect

- 定位：短标签、系统握手、运行编号或命令状态的“科技感揭示”，不是通用文本动画。
- 推荐落点：X-Lab 主题中的“正在编排 RUN-5130”、命令面板命中项、首次进入运行中心的状态标题。
- 时长：320–480 ms；完成后必须稳定为真实文本。
- 可访问性：外层提供完整 `aria-label`，随机字符对读屏隐藏；`prefers-reduced-motion: reduce` 时直接显示结果。
- 禁止：日志正文、失败原因、表单标签、按钮主文案、实时数值、每次刷新都播放、无限循环乱码。

### 3. Skeleton vs. Spinner

| 场景 | 选择 | 原因 |
|---|---|---|
| 页面、列表、表格、图表的结构已知 | Skeleton | 提前保留最终布局，降低布局跳动，并提示内容将出现在哪里 |
| 单个按钮或局部操作，耗时未知且短 | Spinner | 只表达“当前动作仍在进行”，不伪造页面结构 |
| 首屏数据较慢但导航可用 | 局部 Skeleton | 导航和标题保持可操作，内容区逐块替换 |
| 长时间后台执行 | Progress Bar + 状态文案 + Snackbar/通知 | Spinner 或 Skeleton 都不足以解释长期状态 |

Skeleton 应接近最终布局但简化细节；禁止把每个字、每个图标都做成闪动占位，避免视觉噪音。

### 4. 背景幕布 / Backdrop

- 用途：命令面板、危险环境切换、启动回归确认、全局搜索等需要暂时聚焦的顶层任务。
- 视觉：纯色透明遮罩优先，轻微模糊可选；内容弹层保持不透明，保证日志和数据文字对比度。
- 行为：打开后焦点进入弹层，`Esc` 关闭非强制弹层，关闭后焦点回到触发按钮；危险确认不能仅靠点击幕布退出。
- 工程建议：生产实现优先原生 `<dialog>.showModal()` 或可靠的 Dialog 组件，让元素进入 top layer；建立 `dropdown → sticky → backdrop → modal → snackbar → tooltip` 的语义层级。

### 5. Easing / 缓动与定时

| 交互 | 推荐时长 | 推荐曲线 |
|---|---:|---|
| Hover、按压、状态色变化 | 100–160 ms | ease-out |
| Tabs、抽屉内容、行选中 | 160–220 ms | ease-out-quart |
| 弹层进入 | 180–240 ms | ease-out-quint |
| 弹层退出 | 120–180 ms | ease-in，退出快于进入 |
| Liquid Glass 形态变化 | 240–360 ms | 平滑 ease-in-out；只用于顶层控制 |
| Text Scramble | 320–480 ms | 分段更新，完成后停止 |

不对 `width/height/top/left` 做持续布局动画，优先 `transform/opacity/filter`。数据平台不使用弹跳、弹性或编排式整页入场；所有动画提供 reduced-motion 替代。

### 6. Snackbar / 轻提示

- 低优先级、非阻断反馈：保存成功、已加入队列、筛选视图已保存、复制成功。
- 桌面端固定在左下或居中下方，避开侧栏、底部操作条和常用控件。
- 同时只显示一条；后续消息排队替换，不堆叠。
- 文案一行优先，仅允许一个文字操作，例如“撤销”“重试”“查看”。
- 约 4–10 秒自动消失；鼠标悬停或键盘聚焦时暂停计时。
- 失败导致数据不可用、权限不足、生产风险等情况应使用 Inline Alert、Banner 或 Dialog，而不是 Snackbar。

### 7. Tabs

- 用途：同一对象或同一工作上下文内的平级视图，例如“概览 / 实时日志 / 产物 / 关联缺陷”。
- 不承担整个平台一级导航；模块过多时使用侧栏或路由。
- 键盘：`Tab` 进入当前标签，左右方向键移动，`Home/End` 到首尾，必要时 `Enter/Space` 手动激活。
- 面板已预加载且切换无明显延迟时可跟随焦点自动激活；需要请求数据时采用手动激活并显示局部 Skeleton。
- 标签过多时允许横向滚动或“更多”菜单，禁止把标签压缩到无法阅读。

## 二、风格记录与适配判断

### Liquid Glass / 液态玻璃

- 核心：透明材质、背景折射/模糊、动态高光与形态过渡；它应该是位于内容之上的“功能层”。
- 测试平台适合：顶部导航、浮动筛选条、命令面板、Popover、当前环境控件。
- 测试平台不适合：数据表格、日志、代码块、失败详情、密集 KPI 卡片。
- 必须提供不透明回退、降低透明度/动态的设置，并验证文字在不同背景上的对比度。
- Apple 官方建议节制使用，把 Glass 限制在重要功能元素，避免多层 Glass 相互叠压、抢夺内容注意力。

### Cyberpunk / 赛博朋克

- 核心：近黑背景、少量霓虹信号、终端排版、切角或精密线框、状态扫描感。
- 企业化处理：去掉持续 CRT 闪烁和铺满页面的扫描线；霓虹只表示焦点、运行、告警和选中，不给普通文本发光。
- 最适合：夜间运行中心、实时日志、自动化执行、故障定位。
- 风险：高饱和色造成视觉疲劳，细线和低亮灰影响对比度，Glitch 会破坏可读性。

### Claymorphism / 黏土拟态

- 核心：软 3D、浅内外阴影、柔和体块、按压形变、低威胁感。
- 企业化处理：冷灰紫底、14–16 px 圆角、单层浅深度；彩色仅用于模块和状态，不使用儿童化文案或糖果色大面积铺陈。
- 最适合：低代码用例编排、测试计划搭建、新手引导、空状态和协作流程。
- 不适合：高密度日志、告警中心、数十列数据表、夜间大屏。

### Apple

- 可借鉴：内容优先、强留白、克制的文字层级、少而清晰的 CTA、标准图标与可预测操作位置；Liquid Glass 只作为导航与控制层。
- 不照搬：消费电子官网的大幅产品图和长滚动叙事不适合生产工具主界面。

### xAI

- 可借鉴：黑白高对比、直接的大标题、AI/终端输入面、代码或推理状态的可审计表达、少量强信号色。
- 不照搬：营销页面的大字号和大段留白不适合信息密集的日常测试工作台。

### ClickHouse

- 可借鉴：白/黄/黑的高识别度、技术证据和代码优先、对速度与规模的直接表达、密集但有秩序的数据结构。
- ClickStack 在 2026 年公开说明其新主题强调 ClickHouse 熟悉的白、黄、黑，并同时提供明暗版本；这很适合转化为企业测试平台的主生产主题。
- 不照搬：官网的长篇技术叙事和大型营销区块；工作台应保留紧凑行高、筛选、表格和审计链路。

## 三、五套主题蓝图

### 方案 A：Crystal Command / 晶穹控制台

**场景句：** 白天办公室里，测试负责人和项目经理连续查看质量总览、计划和报告，需要安静、清楚、可信。

- 灵感：Apple × Liquid Glass。
- 色彩：冷白与浅蓝灰为内容底，蓝紫作为唯一主操作色；成功/警告/失败保持语义色。
- 结构：实色数据内容层 + 半透明顶栏/浮动筛选层，侧栏可收起。
- 组件组合：Progress Ring 展示计划完成率；表格 Skeleton；Tabs；轻量 Snackbar；背景幕布；Liquid Glass 命令面板。
- 动效：180–220 ms 的淡入与位移，Glass 形态变化不超过 320 ms。
- 适用：管理层总览、报告中心、计划与需求协作。
- 风险：玻璃过多会降低表格可读性；因此所有数据面板保持实色。

### 方案 B：X-Lab / 黑域实验室

**场景句：** 夜间值守的自动化与 SRE 工程师盯着实时日志和异常，需要高对比、紧凑、快速定位。

- 灵感：xAI × 企业化赛博朋克。
- 色彩：近黑、石墨灰、白字；青色表示运行/焦点，品红仅用于 P0 或关键异常。
- 结构：紧凑侧栏、终端式状态头、日志/执行双栏；普通内容不发光。
- 组件组合：Text Scramble 仅用于运行握手；Spinner 表示短时入队；Progress Bar 展示批次；Tabs 切换日志/产物；Snackbar 提供重试。
- 动效：状态切换 140–180 ms；不使用持续闪烁和整页 Glitch；Reduced Motion 直接静态显示。
- 适用：运行中心、自动化、API 调试、故障定位。
- 风险：长时间使用会疲劳，不建议作为唯一默认主题；需提供高对比和低饱和模式。

### 方案 C：Column Pulse / 列阵数据台

**场景句：** 数据与 QA 工程师在普通办公光线下反复筛选上千条用例、运行与缺陷，效率和证据密度优先。

- 灵感：ClickHouse 工业数据风格。
- 色彩：中性白/灰、ClickHouse 黄、黑；黄只用于主操作、当前选中和关键性能指标。
- 结构：36–40 px 表格行、强分隔、Sticky Header、可保存筛选、代码/终端证据区。
- 组件组合：多条 Progress Bar 或 Bullet Chart；表格 Skeleton；Tabs；左下 Snackbar；实体 Backdrop；状态徽标。
- 动效：100–180 ms，以行高亮、筛选更新和进度变化为主。
- 适用：主生产主题、用例服务、缺陷、报告、批量运行。
- 风险：黄色面积过大会刺眼；禁止把所有卡片、表头和按钮都涂黄。

### 方案 D：Clay Studio / 软体测试工坊

**场景句：** 产品、手工测试和业务同事共同编排用例与计划，希望界面降低学习压力并提供明确的按压反馈。

- 灵感：企业化 Claymorphism。
- 色彩：冷灰紫背景，紫色主操作，薄荷绿/柔橙作为协作与提醒色。
- 结构：分步编辑、较大触控目标、柔和模块体块；表格区域仍采用平面实色。
- 组件组合：黏土感 Tabs/分段控件、Progress Ring、分步 Stepper、Skeleton、Snackbar、柔和 Backdrop。
- 动效：按压缩放 0.97、180–220 ms 回弹；不使用夸张弹簧和漂浮装饰。
- 适用：低代码自动化、用例创建、Onboarding、协作计划。
- 风险：不适合作为告警与高密度运行中心的默认皮肤。

### 方案 E：Liquid Spectrum / 液境全景台

**场景句：** 用户需要在总览、用例、运行、日志与产物之间连续工作，希望所有功能组件拥有统一的高端玻璃材质，同时不能牺牲数据可读性和既有操作路径。

- 灵感：Liquid Glass × GlassSurface / FluidGlass × 全组件系统。
- 色彩：冷蓝与紫色环境光场作为玻璃背板，深蓝黑承载文字，蓝紫只用于主操作、焦点和确定性进度；语义状态色保持不变。
- 材质层级：顶栏、侧栏、主题说明、Tabs、面板、Dialog、Snackbar 使用 18–24 px 模糊玻璃；表格、日志、状态和密集数据增加 78%–94% 透明度的“清晰内衬”，保证信息优先。
- 组件组合：Progress Ring、Progress Bar、短时 Spinner、Skeleton、Text Scramble、Tabs、Backdrop、Snackbar 全量映射为同一玻璃语言；主题全景条可直接复用已有加载、提示和启动确认交互。
- 动效：Hover/按压 160 ms，内容与 Tabs 230 ms，进度和玻璃形态 300–320 ms；主题切换优先使用原生 View Transition，只动画 `transform/opacity`，退出快于进入。
- 逻辑约束：主题切换不重置当前模块、Tab、环境、运行进度或 Snackbar 队列；全景条不发起请求、不新增生产操作、不建立第二套业务状态机。
- 无障碍：`prefers-reduced-motion` 关闭主题转场和装饰性动画，`prefers-reduced-transparency` 使用不透明表面，高对比模式强化边界；Text Scramble 完成后稳定显示真实文本。
- 适用：高保真演示、管理与执行混合工作台、需要品牌高级感的正式体验主题。
- 风险：多层 `backdrop-filter` 的 GPU 成本高于其他四套；低性能终端应自动使用不透明回退，生产落地前需验证长列表滚动和集成显卡表现。

## 四、主题与组件分配矩阵

| 组件/风格 | 晶穹 | 黑域 | 列阵 | 软体 | 液境 |
|---|---:|---:|---:|---:|---:|
| Progress Ring | 核心 | 次要 | 少量 | 核心 | 核心 |
| Spinner | 局部 | 核心短任务 | 局部 | 局部 | 核心短任务 |
| Progress Bar | 核心 | 核心 | 核心 | 次要 | 核心 |
| Text Scramble | 不用 | 核心但克制 | 不用 | 不用 | 状态揭示 |
| Skeleton | 核心 | 核心 | 核心 | 核心 | 核心 |
| Backdrop | Glass 幕布 | 深色实体幕布 | 实体幕布 | 柔和模糊幕布 | 高模糊玻璃幕布 |
| Snackbar | 玻璃外观、实色文字层 | 黑底高对比 | 黄/黑工业反馈 | 柔和体块 | 折射玻璃反馈 |
| Tabs | 细线/胶囊 | 终端标签 | 下划线/分隔 | 黏土分段控件 | 流体胶囊 |
| Liquid Glass | 导航与浮层 | 极少 | 不用 | 可做轻度混合 | 全局主材质 + 数据清晰内衬 |

## 五、当前清单遗漏但测试平台应补齐的模式

### P0：先补齐，决定平台是否真正可用

1. **Data Grid / 数据表格体系**：排序、筛选、列显示、固定列、批量操作、保存视图、虚拟滚动、导出。
2. **状态机与 Stepper**：排队、准备、运行、通过、失败、阻塞、取消、超时；必须同时有文字和图形标识。
3. **Inline Alert / Banner / Dialog 分级**：Snackbar 只处理轻反馈，错误和风险必须升级。
4. **Inspector / 详情抽屉与 Split Pane**：在不离开列表上下文时查看运行、用例、缺陷和产物。
5. **Tree View**：项目、模块、计划、套件、环境的层级组织。
6. **Log Stream + Timeline**：暂停、定位错误、按级别过滤、复制、下载、时间跳转。
7. **Diff Viewer 与 Artifact Viewer**：请求/响应、JSON、截图、视频、Trace、基线差异。
8. **Empty / Error / Offline / Permission 状态**：解释原因并给出下一步，而不是只显示“暂无数据”。

### P1：显著提升企业效率

1. Command Palette 与快捷键。
2. Filter Chips、日期范围、环境选择和 Saved Views。
3. Breadcrumb、全局搜索、最近访问、收藏。
4. Context Menu、Popover、Tooltip、批量选择工具条。
5. 通知中心、后台任务中心、审计日志。
6. 响应式密度：舒适/紧凑两档，而不是只按屏幕缩放。

### P2：设计系统护栏

1. Light / Dark 双主题及语义色令牌。
2. High Contrast、Reduced Motion、Reduced Transparency。
3. 图表颜色、线型、标记和数据表替代，不靠颜色单独传达异常。
4. 键盘导航、焦点恢复、读屏 Live Region、44 px 触控目标。
5. 加载阈值和计时规范，防止 Spinner、Skeleton 和 Snackbar 被不同团队随意使用。

## 六、推荐顺序

1. **Column Pulse / 列阵数据台**：最适合作为主生产主题，信息密度、技术可信度和落地风险最平衡。
2. **Crystal Command / 晶穹控制台**：最适合管理层总览、报告和日间协作，可作为第二套正式主题。
3. **X-Lab / 黑域实验室**：最适合运行中心和夜间值守，可做模块级深色工作模式。
4. **Clay Studio / 软体测试工坊**：差异最大，适合低代码和新手流程，建议先验证用户群，不直接替换全平台。
5. **Liquid Spectrum / 液境全景台**：高级感与组件统一性最强，适合先作为体验主题投放；在低性能设备回退验证完成后，再决定是否提升为正式默认主题。
