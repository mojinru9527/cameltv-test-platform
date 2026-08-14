# CamelTv 测试平台 v2 前端架构审查报告（Batch 173）

> 审查对象：`test-platform-v2/frontend/`（React 19 + Vite + axios SPA）
> 文档对照：`test-platform-v2/docs/`（完整PRD / 现状功能PRD / 使用手册）
> 审查方式：静态代码扫描（118 个页面文件、36 个 api 模块、router、layouts、hooks）+ 文档逐条对照
> 审查日期：2026-08（Batch 173）
> 说明：本报告为独立验证结果，不照抄 batch-147 旧结论；凡与 batch-147 结论一致处均以当前代码行号为证。

---

# 任务A —— 前端请求冗余与重复请求审查

## A.0 结论摘要（按影响排序）

| 级别 | 问题 | 证据数 | 影响 |
|------|------|--------|------|
| **P1-1** | 会话级缓存 `cachedGet` 覆盖率极低，且绝大多数调用点传入 `AbortSignal` 直接绕过缓存 → 静态/低频数据（domains/environments/menus）随每次页面挂载重复请求 | 15+ 处 | batch-147「domains×4、environments×6」问题部分复发 |
| **P1-2** | 4 处含异步操作的 `useEffect` 无 cleanup（违反 engineering-standards §4.1 铁律） | 4 处 | StrictMode 下重复请求 + 卸载后 setState 竞态 |
| **P2-1** | 单页面挂载即并行发起 4~5 个 GET 请求，含 `page_size=200/100` 重型调用 | 3 页 | 首屏网络开销大 |
| **P2-2** | 3 处轮询均为固定间隔、无指数退避（cleanup 齐全） | 3 处 | 长任务期间固定 3s 空转 |
| **P3-1** | 死代码：`fetchProjects`、`fetchMe` 定义了全仓库无调用；`project/`、`organization/` 页面因路由重定向不可达 | 5 处 | 维护噪音、误导后续开发 |
| **已修复** | 搜索防抖（batch-147「14键14请求」）、mindmap 10.1MB、菜单 53 次请求、TabsContent 提前挂载 | — | 均已在当前代码验证修复 |

## A.1 页面规模统计（118 个页面文件，合计约 36,583 行）

### 超大型页面（>800 行，单一职责问题）

| 文件 | 行数 | 说明 |
|------|------|------|
| `pages/requirement/AiResultModal.tsx` | 1424 | 需求 AI 结果弹窗，内含 6 个 Tab（extraction/analysis/func/api/regression/coverage）与 21 处 Tabs 标签 |
| `pages/requirement/index.tsx` | 1147 | 需求列表 + 提取 + 蓝湖证据 + 版本对比 + 截图预览全部混在一页 |
| `pages/uitest/index.tsx` | 1072 | UI 任务 CRUD + 运行详情 + 产物回看 + 轮询全在一页 |
| `pages/perftest/index.tsx` | 868 | 性能监控（当前路由已隐藏，仍被维护） |
| `pages/testcase/index.tsx` | 855 | 用例库 + 批量操作 + 评审 + 版本 |

700~800 行临界：`testcase/CaseDrawer.tsx`(755)、`testplan/PlanDetail.tsx`(754)、`release-bundles/BundleDetail.tsx`(745)、`special/index.tsx`(740，隐藏)。

> 五个 >800 行页面中 3 个（requirement×2、uitest）是活跃路由；单一职责拆分建议优先处理 `requirement/AiResultModal.tsx`（1424 行）与 `uitest/index.tsx`（1072 行）。

## A.2 请求冗余模式（全部带 文件:行号 证据）

### P1-1 【架构性】cachedGet 缓存被 AbortSignal 系统性绕过

**机制**：`client.ts:103-131` 实现了会话级缓存 + 进行中去重（Batch 150），但约定「传 signal 时请直接使用 client.get，保持 abort 语义」(`client.ts:101`)。api 模块按此约定写成：

```ts
// api/environment.ts:8-11
export async function fetchEnvironments(signal?: AbortSignal) {
  if (signal) return api.get(BASE, { signal })   // ← 绕过缓存
  return cachedGet<Environment[]>(BASE, undefined, { ttl: 60_000 })
}
```

而页面几乎全部通过 `useApi`/`useAbortableEffect` 传入 signal，导致 **cachedGet 形同虚设**。实测全仓库 `cachedGet` 仅 3 个调用点（`api/auth.ts:40`、`api/environment.ts:10`、`api/testcase.ts:60`），其余 API 函数一律走裸 `client.get`。

**被绕过缓存的具体调用点（传 signal → 走裸 client.get）**：

| 数据 | 调用点 | 说明 |
|------|--------|------|
| `/environments` | `apitest/components/ApiCaseTab.tsx:83` | tab 挂载即拉，永远绕过缓存 |
| `/environments` | `pages/integration/index.tsx:110` | 页面挂载拉取 |
| `/environments` | `release-bundles/BundleDetail.tsx:209` | 页面挂载拉取 |
| `/environments` | `testplan/PlanDetail.tsx:162` | 页面挂载拉取 |
| `/environments` | `pages/uitest/index.tsx:260` | 页面挂载拉取 |
| `/test-cases/domains` | `apitest/components/ApiCaseTab.tsx:82` | tab 挂载拉取 |
| `/test-cases/domains` | `pages/playground/index.tsx:50` | 页面挂载拉取 |
| `/test-cases/domains` | `pages/testcase/index.tsx:136` | 页面挂载拉取 |
| `/test-cases/domains` | `testplan/AddCasesModal.tsx:62` | 弹窗打开拉取 |
| `/system/menus` | `layouts/MainLayout.tsx:219` + `api/auth.ts:39` | 整页刷新时绕过缓存 |

**结果**：60 秒 TTL 缓存只对少数「不传 signal」的调用点生效（如 `environment/index.tsx:60`、`apitest/DebugTab.tsx:128`、`apitest/ApiDebugPanel.tsx:106`、`schedule/index.tsx:123`）。用户快速进出 testcase/apitest/uitest 等页面时，domains、environments 每次重新请求 —— batch-147「domains×4、environments×6」问题在 60s 窗口内依然复现（不同页间无法共享缓存）。

**修复建议**：`cachedGet` 增加「传入 signal 也命中缓存、仅在缓存未命中时发起可取消请求」的语义（例如内部记录 in-flight promise 的 AbortController 集合，abort 只移除订阅不取消共享请求）。

### P1-2 含异步操作的 useEffect 无 cleanup（违反 engineering-standards §4.1）

静态扫描 83 个 useEffect（其中 31 个含异步操作），4 个无任何 cleanup：

| 位置 | 异步操作 | 影响 |
|------|----------|------|
| `pages/defect/DefectFormDialog.tsx:61-81` | `fetchUsers()` + `fetchTestCases({page_size:200})`（每次打开弹窗触发，另见 P2-1） | StrictMode 双请求；弹窗关闭后仍 setState |
| `pages/knowledge/components/SearchTab.tsx:63-67` | `fetchSearchHealth()`（挂载即拉） | 卸载后 setState |
| `pages/knowledge/components/SearchTab.tsx:70-86` | 自动检索 `searchKnowledge()` | 页面切换后 setState 竞态 |
| `pages/testcase/CaseDrawer.tsx:125-154` | `fetchDatasets({page_size:100})` + `loadReviewHistory()` | 同上 |

**手工补充**（扫描器盲区，异步函数被抽到 useCallback 内）：
- `pages/environment/index.tsx:106-108`：`useEffect(() => { if (selectedEnv) loadVars(selectedEnv.id) }, [selectedEnv, loadVars])` 无 cancelled 标志 —— 快速切换环境时旧环境的变量列表可能覆盖新环境（竞态）。

### P2-1 单页面挂载并行请求集过大

| 页面 | 挂载时请求 | 证据 |
|------|-----------|------|
| `pages/uitest/index.tsx` | `fetchScripts` + `fetchEnvironments` + `fetchTestCases({case_type:'ui',page_size:200})` + `fetchUiJobs`（+运行历史按需） | :240-246、:259-263、:265-274、:442 |
| `pages/testcase/index.tsx` | `fetchTestCases` + `fetchDomains` + `fetchTestCaseStats` + `fetchTaxonomy` | :118-132、:135-138、:140-143、:144-147 |
| `pages/integration/index.tsx` | `fetchIntegrations` + `fetchEnvironments` + `fetchRequirements` + `fetchTestCaseStats` | :132-135、:108-119、:151-156 |

其中 `fetchTestCases({page_size:200})` 属重型调用，共 3 处：`uitest/index.tsx:266`、`defect/DefectFormDialog.tsx:65`、`testcase/CaseDrawer.tsx:127`（后两处还叠加无 cleanup，见 P1-2）。

### P2-2 轮询有 cleanup、无退避

| 位置 | 间隔 | cleanup | 退避 |
|------|------|---------|------|
| `pages/dsh-tasks/index.tsx:81-85` | 3s 固定（仅 hasRunning 时） | ✅ `clearInterval` | ❌ |
| `pages/uitest/index.tsx:297-323` | 3s 固定（仅运行详情打开且 running/pending 时），双层 cleanup | ✅ | ❌ |
| `pages/special/index.tsx:131-139` | 1s × 60 次上限（页面已隐藏，仅作记录） | ✅ abort | ✅ 有次数上限 |

均为「有 cleanup、固定间隔、无指数退避」，影响为低；长任务期间每秒/每 3 秒空转请求可优化为退避或长轮询。

### P3-1 死代码 / 不可达页面

- `api/auth.ts:43-44` `fetchProjects()` 定义后全仓库 0 调用（页面直接用 `api.get('/projects')`）。
- `api/auth.ts:33-35` `fetchMe()`（`/auth/me`）定义后 0 调用。
- `pages/project/index.tsx`（533 行）—— 路由 `/project` 已重定向到 `/my-projects`（`router/index.tsx:221`），页面不可达但仍在维护。
- `pages/organization/index.tsx`（497 行）—— 路由 `/organizations` 重定向到 `/my-projects`（`router/index.tsx:203`），同上。
- `pages/my-projects/index.tsx:88,132` 绕过 api 模块直接 `api.get('/projects')`，未走 `fetchProjects()`、未走 cachedGet。

## A.3 专项核查（对应任务要求 4/5/6）

### (1) MainLayout 菜单加载 —— ✅ 不随路由切换重复请求

`layouts/MainLayout.tsx:217-237` 通过 `useAbortableEffect` 加载菜单，依赖数组为 `[isAuthenticated, menuRequest]`。React Router v8 嵌套路由下 MainLayout 是父级布局，子路由切换**不会重挂载**，因此 `/system/menus` 每次应用会话只请求 1 次（登录态变化或手动点「重新加载导航菜单」:323 时除外）。`useAbortableEffect`（`hooks/useAbortableEffect.ts:21-35`）用 `queueMicrotask + cancelled` 规避 StrictMode 双请求。**batch-147「menus×53」已修复**。唯一瑕疵是 `fetchMenus(signal)` 传 signal 绕过 cachedGet（`api/auth.ts:39`），整页刷新即重拉一次，影响可接受。

### (2) TabsContent / forceMount —— ✅ 无提前挂载

- 仅 `pages/knowledge/index.tsx:149-184` 使用 forceMount，且为「visitedTabs」模式：初始只挂载 URL 指定的当前 tab（:42），切过的 tab 才保持挂载（:44-47）。**不会**导致非活跃 tab 提前请求；相比 engineering-standards §4.4 的「forceMount + 条件渲染」，此模式还能保留已访问 tab 的滚动/输入状态。
- 其余 Tabs 使用点（`apitest/index.tsx:61-79`、`system/index.tsx:71-93`、`workbench/index.tsx:502-506`、`uitest/index.tsx:553/767`、`testplan/PlanDetail.tsx:472-649`、`defect/DefectDetailSheet.tsx:184-424` 等）未传 forceMount，依赖 Radix 默认「非激活即卸载」，同样不会提前请求。
- 反向问题：`pages/workbench/index.tsx:502` `<TabsContent value="project">{renderProjectOverview()}</TabsContent>` —— `renderProjectOverview()` 在渲染期被调用生成 JSX，但仅活跃 tab 会被 React 挂载子树，无实际请求泄漏。

### (3) 搜索/筛选防抖 —— ✅ batch-147「14键14请求」已修复

- `pages/testcase/index.tsx:517-538`：`keywordInput`（受控输入）与 `keyword`（提交值）分离，仅 Enter/按钮触发搜索，无逐键请求。
- `pages/requirement/index.tsx:149-152`：300ms `setTimeout` 防抖 + `clearTimeout` cleanup。
- `pages/knowledge/components/SearchTab.tsx:186-207`：Enter/按钮触发，无逐键请求。
- 全量扫描 `onChange` 直发请求仅命中分页 `special/index.tsx:515`（页面已隐藏）。

### (4) 页面切换请求取消 —— ✅ 大部分有 AbortController

`hooks/useApi.ts`（内部 AbortController + `controllerRef.abort()`，:66-74、:107-118、:146-148）与 `hooks/useAbortableEffect.ts`（:22-31）均已实现挂载/卸载取消；client.ts 响应拦截器对 `ERR_CANCELED` 静默处理（`client.ts:47-49`）。例外即 P1-2 的 4 处裸 useEffect。

### (5) 同一页面不同组件对同一 API 的重复调用（任务要求 2a）

未发现「同一挂载瞬间、同一 API 被两个组件并行请求」的直接重复（各 tab 组件随激活才挂载）。但存在**顺序重复**：apitest 的 3 个 tab 组件各自挂载时都拉 `/environments` —— `DebugTab.tsx:128`、`ApiDebugPanel.tsx:106`、`ApiCaseTab.tsx:83`；其中 ApiCaseTab 传 signal 绕过缓存，即使 60s 内重复进入「接口用例」tab 也会重新请求。

### (6) 静态数据应该用 cachedGet 却用 client.get（任务要求 2b）

除 P1-1 表格所列被 signal 绕过的调用点外，还有 3 个 api 层函数**完全未接入缓存**：
- `api/testcase.ts:63-65` `fetchTestCaseStats`（在 testcase、integration 页挂载各拉一次）
- `api/testcase.ts:67-72` `fetchTaxonomy`（在 testcase、mindmap 页各拉一次）
- `api/auth.ts:44` `fetchProjects`（未使用）

---

# 任务B —— PRD/手册与实际实现对照（甲方验收视角）

## B.1 「承诺 vs 实现」差异总表

| # | 文档承诺 | 文档位置 | 代码实际 | 代码位置 | 差异类型 |
|---|---------|---------|---------|---------|---------|
| 1 | 「Windows/macOS 完整步骤见 `docs/local-setup.md`」 | 手册:11、:51 | **引用路径歧义**：`test-platform-v2/docs/local-setup.md` 不存在（Test-Path=False），但**仓库根 `docs/local-setup.md` 存在**（Batch 152 创建，74 行）；手册相对路径从 test-platform-v2/docs/ 上下文解析失效；实际本地搭建脚本 `scripts/start-platform-environment.ps1` 存在 | 手册引用 vs 实际文件位置 | 🔴 手册引用的相对路径指向不存在的文件（文件实存于仓库根） |
| 2 | 前端技术栈「React 18.3 · TS 5.6 · React Router 6」 | 完整PRD:71、:100 | 实际 `react ^19.2.8`、`react-router ^8.3.0`（package.json:56,61）；现状PRD:41 与 README.md:51 已正确写 React 19.2.8 + Router 8.3.0 | package.json:56,61 | 🟡 完整PRD 技术栈过时（README 反而是新的） |
| 3 | 手册模块总览与验收清单声称「音视频专项」「性能监控」可用 | 手册:9、:35、:39、:269 | 路由已注释隐藏：`router/index.tsx:214-215`（special）、:234-235（perftest）；懒加载注释 :27-28、:43-44；访客目录也注释 :guestModuleCatalog.ts:83-86、:151-155。**页面不可达** | router/index.tsx:214-215、234-235 | 🔴 手册声称可用，实际入口已下线 |
| 4 | 手册 §6 音视频专项操作步骤（记录延迟/音画同步等） | 手册:150-161 | 页面存在（`pages/special/index.tsx` 740 行）但路由隐藏，用户无法进入 | router/index.tsx:214-215 | 🔴 操作手册与可达性矛盾 |
| 5 | 「进入'项目管理'，创建项目编码…」 | 手册:64 | 路由 `/project` 重定向到 `/my-projects`（`router/index.tsx:221`）；组织管理折叠进「我的项目」（:17-18 注释、:203 重定向） | router/index.tsx:221 | 🟡 手册入口名称过时（应为「我的项目」） |
| 6 | 「选择 OpenAPI URL、JSON/YAML **文件**或文本导入」 | 手册:107 | 导入对话框只有「URL 导入」「文本导入」两个 Tab，**无文件上传** | `apitest/components/ImportDialog.tsx:96-112` | 🟡 手册称支持文件导入，UI 无文件选择器 |
| 7 | 「对新增知识源执行切片和向量回填」 | 手册:94 | UI 只有「向量回填」按钮（SearchTab:109-117、209-225）与「验证」按钮（SourceListTab:150-155）；**无显式'切片'按钮**（切片随导入自动进行） | SearchTab.tsx / SourceListTab.tsx | 🟡 手册暗示手动切片步骤，UI 无对应操作 |
| 8 | 用例管理「无评审流、版本历史、Xmind 导入导出、批量操作」 | 完整PRD:252 | 代码已有：评审流 `reviewCase`/`fetchReviewHistory`（CaseDrawer.tsx:138,156-159）、版本 `fetchVersions`/`fetchVersionDetail`（VersionDialog.tsx）、Xmind 导入导出（index.tsx:160,177）、批量 `batchUpdateCases`/`batchDeleteCases`（index.tsx:94,95） | testcase 相关文件 | 🟡 完整PRD 现状描述严重滞后（现状PRD:211 已更新） |
| 9 | 测试计划「无批量执行」 | 完整PRD:273 | 代码已有 `executeAllCases`、`autoExecutePlan`、`triagePlanFailures`（PlanDetail.tsx:216,253；api/testplan.ts） | PlanDetail.tsx:216,253 | 🟡 同上 |
| 10 | API 测试「🧪 演示态，浏览器 fetch 直发，无后端/无落库」 | 完整PRD:327-335 | 后端真实 httpx 执行引擎 + 前端四 Tab（现状PRD:288-301 已更新为 🟡 真实执行） | apitest 全套 | 🟡 完整PRD 严重过时 |
| 11 | UI 自动化「⚠️ 随机数伪造」 | 完整PRD:339-348 | 真实 Playwright 子进程执行 + 产物收集（现状PRD:305-320 已更新） | uitest | 🟡 完整PRD 严重过时 |
| 12 | 音视频专项「⚠️ 随机数」 | 完整PRD:352-361 | 现状PRD:335 已更新为真实 ffprobe 样本链；但**前端入口已隐藏**（同 #3） | — | 🟡 完整PRD 过时 + 入口下线 |
| 13 | 缺陷管理「仅 open/resolved 雏形」 | 完整PRD:309-323 | 完整状态机 open→confirmed→fixing→pending_review→closed/rejected（DefectTransitionDialog.tsx、现状PRD:282） | defect 全套 | 🟡 完整PRD 过时 |
| 14 | 主题实验室 | 现状PRD:64（✅ 本地工具） | 路由存在但生产环境由 `isThemeLabEnabled` 门禁（`router/index.tsx:239-244` + `themeLabAvailability.ts:1-3`），生产返回「主题实验室未开放」Unavailable 页 | router/index.tsx:240-244 | ✅ 一致（手册未宣传，现状PRD 描述准确） |
| 15 | 项目管理路由 `/project` | 现状PRD:48 | 实际路由 `/project` 为重定向，入口是 `/my-projects` | router/index.tsx:221 | 🟡 现状PRD 路由列过时 |

## B.2 手册操作步骤抽查（接口测试 / 测试计划 / 缺陷管理 / 知识中心 / 环境管理）

| 模块 | 手册步骤 | 实际组件 | 结论 |
|------|---------|---------|------|
| 接口测试 §4.1 | 导入 OpenAPI → 预览（核对服务名/新增/重复数量）→ 确认 | ImportDialog 有「预览导入」按钮（ImportDialog.tsx:114-117），预览含数量 | ✅ 一致（除「文件」导入外，见 B.1#6） |
| 接口测试 §4.2 | 快速调试：选环境、填 URL/Header/Body、发送后看状态/业务状态/响应字段/耗时 | DebugTab（请求构建 + 响应查看） | ✅ 一致 |
| 测试计划 §7.2-3 | 选用例和环境发起执行；结果 pass/fail/skip/block；失败创建缺陷 | PlanDetail 有 executeCase/executeAllCases/autoExecutePlan + 失败分诊转缺陷（triagePlanFailures）；结果枚举与手册一致 | ✅ 一致 |
| 缺陷管理 §7.5 | 「按确认、修复、待验证、关闭等状态推进」 | DefectTransitionDialog + STATUS_MAP（confirmed/fixing/pending_review/closed） | ✅ 一致 |
| 知识中心 §3.2 | 「执行切片和向量回填」「向量健康：可用切片数应等于总切片数」 | 回填按钮在 SearchTab；向量健康栏显示 embedded_chunks/active_chunks 与覆盖率（SearchTab.tsx:150-164） | 🟡 部分一致（无显式「切片」按钮，见 B.1#7） |
| 环境管理 §2.2 | 创建 dev/test/staging/prod 环境；Token 等勾选「加密存储」；`${VAR}` 引用 | environment 页：createEnvironment(env_type) + createVariable(encrypted) + resolveVariables；ENV_TYPE_MAP 四类 | ✅ 一致 |

## B.3 文档与实现不一致清单（最小证据集）

1. 🔴 **`docs/local-setup.md` 引用路径歧义** —— 手册:11「Windows/macOS 完整步骤见 `docs/local-setup.md`」、手册:51「详见 `docs/local-setup.md`」；`test-platform-v2/docs/` 下无该文件（有 `perf-setup.md`、`onboarding.md`，无 local-setup），但**仓库根 `docs/local-setup.md` 存在**（Batch 152）——手册相对路径解析失效，读者按文档找不到文件。
2. 🔴 **音视频专项 / 性能监控「手册可用 vs 路由下线」** —— 手册:9,35,39,150-161,269 声称存在；`router/index.tsx:214-215`（special）、`234-235`（perftest）为注释路由；`guestModuleCatalog.ts:83-86,151-155` 同步注释。
3. 🟡 **完整PRD 技术栈过时** —— `CamelTv测试平台-完整PRD.md:71,100` 写「React 18.3 · React Router 6」；实际 `package.json:56,61` 为 React 19.2.8 / Router 8.3.0；`现状功能PRD.md:41`、`test-platform-v2/README.md:51-52`、`frontend/README.md:13-17` 均为新版本号。**README 与 package.json 一致 ✅**（仅完整PRD 过时，且完整PRD:94 自己还标注「README 称 Ant Design 5 已过时」，说明该文档长期未同步）。
4. 🟡 **完整PRD 模块成熟度整体滞后** —— 模块 6/7/10/11/12/13 现状描述与代码不符（见 B.1#8-#13）；现状功能PRD 已同步，建议验收时以「现状功能PRD + 实际路由」为准。
5. 🟡 **手册「文件导入」无对应 UI** —— 手册:107 vs `ImportDialog.tsx:96-112`（仅 URL/文本两 Tab）。
6. 🟡 **入口命名** —— 手册:64「项目管理」vs 实际入口「我的项目」（`router/index.tsx:221` 重定向）。
7. 🟡 **现状PRD 路由列** —— 现状PRD:48「/project」、:58「/special」、:62「/perftest」为旧路由，实际已重定向/隐藏（router/index.tsx:203,214-215,221,234-235）。

## B.4 技术栈一致性专项（任务要求 4）

| 声明来源 | 声明 | 与 package.json 比对 |
|---------|------|---------------------|
| `frontend/README.md:13-17` | React 19 · React Router 8 · shadcn/ui · Vite · TS | ✅ 一致 |
| `test-platform-v2/README.md:51-52` | React 19.2.8 + Router 8.3.0 + shadcn/ui(Radix+Tailwind) | ✅ 一致 |
| `CamelTv测试平台-完整PRD.md:100` | React 18.3 · Router 6 | ❌ 过时 |
| `现状功能PRD.md:41` | React 19.2.8 + Router 8.3.0 | ✅ 一致 |
| `package.json` | react ^19.2.8（:56）、react-router ^8.3.0（:61）、axios ^1.7.7（:48） | 基准 |

---

## 附录：方法与局限

- 方法：PowerShell + Node 静态扫描（`useEffect` 括号平衡提取、API 函数名计数、signal 传递链追踪）、关键文件人工通读、`Test-Path` 验证文档存在性。
- 局限：未运行 dev server 做 Network 面板实测（batch-147 的 53/6/4 数字来自当时实测，本次为静态推断请求次数）；部分「多计数」经核查为事件处理器多路径（如 `fetchRunDetail` 在 uitest 的 4 处分别对应轮询/选中/刷新按钮），未计为重复。
- 扫描脚本留存：`_review_tools/b173/scan-effects.cjs`。
