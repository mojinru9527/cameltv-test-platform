# Batch 173 — 全平台四视角深度对抗审查问题落地修复文档

> **来源**：Batch 173 四视角深度对抗审查（UI设计/测试工程师/架构师/甲方验收 × 生产环境真实使用 + CRUD 实测 + 网络捕获 + 前后端源码审查）
> **日期**：2026-08-14 | **用途**：下版本全面修复的输入清单（可直接拆分多个修复批次）
> **生产环境**：`https://cameltv-test-platform1.vercel.app`（Vercel 前端 + Railway 后端 v2.1.0 + Supabase PG）
> **审查项目**：CamelTv 体育平台（用例 8984 / 计划 11 / 缺陷 8 / 接口资产 899）
> **配套**：四份视角报告（`_review_tools/b173/report-*.md`）+ `docs/平台功能流转与数据流转-四视角深度审查173.xmind` + `_review_tools/b173/evidence/`
> **与 Batch 127 差异**：127 为清单式浅层走查（逐模块截图+问题列表）；173 为对抗性深度审查（CRUD 实测、渲染层 bug 定位到源码行、架构机制级证据、统计口径 API 直查对比）

---

## 1. P0 阻断（下一版本必须修复）

| ID | 模块 | 问题 | 根因（文件:行号） | 修复建议 | 验收标准 |
|----|------|------|------------------|---------|---------|
| FIX-173-P0-01 | 接口测试/批量执行 | **API 批量任务双 Worker 竞态 + 认领后僵尸任务**：任务永久卡 running 无结果；**生产有用户可见实例**：UI 任务 #5「15.0.0-上线核心路径回归-UI」与 #6「16.0.0-开发页面验收-UI」自 2026-08-12 08:10 创建后持续 running 超过 48 小时（实测 /api/v1/ui-tests） | `task_worker.py:53-62,81-82`（APScheduler 每5s轮询）+ `api_task_worker.py:290-316`（守护线程每2s）并行认领；`:82` 认领后重查 `status not in ("pending",)` 直接 return（claim 先置 running 再调 _run_api_task，**必然僵尸**而非偶发） | ① 收敛为单一 worker（保留 api_task_worker，task_worker 移除 API 分支）；② 删除 :82 僵尸守卫或改为校验 locked_by；③ api_execution_task 增加 stale 回收（心跳超时置 failed，仿 scheduler.py:292）；④ 清理生产存量僵尸任务 #5/#6 | 批量任务 100% 到达终态；连续创建 10 任务无卡 running；存量僵尸任务被回收 |
| FIX-173-P0-02 | 接口测试/批量执行 | **认领非原子（TOCTOU）**：PG 下双 worker 可重复认领同一任务 | `api_task_worker.py:46-58` SELECT→UPDATE→commit 无 `FOR UPDATE`/`SKIP LOCKED`（对比 scheduler.py:34 正确范式） | 认领改 `UPDATE ... WHERE status='pending' ... FOR UPDATE SKIP LOCKED RETURNING id`（PG 方言）/ SQLite 退化为单线程 + BEGIN IMMEDIATE | 双 worker 并发下同一任务仅执行一次 |
| FIX-173-P0-03 | 测试计划/执行 | **计划执行单长事务**：整个计划所有用例一个事务末尾 commit，数百用例挂数分钟锁行；被 APScheduler 线程调用阻塞 cron | `test_plan_service.py:924-1119`（execute_all_cases）、`:465-610`（auto_execute_api_cases）单事务；scheduler.py:127 直接调用 | ① 逐用例独立短事务（结果落 test_execution 立即 commit）；② 或整体改走 api_execution_task 队列（trigger_type=plan 已有雏形 :856-890）；③ execute_all_cases 从 APScheduler 线程挪到独立执行线程 | 325 条用例批量执行 10 分钟内完成；执行期间计划页可正常刷新；cron 不阻塞 |
| FIX-173-P0-04 | 用例服务/渲染 | **用例内容渲染 bug：正文数字被拆行编号**（"假设上限 2、1 3、0 4、0" 实为 10000；"latestVersion= 2、0" 实为 6.0.0），大量 AI 生成用例展示失真，直接影响用例可读性与执行可操作性 | `frontend/src/pages/testcase/caseListFormatters.ts:59` 启发式分割正则 `/(?=\d+\s*[、.．)）])/g` 把正文中"数字+右括号/点号"误判为列表分隔符；数据层正常（API 返回原始文本） | ① 正则收紧：仅在**行首**数字前缀处分割（`/^\d+\s*[、.．)）]/m` 多行模式），正文中数字不拆分；② 增加回归单测：含 "10000）"、"6.0.0"、"2.0" 文本不被拆；③ 全量扫描受影响用例（搜索"、0"模式）确认存量影响范围 | 用例列表/详情中"假设上限10000"完整显示；单测覆盖数字+标点场景 |

## 2. P1 必改（复验项）

| ID | 模块 | 问题 | 根因 | 修复建议 |
|----|------|------|------|---------|
| FIX-173-P1-01 | 统计/追溯/报告 | **"通过率"同名不同口径且无标签区分**：工作台 9.1%（执行记录维度 731/8024，含重跑）vs 追溯 22.1%（用例维度 729/3303）；分子 731 vs 729 不一致；需求覆盖率 0%（页面"选择文档查看"）/ 33.3%（追溯）/ 67%（集成页）三处三个数 | 执行记录双轨：`test_plan_service.py:521-544,1046-1079` 同一执行双写 test_execution 与 api_execution_task_item；`report_aggregator.py:40,94` 只读 task/run 表 vs `trace/dashboard` 读 test_execution；batch-149 收敛的是"用例总数"层面，执行/覆盖率维度仍分裂 | ① 确定唯一执行事实源（建议 api_execution_task_item/ui_test_run），test_execution 收敛为轻量索引；② statistics_service 成为唯一聚合入口，report_aggregator/trace/dashboard/集成页全部改调；③ UI 上"通过率"按维度明确标注（执行记录口径/用例口径），避免同名歧义；④ 需求覆盖率三处统一（0/33.3/67 需对账） |
| FIX-173-P1-02 | 全局/请求层 | **cachedGet 被 AbortSignal 系统性绕过**：静态数据（environments/domains/menus）跨页重复请求（实测 apitest 切 tab environments×2）；batch-147 冗余问题部分复发 | `client.ts:101` 约定"传 signal 直接走 client.get"；api 模块 10+ 处按此约定传 signal 绕过缓存；cachedGet 全仓仅 3 调用点 | cachedGet 支持 signal：传 signal 也命中缓存，仅未命中时发起可取消请求（内部维护 in-flight AbortController 集合，abort 只移除订阅不取消共享请求）；静态数据统一接入缓存+失效策略 |
| FIX-173-P1-03 | 全局/前端 | **4 处异步 useEffect 无 cleanup + 1 处环境切换竞态**（违反 engineering-standards §4.1） | `defect/DefectFormDialog.tsx:61-81`、`knowledge/SearchTab.tsx:63-67,70-86`、`testcase/CaseDrawer.tsx:125-154`；`environment/index.tsx:106-108` 切换竞态 | 全部补 cancelled 标志/AbortController；environment 页 loadVars 加竞态守卫 |
| FIX-173-P1-04 | 缺陷管理 | **缺陷删除按钮为无文本无 aria 的裸图标按钮**（行内第 4 个按钮，alert-dialog-trigger，a11y 不可见——DOM 审计 16 处无文本按钮即此；点击会正常弹出"确定删除此缺陷？"确认框）；**已删缺陷知识切片残留**（删除后 knowledge source status=deprecated，仍在知识中心"项目知识"tab 用户可见，source id=113） | `DefectTable.tsx:151-176` 裸图标按钮未加 aria-label；`defect_service.py:244` 级联知识清理仅标记 deprecated 未隐藏/删除 | ① 删除按钮补 aria-label/文本（IconButton 封装）；② 删除缺陷时级联清理知识切片（硬删或隐藏）；③ 清理存量残留（source id=113 等） |
| FIX-173-P1-05 | 文档 | **手册引用 local-setup.md 路径歧义**（手册:11,51 写 `docs/local-setup.md`，文件实际在仓库根 `docs/local-setup.md`，从 test-platform-v2/docs/ 上下文解析会指向不存在的路径）；手册声称音视频专项/性能监控可用但路由已隐藏（DOC-02）；完整PRD 技术栈/模块成熟度严重过时（DOC-03） | 手册内相对路径未标注基准目录（batch-152 已创建根 docs/local-setup.md，但手册引用与文件位置不一致）；路由隐藏（batch-165）未同步手册 | ① 手册引用改为显式路径 `../../docs/local-setup.md`（或直接链接到仓库根）；② 手册与路由对齐（隐藏模块标注"已下线"）；③ 完整PRD 技术栈更新 React 19.2.8/Router 8.3.0，模块状态同步现状PRD |
| FIX-173-P1-06 | 执行引擎 | **执行记录双轨 + 状态机 4 套取值**：同一执行写两张表，pass/passed/done/completed 混用 | `test_plan.py:85` api_task_id + `api_asset.py:109` test_execution_id 双向互指；四表状态值不同 | 统一状态枚举（pending/running/passed/failed/skipped/cancelled）；废弃双写中非必要一方；前端 status_map 收敛 |
| FIX-173-P1-07 | 接口测试/用例化 | **接口资产 899 仅 71 条用例（3.8%）**：自动化覆盖严重不足 | 无批量生成引导，仅手动逐条 | 一键按服务/模块批量生成用例（GET 只读优先）；生成后展示计划与去重 |
| FIX-173-P1-08 | UI 自动化/Playground | **Playground 回写 UI 任务全部"未绑定"环境 → 永远无法执行**（4 个 [Playground] 任务实测目标环境=未绑定、状态=待执行）；回写无幂等 → 同 (case_id, spec) 重复建任务（实测横幅广告/开屏广告各 2 条重复） | `playground_service._write_spec_as_ui_job`（:413-440）创建 UiTestJob 未传 environment_id（:427-433），且每次调用无脑新建无查重 | ① 回写时绑定默认环境（缺省取项目默认/最近使用）；② 创建前按 (case_id, spec) upsert/查重；③ 清理存量 4 条未绑定任务与 2 条重复任务 |

## 3. P2 应改（体验与完整性）

| ID | 模块 | 问题 | 修复建议 |
|----|------|------|---------|
| FIX-173-P2-01 | 接口测试/UI 自动化 | UI 任务列表 2 条完全重复数据（横幅广告/开屏广告各 2 条），无幂等/去重提示 | 创建任务前查重提示；清理存量重复 |
| FIX-173-P2-02 | 需求 | 交互覆盖缺口 2217 条弱分页（50/页无跳页、URL 未解码、首页被"首页"入口占满），无 P0 优先 | URL decode + 按模块分组折叠 + 跳页分页 + P0 优先排序筛选 |
| FIX-173-P2-03 | 用例 | "所属域"下拉 100+ 项扁平列表无搜索 | 分组（用户端/运营后台/接口测试）+ 搜索过滤 |
| FIX-173-P2-04 | 蓝湖证据包 | 失败任务（#30/#29/#26）无删除入口，仅重试 | 补删除/归档入口 + 失败原因可读 |
| FIX-173-P2-05 | 执行引擎 | UI 执行三入口并存（ui_runner_queue + task_worker 轮询 + open_api 裸线程 :300-304） | 统一走 ui_runner_queue.enqueue_run |
| FIX-173-P2-06 | 架构 | 6 套各自为政的认领式任务队列（API/AI/DSH/证据包/Agent/UI run） | 收敛为统一 TaskQueue 基类（claim/execute/finish + locked_by/heartbeat） |
| FIX-173-P2-07 | 架构 | 权限码双份维护（seed.py 目录 vs 路由内联 ~344 处）无 CI 校验 | 新建 app/core/permissions.py 常量；CI pytest 比对路由引用与 seed 目录 |
| FIX-173-P2-08 | 架构 | 软删除三套语义并存（is_deleted/status=deprecated/硬删） | 统一 is_deleted；清理 `== False` 3 处写法 |
| FIX-173-P2-09 | 架构 | 重复端点：DELETE /test-cases/batch vs POST /batch-delete（函数体相同）；计划 execute-all/auto-execute/batch-execute 三端点；报告 gate/gate/check 双端点 | 各收敛为一个（其余 deprecated/410） |
| FIX-173-P2-10 | 架构 | 9 个路由文件 >20KB（knowledge.py 68KB 路由内直连 ORM :675-693） | 按域拆分 + 路由层禁 ORM |
| FIX-173-P2-11 | 架构 | 无 statement_timeout；`_in_new_session` 命名误导；soft_delete_status 死代码 | PG 连接串加 statement_timeout=30000；改名/删死代码 |
| FIX-173-P2-12 | 定时任务 | 轮询无退避（dsh-tasks/uitest 3s 固定）；page_size=200 重型调用 3 处 | 指数退避；按需分页 |
| FIX-173-P2-13 | 环境 | 长变量值（PROD_ALLOWED_HOSTS）溢出无换行/tooltip | 单元格换行 + hover tooltip |
| FIX-173-P2-14 | DSH 任务 | "DSH 服务未启用"但新建任务入口可见可点 | 未启用时隐藏入口或禁用+引导 |
| FIX-173-P2-15 | 运维发布控制 | 未配置数据源整页占位无隐藏/配置引导 | 按环境隐藏或给配置引导 |
| FIX-173-P2-16 | 发布包 | 15.0.0 活跃包 0 模块 0 页面空壳；功能地图草稿 0/0 | 空壳清理或创建引导 |
| FIX-173-P2-17 | 系统管理 | 角色/邀请码 tab 初始空白无骨架屏 | 补加载态 |
| FIX-173-P2-18 | 需求 | 需求覆盖率显示 0%（选择文档查看）与追溯 33.3% 矛盾 | 口径统一（并入 P1-01） |
| FIX-173-P2-19 | UI 自动化 | 385 UI 用例 vs 10 任务体量不匹配；P0 用例 UI 化覆盖不足 | Playground 批量编译 + P0 优先建任务 |

## 4. P3 打磨

| ID | 问题 |
|----|------|
| FIX-173-P3-01 | 缺陷严重度标签风格混用："P0 致命"（DefectStatsCards.tsx:25 空格）vs "P0-致命"（constants.ts:7-10 连字符）vs 追溯图例"P0 缺陷"三套并存 |
| FIX-173-P3-02 | 缺陷统计卡维度混排：四卡=总数/严重度(P0)/状态(待处理)/状态(已解决)并列，3+7+1≠8 破坏可加性直觉 |
| FIX-173-P3-03 | 追溯轴标签中英混排（功能/接口/自动化 vs functional） |
| FIX-173-P3-04 | 域命名体系不统一（用户端/xxx、运营后台/xxx、接口测试/xxx、裸域五种范式并存） |
| FIX-173-P3-05 | 菜单三套命名体系（侧边栏/导航标签/模块标题不一致）；批次号泄漏进标题（C119-2/batch-166 等） |
| FIX-173-P3-06 | 报告模板列全为"—"（无默认模板引导） |
| FIX-173-P3-07 | 报告/缺陷/通知页无文本按钮 a11y（10/16/8 个；缺陷 16 个即删除裸图标按钮） |
| FIX-173-P3-08 | 死代码：fetchProjects/fetchMe 0 调用；project/、organization/ 页面不可达仍维护 |
| FIX-173-P3-09 | 5 个 >800 行页面（AiResultModal 1424/uitest 1072/requirement 1147/perftest 868/testcase 855） |
| FIX-173-P3-10 | 用例表格 10 列高密度全文直出，步骤/预期无法配对查看 |
| FIX-173-P3-11 | 环境变量长值 200px 截断仅悬停可看，触屏不可用、无复制按钮 |
| FIX-173-P3-12 | 知识中心"待审 AI 产物 11 / 未审核 11"重复计数；"已废弃知识源 0"与存量 deprecated 残留矛盾 |

## 5. 建议修复批次拆分（下版本）

| 建议批次 | 范围 | 承接 ID |
|---------|------|---------|
| Batch 174（P0 执行引擎） | 统一 Worker + 认领原子化 + 短事务 + stale 回收 | FIX-173-P0-01/02/03 |
| Batch 175（P0 渲染 + P1 统计） | 用例渲染 bug + 统计口径收敛（唯一事实源） | FIX-173-P0-04/01(P1-01) |
| Batch 176（P1 请求层） | cachedGet signal 语义 + useEffect cleanup + 轮询退避 | FIX-173-P1-02/03 |
| Batch 177（P1 缺陷/文档） | 缺陷删除+级联清理 + local-setup.md + 手册/PRD 对齐 | FIX-173-P1-04/05 |
| Batch 178（P2 体验） | UI 任务去重/缺口分页/域下拉搜索/蓝湖删除/加载态 | FIX-173-P2-01/02/03/04/17 |
| Batch 179（P2 架构收敛） | TaskQueue 统一/权限常量/软删统一/重复端点/路由拆分 | FIX-173-P2-06~11 |
| 持续（P3） | 打磨项 | FIX-173-P3-* |

## 6. 生产数据安全记录

- 写路径全部使用 `B173TMP-` 前缀临时数据，已清理：用例 B173TMP-验证入库-952908、计划 B173TMP-计划复验-56313（#18）、缺陷 B173TMP-缺陷-状态流转验证-80044（#14，API 删除）、环境 B173TMP-环境-59499（#6）。
- **遗留不可逆写入**：① 缺陷删除后知识切片残留 1 条（source id=113，status=deprecated）——已登记为修复项 P1-04 的存量清理目标；② 审计日志记录了本次审查的 plan:create/delete、case:delete 操作（属正常审查证据）。
- 未修改任何既有生产数据；全部查询/遍历为只读。

## 7. 复验证据索引

- 渲染 bug：`evidence/29-render-check.js`（API 10000 vs 渲染 2、1 3、0）
- 统计矛盾：`evidence/26-stats-compare.js` / `27-stats2.js`
- CRUD 实测：`evidence/07-case-crud-log.json` / `11-verify-log.json` / `12-trace-log.json` / `14-cleanup-log.json`
- 请求冗余：`evidence/15-apitest-log.json` / `09-testcase-load-requests.json`
- DOM 审计：`evidence/04-ui-audit.json`
- 后端架构：`report-arch-backend.md`（406 行，全部文件:行号证据）
- 前端架构/文档：`report-arch-frontend.md`（212 行）
