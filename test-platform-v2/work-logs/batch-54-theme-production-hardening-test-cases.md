# Batch 54 — 五主题与共享组件生产级验收用例

> QA Design | Date: 2026-07-28 | Requirement source: Batch 54 issue register / acceptance standard

## 1. 功能点覆盖矩阵

| 功能点 ID | 功能点 | 主流程 | 异常/边界流 | 正面用例 | 负面用例 |
|---|---|---|---|---|---|
| FP-UI54-01 | 主题治理 | canonical 主题加载、切换、刷新 | 旧别名、非法值、模式不一致 | UI54-001 | UI54-002 |
| FP-UI54-02 | 多页面视觉与响应式 | 五主题在五表面三视口完成主任务 | 横向溢出、200% 文本、横屏 | UI54-003 | UI54-004 |
| FP-UI54-03 | 可访问性与触控 | Axe、键盘、焦点、44px | 低对比、无名控件、小热区 | UI54-005 | UI54-006 |
| FP-UI54-04 | 共享状态组件 | loading/empty/error/success | spinner 抖动、不可恢复空态、无名进度 | UI54-007 | UI54-008 |
| FP-UI54-05 | 高密度数据与图表 | 100 行、局部滚动、图表替代 | 全局溢出、缺摘要、色彩唯一表达 | UI54-009 | UI54-010 |
| FP-UI54-06 | 请求与真实后端 | 单动作单请求、真实登录与回读 | 401、取消、后到响应、重复 mutation | UI54-011 | UI54-012 |

覆盖率：6/6 功能点均具备正面与负面用例，设计覆盖率 100%。

## 2. 环境与数据基线

- 分支：`feature/batch-54-theme-production-hardening`
- 基线：`origin/main@67bc7eca712e1194c23abe6dc8ad7828118e4f7b`
- 前端：Batch 54 worktree 独立端口 `5178`。
- 后端：Batch 54 worktree 独立端口 `8005`；临时 SQLite 与临时凭据只用于真实链路，执行后后端停止。
- 主题：`cyberpunk`、`apple`、`clay`、`xlab`、`liquid-glass`；`obsidian-flow` 作为 Batch 53 回归基准。
- 模式：五个非黑曜主题均执行 light/dark；黑曜保持 dark-only。
- 视口：390×844、768×1024、1440×900；另测 844×390 与 200% 根字号。
- 确定性数据：100 条用例、完整工作台统计、图谱 2 节点/1 关系、空集成配置。
- 真实数据：登录后创建 24 条隔离用例，验证移动表格与桌面工作台，`finally` 批量清理。

## 3. 详细用例

| 用例编号 | 模块 | 用例标题 | 重要程度 | 类型 | 前提条件 | 操作步骤 | 可观察预期结果 | 自动化/备注 |
|---|---|---|---|---|---|---|---|---|
| UI54-001 | 主题治理 | 五主题合法值在加载、刷新和跨路由后保持一致 | P0 | UI/正面/自动 | 清空或预置合法主题与模式 | 1. 写入主题/模式<br>2. 打开工作台<br>3. 依次访问五个关键表面并刷新 | `html[data-theme]`、class、Theme Lab、存储值一致；首屏无错误主题；无运行时错误 | Batch54 fixture + real backend |
| UI54-002 | 主题治理 | 旧别名和非法值确定迁移或回退 | P0 | 单元/负面/自动 | 预置 `crystal/column/liquid` 与非法值 | 1. 初始化 Provider<br>2. 读取规范化结果<br>3. 再次初始化 | 旧值迁移到 canonical 且幂等；非法值回退默认；registry 六主题唯一 | registry/governance Vitest |
| UI54-003 | 响应式 | 五主题×light/dark×三视口遍历五个关键表面 | P0 | UI/a11y/正面/自动 | 固定生产形态 fixture | 1. 30 个矩阵单元依次打开工作台、用例、集成、图谱、Theme Lab<br>2. 运行 Axe/overflow/runtime | 150 次页面检查均无 Axe A/AA、全局溢出、运行时错误；主题与模式正确 | `batch54-five-theme-production.spec.ts` |
| UI54-004 | 响应式 | 200% 文本与移动横屏保持主任务可达 | P0 | 兼容/负面/自动 | 五主题，844×390，根字号 200% | 1. 打开用例服务<br>2. 定位命名表格区<br>3. 检查全局宽度 | 页面溢出≤1px；表格在命名局部区域滚动；核心内容可见 | 同上 5 项边界用例 |
| UI54-005 | 可访问性 | 键盘、读屏与对话框焦点契约不因主题变化而降低 | P0 | a11y/正面/自动 | 关键页面有代表数据 | 1. 在共享契约回归中仅用键盘操作导航、筛选、表格和对话框<br>2. 五主题分别键盘打开 Theme Lab 对话框并以 Escape 关闭<br>3. 运行 Axe | 名称/角色/状态完整；对话框焦点被圈定并返回触发器；Axe A/AA 0 | Batch53 16 项共享行为回归 + Batch54 五主题焦点闭环/Axe |
| UI54-006 | 触控 | coarse pointer 下所有代表控件达到 44×44 | P0 | UI/负面/自动 | 390/768 启用 hasTouch | 1. 测量 button/link/input/select/tab/checkbox/combobox/menuitem<br>2. 测量 Theme Lab 控件 | 所有启用控件有效命中区≥44×44；Checkbox 可见方框仍为 16px | Batch54 matrix |
| UI54-007 | 共享状态 | 首次加载、进度、空态和图表替代具备完整语义 | P0 | UI/正面/自动 | 注入慢请求、空数据、100 行与图表数据 | 1. 观察 Skeleton<br>2. 检查 Progress 名称<br>3. 检查空态动作<br>4. 展开图表数据表 | Skeleton 保留结构；Progress 有名称和值；空态可恢复；图表有标题/摘要/表格 | Vitest + Batch53/54 Playwright |
| UI54-008 | 共享状态 | 500、无数据和禁用状态不会静默或误导 | P0 | UI/负面/自动 | 可控制接口 500/空/慢 | 1. 返回失败<br>2. 点击重试<br>3. 检查重复提交 | 原位错误含恢复路径；禁用期间不可重复提交；一次动作一个请求 | Batch53 shared regression |
| UI54-009 | 数据密度 | 100 条数据可分页且不破坏布局 | P0 | UI+性能/正面/自动 | fixture 共 100 条 | 1. 打开用例服务<br>2. 检查 total、20 行首屏并翻到第 2 页<br>3. 验证命名局部滚动契约 | total 为 100；首屏 20 行；第 2 页出现第 21 条；局部区域有名称、tabindex 和 `overflow-x:auto`，仅在内容超宽时滚动；页面无全局滚动 | Batch54 五主题边界用例 + DataTable Vitest |
| UI54-010 | 视觉语义 | 状态色、灰阶、Emoji 和动效债务均被阻断 | P1 | 静态/负面/自动 | 扫描生产 TS/TSX/CSS | 扫描固定 hue/灰阶、8–11px、Emoji、原生 confirm、transition-all、无效 ring 和非白名单 raw color | 七类计数均为 0；图表/主题预览 raw color 仅在带理由的跨平台 allowlist | governance Vitest；规则自身由匹配结果非空即失败的断言构造验证 |
| UI54-011 | 真实后端 | 真实登录、五主题遍历与真实数据回读 | P0 | E2E+API/正面/自动 | 隔离后端、临时账号、无 `/api/v1/**` mock | 1. 登录<br>2. 创建 24 条用例<br>3. 验证移动用例和桌面工作台<br>4. 遍历五主题 light/dark并比对统计值<br>5. 批量清理并校验删除响应 | 登录/创建/GET/统计均来自真实后端；工作台用例总数与 API 一致；Axe/overflow/runtime 通过；清理返回删除 24/24 | Batch53 real + Batch54 real，3/3，skipped=0 |
| UI54-012 | 认证与竞态 | 未登录、取消和后到响应提供正确恢复 | P0 | E2E/负面/自动 | 新浏览器上下文；可延迟请求 | 1. 未登录打开工作台<br>2. 验证跳登录<br>3. 快速切换筛选使旧请求后到 | 真实 401 跳转登录且表单可用；旧响应不覆盖新状态；取消不弹伪错误 | Batch54 real 401 + Batch53 request race |

## 4. A01–A12 门禁映射

| 门禁 | Batch 54 证据 |
|---|---|
| A01 | issue register、acceptance standard、用例、QA 与代码逐项映射 |
| A02 | Agent Team/Codex 独立 worktree；5178/8005；metadata 验证通过 |
| A03 | 6 个功能点正/负面覆盖；P0/P1 全部执行 |
| A04 | 真实登录、用例 CRUD/清理、统计 envelope 与 UI 回读 |
| A05 | 本批无 RBAC/租户逻辑差异，范围判定 N/A；真实未登录 401 + 路由守卫仅作认证回归，不冒充跨租户矩阵 |
| A06 | 100 条 fixture 的 total/分页/行数一致；真实工作台统计值与 API 回读一致；清理响应 24/24 |
| A07 | 单动作单请求、AbortSignal、重复提交与竞态回归 |
| A08 | 100 条高密度数据、分页、局部滚动和 content-visibility |
| A09 | 390/768/1440、844×390、200%、Axe、44px、console/pageerror |
| A10 | 本批无后端模型/迁移差异；后端迁移门禁 N/A 有差异依据 |
| A11 | npm ci、typecheck、build、190 Vitest、54 浏览器用例、3 真实链路 |
| A12 | QA、Leader Verdict、问题台账和证据数一致；生成报告不提交 |

## 5. 最终执行结果

| 用例 | 结果 | 证据 |
|---|---|---|
| UI54-001/002 | PASS | 六主题 registry、别名、模式与 Theme Lab Provider 测试 |
| UI54-003/004 | PASS | 五主题 30 矩阵单元 + 5 边界用例，共 35/35 |
| UI54-005/006 | PASS | 每个矩阵表面 Axe A/AA；390/768 触控测量；五主题 Theme Lab 焦点闭环；Batch53 16/16 |
| UI54-007/008 | PASS | Skeleton、Progress、空态、错误恢复与单次提交回归 |
| UI54-009/010 | PASS | 100 条 fixture 的 total/20 行/第 2 页/局部滚动；跨平台治理测试与最终静态扫描全 0 |
| UI54-011/012 | PASS | 真实后端 3/3，skipped=0；24 条数据已清理；真实 401 通过 |

最终判定：**READY**。P0/P1 12/12 通过，设计覆盖与执行覆盖均为 100%。
