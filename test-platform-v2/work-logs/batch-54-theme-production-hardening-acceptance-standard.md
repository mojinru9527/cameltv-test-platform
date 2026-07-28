# Batch 54 多主题与共享组件生产级验收标准

本标准由 Batch 53 黑曜主题的生产验收抽象而来，适用于现有六主题、新主题、共享基础组件和业务页面。目标分为五层，任何主题不得通过页面级特判绕过共享层。

## 1. 五层契约

1. **主题治理层**：canonical ID、别名迁移、版本、状态、模式、密度、材质、能力、fallback 由单一 registry 管理。
2. **共享基础层**：Button/Input/Select/Checkbox/Menu/Tabs/Dialog/Table 的触控、焦点、禁用、错误、加载契约对所有主题一致。
3. **语义令牌层**：业务只使用 canvas/surface/text/action/status/data/border/focus token；固定品牌色和图表色必须有 allowlist 理由。
4. **业务容器层**：统一 AsyncState、EmptyState、DataTable、ChartFrame、确认弹窗和错误恢复。
5. **主题表达层**：主题只能改变 token、材质、密度和必要动效；不得降低可读性、触控、键盘或运行时稳定性。

## 2. 生产满分门禁

### 2.1 主题和模式

- 合法主题首次加载、切换、刷新、跨路由后，DOM 属性、本地存储和项目偏好一致。
- 旧别名迁移确定且幂等；非法值回退到默认主题。
- `supportedModes` 必须与实际视觉一致；原生控件 `color-scheme` 不得和画布明暗相反。
- 首屏不得出现错误主题闪烁。

### 2.2 可访问性

- Axe WCAG 2 A/AA：0 violation。
- 普通文本对比度 ≥4.5:1；大号文本和非文本状态 ≥3:1。
- 状态不得只依赖颜色，必须同时有文字、图标或形状。
- 页面唯一 H1；交互均有可访问名称。
- 键盘完成导航、筛选、表格、表单、Dialog；Escape 关闭，焦点返回触发器。
- 200% 文本下不裁切、不遮挡，核心动作仍可达。

### 2.3 响应式和触控

- 基准视口：390×844、768×1024、1440×900；高风险页补 844×390 横屏。
- 页面横向溢出 ≤1px；表格只能在有名称、可聚焦的局部区域滚动。
- coarse pointer 下 button/input/select/menu/tab/pagination/effective checkbox target 均 ≥44×44px。
- 相邻高频热区至少 8px，或命中区域不重叠。

### 2.4 状态与恢复

- loading/empty/error/retry/populated/disabled/success 全覆盖。
- 300ms 内请求不闪烁；超过 300ms 使用匹配内容结构的 Skeleton。
- 初始空态有创建/导入动作；筛选空态有清除筛选；错误态有重试。
- 表单非法输入不发请求并聚焦首错；500 后保留输入；重复提交只产生一次 mutation。

### 2.5 数据与性能

- 图表同时提供标题、摘要、单位和结构化数据表；图形值与 API/表格逐项一致。
- 50/100 行数据仍可滚动、选择、排序、翻页；不丢焦点、不重复请求。
- 单动作单请求；批量操作使用单一批量任务/接口。没有批量接口时不得在循环中逐条请求。
- 所有 effect 异步请求有 AbortSignal 或明确 cancelled cleanup；旧响应不得覆盖新状态。
- console error、pageerror、非预期 requestfailed 为 0。

### 2.6 动效和材质

- 禁止 `transition-all`；只动画 transform/opacity/color 等明确属性。
- reduced-motion 关闭非必要运动；Skeleton 不持续闪烁。
- Liquid Glass 在 reduced-transparency 和无 backdrop-filter 时仍可读。
- blur、shadow、glow 不得覆盖高密度正文；非交互卡片不得显示手型。

## 3. 自动化矩阵

基础矩阵：`主题 × 支持模式 × 390/768/1440 × 关键表面`。

证据分两层，禁止互相冒充：

- **确定性 UI 矩阵**：允许固定生产形态 fixture，用于逐主题验证 Axe、对比度、响应式、触控、空/错/慢和运行时稳定性；报告必须明确标注 mock 范围。
- **真实后端抽样**：不得 mock `/api/v1/**`，必须报告 skipped 数、登录/项目头/真实数据回读与清理结果。任一真实链路 P0 被 skip 时不能评满分。

基础关键表面至少包括：

- `/workbench`：KPI、图表、摘要、主题切换；
- `/testcase`：筛选、50+/100 行表格、分页、行操作；
- `/integration`：表单校验、保存、危险确认；
- `/knowledge?tab=graph`：图谱控制和文本替代；
- `/theme-lab`：Button/Input/Select/Tabs/Table/Badge/Tooltip/Toast/Dialog/Sheet/Skeleton。

受本批差异直接影响的高风险路由（例如 Panorama、Requirement 审核或 Release Bundle 详情）必须额外加入扩展矩阵；未受影响的扩展路由由既有回归与共享契约覆盖，不得写成已完成逐主题视觉遍历。

负面证据分层执行：长文案、空态和状态色必须分配到每个主题的基础矩阵；500、慢网、竞态、重复提交等主题无关的行为契约在共享组件/代表主题执行一次完整回归，再由 Theme Lab 与语义 token 门禁证明五主题外观不降级。只有主题 CSS 会改变行为时，才扩展为主题全矩阵，避免把重复笛卡尔组合冒充有效覆盖。

## 4. 静态防回归

- 生产 TSX 禁止固定 Tailwind 状态 hue 类。
- 生产业务文字禁止 `text-[9px]`、`text-[10px]`、`text-[11px]`。
- 禁止原生 `confirm`、结构性 Emoji、无效 CSS ring 属性和 `transition-all`。
- 图表/品牌 raw color 仅允许在带理由的文件 allowlist。
- 六主题 registry 完整性、canonical 别名和模式真实性由 Vitest 阻断。

## 5. 评分规则

总分 100：视觉层级 15、主题一致性 15、响应式 15、可访问性 20、交互状态 15、数据与性能 10、运行时稳定性 10。

只有全部 P0/P1 用例已执行且通过、真实后端 `skipped=0`、静态和构建门禁全绿时才具备评分资格；否则结论固定为 `NEEDS WORK`，不得先给 100 分再列未执行项。

任何以下问题直接判定 `NEEDS WORK`，不允许用总分抵消：Axe A/AA 失败、核心操作不可键盘完成、移动端核心控件小于 44px、全局横向溢出、表单假成功、旧请求覆盖新状态、单动作重复请求、真实后端证据被 skip。
