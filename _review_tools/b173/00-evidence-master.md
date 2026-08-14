# Batch 173 全平台对抗审查 — 证据总览（第一手实测数据）

> 审查日期：2026-08-14 | 生产环境：https://cameltv-test-platform1.vercel.app（Vercel 前端 + Railway 后端 v2.1.0 + Supabase PG）
> 账号：sportsadmin（超级管理员权限 `*`） | 项目：CamelTv 体育平台（id=1，另有 CAMELTV-VER=8 / C165WALK=9 / sports-live=10）
> 审查方式：真实浏览器 Playwright 全站遍历 + CRUD 实测 + API 直查 + 前后端源码静态审查（两份子代理深度报告）
> 证据目录：`_review_tools/b173/evidence/`（25 页截图/文本 + 网络请求日志 + 对话框结构）

---

## 1. 平台全景（实测快照）

- 25 个页面全部可达、初始加载 0 控制台错误、0 重复 GET（会话级缓存生效），加载耗时 2.4~4.1s/页
- 菜单 26 项：工作台/质量追溯/需求文档/版本测试任务/用例脑图/用例服务/测试计划/接口测试/UI 自动化/Playground/定时任务/报告中心/系统管理/我的项目/缺陷管理/测试数据集/集成配置/通知配置/目标环境/Agent 工作台/DSH 任务/蓝湖证据包/知识中心/运维发布控制 + 主题实验室
- 已隐藏路由（代码注释）：音视频专项 /special、性能监控 /perftest、项目管理 /project、组织 /organizations（重定向）
- 生产数据：用例 8984（功能 8528 / 接口 71 / UI 385）、测试计划 11、缺陷 8、报告 5、环境 3、数据集 4、通知渠道 2、定时任务 4、发布包 4、知识源 91、图谱实体 989、蓝湖任务 6（2 成功 4 失败）、UI 任务 10（2 个重复）、接口资产 899（7 服务 45 页）

## 2. 统计口径矛盾（实测 API 直查）

| 指标 | 工作台 dashboard/stats | 追溯 trace/coverage | 集成模块联动 | 需求页 |
|------|----------------------|--------------------|--------------|--------|
| 用例总数 | 8984 | 8984 | 8984 | — |
| 通过率 | **9.1%**（execution_pass=731 / execution_total=8024） | **22.1%**（729/3303） | — | — |
| 计划覆盖率 | — | 36.8%（3303/8984） | — | — |
| 需求覆盖率 | — | **33.3%**（2/6） | **67%** | **0%**（"选择文档查看"） |
| 已联动用例 | — | — | 1157（13%） | AI 导入用例 1157 |

**矛盾点**：
1. 通过率 9.1% vs 22.1%——分子 731 vs 729 都不一致，分母 8024（执行记录数）vs 3303（执行用例数）口径完全不同
2. 需求覆盖率 0% / 33.3% / 67% 三处三个数
3. 用例执行总数 8024 vs 3303：dashboard 统计所有执行记录（含重跑），trace 统计用例维度
4. 接口用例通过率 1.1%（4/363）、失败 359 条——历史失败执行记录大量残留

## 3. 功能 CRUD 实测结果（生产真实操作）

| 模块 | 操作 | 结果 | 证据 |
|------|------|------|------|
| 用例服务 | 新建（标题/前置/步骤/预期/域/模块） | ✅ POST 200，dialog 关闭，搜索可见 | 11-verify.js |
| 用例服务 | 搜索（回车触发） | ✅ 结果行=1 | 同上 |
| 用例服务 | 删除（图标按钮→确认对话框） | ✅ DELETE 200 | 12-trace-delete-plan.js |
| 用例服务 | 表单必填校验 | ✅ 5 项（标题/域/模块/步骤/预期）清晰提示 | 08-dialog-probe.js |
| 测试计划 | 新建（名称必填） | ✅ POST 200 | 13-plan-bug-verify.js |
| 测试计划 | 删除 | ✅ DELETE 200 | 14-cleanup.js |
| 缺陷管理 | 新建（标题+处理人可选） | ✅ POST 200，assignee 默认"未指定"不崩溃（147 已修复） | 16-defect-module.js |
| 缺陷管理 | 详情查看 | ✅ | 同上 |
| 缺陷管理 | **删除** | ⚠️ **有删除入口但是裸图标按钮**：行内第4个按钮为 alert-dialog-trigger（无文本无 aria-label），点击弹出"确定删除此缺陷？"确认框——删除能力对辅助技术不可见（UI 报告对抗性修正：前轮"无删除入口"结论错误，来源 DefectTable.tsx:151-176） | 36/37-defect-del-*.js |
| 缺陷管理 | 删除缺陷后知识切片 | ❌ **残留**（status=deprecated 未清理，缺陷已删但知识源 id=113 仍在知识中心"项目知识"tab 可见） | 25-env-knowledge-guest.js / 30-knowledge-residue.js |
| 环境管理 | 新建/删除 | ✅ POST/DELETE 200 | 17/18/25 |
| 接口测试 | 4 tab 切换 | ✅ 但 environments/datasets 每次切换重复请求（各 2 次） | 15-apitest-module.js |
| 系统管理 | 用户/角色/审计/Token/邀请码 5 tab | ✅ 全部正常 | 20/21/22 |
| Agent 工作台 | 执行对话框 | ✅ 7 种 Agent 均可执行；DSH 执行显示"暂不可用" | 21-probe-extra.js |
| UI 自动化 | 新建任务对话框 | ✅ 脚本/浏览器/关联用例/定时齐全 | 同上 |
| 报告中心 | 生成报告对话框 | ✅ 计划选择+门禁 | 19-more-modules.js |
| 定时任务 | 新建调度 | ✅ cron 提示+计划/环境选择 | 17-modules.js |
| 通知/集成 | 渠道/连接配置 | ✅ 对话框正常；外部集成 0 配置 | 同上 |

## 4. UI/UX 对抗审查发现（DOM 层 + 内容层）

### P1 级
- **UI-01 无文本按钮 a11y 缺失**：报告页 10 个、缺陷页 16 个、通知页 8 个 `button` 无文本且部分无 aria-label（alert-dialog-trigger 删除按钮）；用例/计划/UI 任务行内图标按钮有 aria-label（✅），但 report/defect/notify 的缺失
- **UI-02 用例内容数据质量**：生产用例正文数字被错误拆分，如「假设上限 2、1 3、0 4、0 5、0 6、」「latestVersion= 2、0」——AI 生成的用例中数字被插入顿号拆行，大量用例受影响（搜索"2、0"可复现多行），直接影响用例可读性与执行可操作性
- **UI-03 UI 任务列表重复数据**：10 条任务中「[Playground] 横幅广告-多广告按权重顺序轮播」「[Playground] 开屏广告-展示进行中的开屏广告」各出现 2 条（完全重复），无去重/幂等提示
- **UI-04 统计口径多套并存**（见 §2）：同一项目三处看到不同通过率/覆盖率，用户无法信任数据
- **UI-05 需求页「交互覆盖缺口」2217 条弱分页**：有 50 条/页分页（45 页）但无跳页、URL 未解码、首页被"首页"入口占满（UI 报告修正：前轮"无分页"结论错误，InteractionGapPanel.tsx:87-88 有 GAP_PAGE_SIZE=50）

### P2 级
- **UI-06 用例「所属域」下拉 100+ 项扁平列表无搜索**：域选择器列出全部域/模块（用户端/运营后台/接口测试/APP-版本更新/UGC…100+ 项），无分组搜索，选择效率低
- **UI-07 环境页长变量值无换行**：PROD_ALLOWED_HOSTS 一长串域名溢出单元格
- **UI-08 蓝湖证据任务失败无清理**：6 任务中 4 个失败（#30/#29/#26 会话失效、#26 页面发现失败），界面仅"重试"，无删除入口
- **UI-09 报告模板列为"—"**：5 份报告模板全空（生成时未选，可接受但无默认模板引导）
- **UI-10 角色管理/邀请码 tab 初始渲染空白**：点击后需等待 2-3s 才有数据（无骨架屏）
- **UI-11 DSH 任务页显示「DSH 服务未启用」但菜单/新建按钮可见**：进入后新建任务可点但提交必然失败（无禁用引导）
- **UI-12 运维发布控制页"未启用"占位**：整页仅提示无数据源，无隐藏或配置引导

### P3 级
- UI-13 缺陷严重程度显示「P0-致命」等中文标签 vs 编号列「P1-严重」混用两种风格
- UI-14 追溯页轴标签「功能/接口/自动化」与域命名体系（用户端/xxx、运营后台/xxx、接口测试/xxx、以及无前缀的裸域如「UGC」「广告」）混排，域体系不统一
- UI-15 发布包列表 15.0.0 活跃包 0 模块 0 页面（空壳）
- UI-16 页面纵向溢出（滚动）普遍存在（多为正常滚动）；无横向溢出 ✅

## 5. 前后端请求冗余（实测 + 源码）

### 实测
- 25 页初始加载：无重复 GET（cachedGet 生效 ✅）
- apitest 模块切 tab：`/environments` ×2、`/datasets` ×2（tab 组件各自挂载绕过缓存）
- 用例搜索：回车/按钮触发，无逐键请求 ✅（防抖已修复）
- menus：会话级仅 1 次 ✅

### 源码（前端子代理报告 report-arch-frontend.md）
- **P1-1 cachedGet 被 AbortSignal 系统性绕过**：全仓 cachedGet 仅 3 调用点；fetchEnvironments/fetchDomains/fetchMenus 等 10+ 处传 signal 走裸 client.get → 60s 缓存失效，跨页重复请求复发（apitest 3 tab 各拉 environments）
- **P1-2 4 处异步 useEffect 无 cleanup**：DefectFormDialog.tsx:61-81、SearchTab.tsx:63-67/70-86、CaseDrawer.tsx:125-154；另有 environment 页环境切换竞态
- **P2-1 挂载并行请求集过大**：uitest/testcase/integration 各 4-5 请求含 page_size=200 重型调用
- **P2-2 轮询无退避**：dsh-tasks 3s、uitest 3s 固定间隔
- **P3 死代码**：fetchProjects/fetchMe 0 调用；project/、organization/ 页面不可达仍维护；5 个 >800 行超大页面（最大 AiResultModal 1424 行）

## 6. 后端架构发现（子代理报告 report-arch-backend.md）

### P0
- **ARCH-01 API 批量任务双 Worker 竞态 + 僵尸任务**：APScheduler 轮询（task_worker.py:53-62）与 api_task_worker 守护线程（:290-316）并行认领；task_worker.py:82 认领后重查 `status not in ("pending",)` 直接 return → 任务永久卡 running 且无 stale 回收
- **ARCH-02 认领非原子（TOCTOU）**：api_task_worker.py:46-58 SELECT→UPDATE→commit 无 FOR UPDATE/SKIP LOCKED，PG 双 worker 可重复认领
- **ARCH-03 计划执行单长事务**：execute_all_cases（:924-1119）/auto_execute_api_cases（:465-610）整个计划一个事务末尾 commit，数百条用例挂数分钟锁行，且被 APScheduler 线程调用阻塞 cron

### P1
- **ARCH-04 执行记录双轨**：同一计划 API 执行同时写 test_execution 与 api_execution_task_item 两张表双向互指；report_aggregator 与 trace/dashboard 读不同表 → 统计分裂（与 §2 呼应）
- **ARCH-05 环依赖仅靠 lazy import 压制**：requirement_service ↔ test_case_service 双向；8 处跨服务私有符号直接引用（_row_to_dict/_call_llm_sync 等）
- **ARCH-06 UI 执行三套入口并存**：ui_runner_queue + task_worker 轮询 + open_api.py 裸线程
- **ARCH-07 6 套各自为政的认领式任务队列**：API/AI/DSH/证据包/Agent/UI run 各写一套
- **ARCH-08 9 套调度/执行机制并存**（APScheduler/轮询线程/守护线程/线程池/裸线程/BackgroundTasks…）
- **ARCH-09 状态机不一致**：test_execution 用 pass/fail/skip，api_execution_task_item 用 passed/failed/skipped，ui_test_run 用 done/fail——同事实 4 套取值
- **ARCH-10 同步长任务端点残留**：知识图谱 extract/evolve、计划 execute-all 默认同步、接口批量生成——无 async 覆盖；`_in_new_session` 命名误导

### P2
- **ARCH-11 权限码双份维护**：seed.py 目录 vs 路由内联 ~344 处，无共享常量无 CI 校验（本次核对 96 码无漂移但风险在）
- **ARCH-12 软删除三套语义**：is_deleted 布尔 / status=deprecated / 硬删除并存
- **ARCH-13 重复端点**：DELETE /test-cases/batch 与 POST /test-cases/batch-delete 函数体逐行相同；计划 execute-all/auto-execute/batch-execute 三端点语义重叠；报告 gate 双端点
- **ARCH-14 超大路由文件**：knowledge.py 68KB/1668 行且路由内直连 ORM；9 个路由 >20KB
- **ARCH-15 无 statement_timeout**；`soft_delete_status` 死代码；TestSchedule.job_id 多态外键

## 7. 文档/承诺 vs 实现（甲方验收视角，前端子代理报告）

- **DOC-01 🔴 手册引用 local-setup.md 路径歧义**：使用手册:11、:51 引用「Windows/macOS 完整步骤见 docs/local-setup.md」，文件**实际存在**于仓库根 `docs/local-setup.md`（Batch 152 创建，74 行，含一键启动/手动启动/首次登录/常见问题），但从 `test-platform-v2/docs/` 相对上下文解析会指向不存在的 `test-platform-v2/docs/local-setup.md`——手册引用未标注基准目录
- **DOC-02 🔴 手册声称可用的音视频专项/性能监控路由已隐藏**：手册:9,35,39,150-161,269 声称可用；router/index.tsx:214-215（special）、234-235（perftest）已注释 → 手册与可达性矛盾
- **DOC-03 🟡 完整PRD 技术栈过时**：React 18.3/Router 6 vs 实际 19.2.8/8.3.0；模块成熟度描述严重滞后（演示态→真实引擎已多次迭代）
- **DOC-04 🟡 手册「OpenAPI 文件导入」无对应 UI**：手册:107 称支持 JSON/YAML 文件，实际 ImportDialog 仅 URL/文本两 Tab
- **DOC-05 🟡 手册「项目管理」入口名过时**：手册:64 称「项目管理」，实际路由 /project 重定向 /my-projects
- **DOC-06 🟡 手册「切片和向量回填」无显式切片按钮**：切片随导入自动，UI 无对应操作
- **DOC-07 🟡 现状PRD 路由列过时**：/project、/special、/perftest 为旧路由

## 8. 测试数据清理记录（生产安全）

- 创建并已删除：B173TMP-验证入库-952908（用例）、B173TMP-计划复验-56313（计划 #18）、B173TMP-缺陷-状态流转验证-80044（缺陷 #14，API 删除）、B173TMP-环境-59499（环境 #6）
- **遗留**：缺陷删除后知识切片残留（knowledge source id=113，status=deprecated）——本身就是发现 ARCH/UI 问题
- 未改动任何既有生产数据；仅执行了读操作 + 上述临时数据（均已清理）

## 9. 关键问题根因链

1. 统计矛盾根因：执行记录双轨（ARCH-04）→ 各统计服务读不同表 → dashboard/trace/report 口径分裂（UI-04）
2. 僵尸任务根因：双 worker 认领（ARCH-01/02）→ API 批量任务卡 running → 用户看到任务永不结束 → 计划执行不可信
3. 长事务根因：单事务全计划执行（ARCH-03）→ 生产库 statement timeout/锁等待 → 批量执行失败 → 用户只能单条执行
4. 文档矛盾根因：路由隐藏（batch-165 用户指定隐藏专项/性能）未同步手册与 PRD
5. 请求冗余根因：cachedGet 缓存与 AbortSignal 不兼容的设计约定（client.ts:101）
6. 用例内容质量问题根因：AI 生成（或导入解析）时数字格式化/列表解析错误 → 2、0 样式
