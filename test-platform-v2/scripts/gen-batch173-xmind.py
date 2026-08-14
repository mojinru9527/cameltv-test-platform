# -*- coding: utf-8 -*-
"""batch-173 生成《平台功能流转与数据流转-四视角深度审查173.xmind》"""
import json, zipfile, uuid, os

def nid():
    return str(uuid.uuid4())

def topic(title, note=None, children=None):
    t = {"id": nid(), "class": "topic", "title": title}
    if note:
        t["notes"] = {"plain": {"content": note}}
    if children:
        t["children"] = {"attached": children}
    return t

def sheet(title, root_children):
    return {
        "id": nid(), "class": "sheet", "title": title,
        "rootTopic": topic(title, children=root_children),
    }

def N(t, note=None): return topic(t, note)

root_children = []

# ============ 0 审查总览 ============
overview = [
    N("审查方法：四视角对抗（UI设计/测试工程师/架构师/甲方验收）× 生产浏览器深度使用 × CRUD实测 × 网络请求捕获 × 前后端源码审查", "batch-173，生产 cameltv-test-platform1.vercel.app，CamelTv 体育平台项目（sportsadmin），25 页全遍历 + 用例/计划/缺陷/环境 CRUD 实测"),
    N("平台全景：25 页可达 / 0 初始控制台错误 / 用例8984（功能8528/接口71/UI385）/ 计划11 / 缺陷8 / 报告5 / 环境3 / 接口资产899（7服务）/ 知识源91 / 图谱实体989", "evidence/03-summary.json + pages/*.txt"),
    N("统计口径矛盾（实测）：通过率 工作台9.1%(731/8024) vs 追溯22.1%(729/3303)；需求覆盖率 0% vs 33.3% vs 67% 三处三个数", "执行记录双轨（test_execution vs api_execution_task_item）根因，evidence/26-stats-compare.json"),
    N("P0 级新发现：①API批量任务双Worker竞态+认领后僵尸任务（task_worker.py:82）；②认领TOCTOU无锁（api_task_worker.py:46-58）；③计划执行单长事务阻塞cron（execute_all_cases:924-1119）；④用例内容渲染bug（数字被拆行，caseListFormatters.ts:59）"),
    N("P1 级：执行记录双轨/环依赖lazy压制/UI执行三入口/6套认领队列/cachedGet被signal绕过/4处useEffect无cleanup/文档3处硬伤（local-setup.md不存在等）/统计口径分裂"),
    N("主链路状态：需求✅→用例✅→计划✅(编排36.8%)→执行⚠️(通过率22.1%)→缺陷✅(前端无删除入口)→报告⚠️(27.1%均8/12生成)→统计❌(口径矛盾)→通知⚠️(渠道2条但外部集成0)"),
    N("交付结论：有条件通过（CONDITIONAL）——P0 四项 + P1 统计/请求层修复后复验；测试数据已清理（B173TMP 已删，缺陷知识切片残留1条）"),
]
root_children.append(topic("0 审查总览与问题热力图（batch-173）", children=overview))

# ============ 1 需求域 ============
req_flow = [
    N("功能流转：蓝湖链接/文件上传(.md/.docx/.xlsx) → 证据任务(采集/OCR/审核) → 需求文档(6) → AI提取(功能点/模块树) → AI生成用例(1157导入) → 生产差异标注(16.0.0) → 交互覆盖缺口(2217) → 评审/导入用例库", "实测：蓝湖任务6个(2成功4失败)；需求覆盖率显示0%；交互缺口2217条全量平铺无分页"),
    N("数据流转：LanhuEvidenceJob → LanhuEvidencePage/Asset(OCR) → RequirementDocument → RequirementModule → InteractionEdge(2217) → TestCase(source_doc_id) → 知识中心切片", "evidence/25-guest-home / pages/requirement.txt"),
    N("API：/lanhu-evidence/jobs /requirements /requirement-modules /interaction-coverage/gaps /test-cases/domains /ai-task/{id}", "证据任务失败无删除入口仅重试；蓝湖会话失效需手动更新Cookie"),
    N("问题（173）：①需求覆盖率 0%（页面）vs 33.3%（追溯）vs 67%（集成页）三口径；②交互缺口2217全量无分页无P0优先；③蓝湖失败任务#30/#29/#26无清理入口；④用例内容渲染bug影响AI生成用例可读性（数字拆分）", "UI-05/UI-08/统计矛盾"),
]
root_children.append(topic("1 需求域（需求文档/证据包/模块树/生产差异/交互缺口）", children=req_flow))

# ============ 2 用例域 ============
case_flow = [
    N("功能流转：用例库(8984: 功能8528/接口71/UI385) → 域/界面/模块/场景/优先级筛选 → 搜索(回车触发) → 新建/编辑(必填5项校验✅) → 评审/版本历史 → 导入(Excel/XMind) → 导出 → Playground批量编译→UI任务回写", "实测CRUD全通过：创建POST200/搜索✅/删除DELETE200；表单校验清晰（标题/域/模块/步骤/预期）"),
    N("数据流转：TestCase(domain/module/P0-3/type) ↔ TestCaseVersion ↔ TestCaseReview ↔ TestCaseTaxonomy(树) ↔ 计划(TestPlanCase 3303条) ↔ 知识图谱", "evidence/07-case-crud-log / 08-dialog-probe"),
    N("API：/test-cases /test-cases/stats /test-cases/taxonomy /test-cases/domains /test-cases/batch(batch-delete重复)", "批量删除双端点 DELETE /batch 与 POST /batch-delete 函数体相同（ARCH-13）"),
    N("问题（173）：①渲染bug——正文数字被拆行（'假设上限 2、1 3、0'实为10000），caseListFormatters.ts:59启发式分割误判；②所属域下拉100+项无搜索；③用例8984仅71接口+385UI（接口资产899仅3.8%用例化）；④统计口径（用例总数一致8984✅但执行统计分裂）", "UI-02/UI-06/ARCH-13"),
]
root_children.append(topic("2 用例域（用例库/分类树/评审/版本/导入导出）", children=case_flow))

# ============ 3 计划与执行域 ============
plan_flow = [
    N("功能流转：测试计划(11) → 编排用例(3303/8984=36.8%) → 环境选择 → 一键/批量/单条执行 → 失败分诊(triage) → 失败自动转缺陷/报告/通知(计划级开关) → 执行历史", "实测：计划新建POST200/删除DELETE200；11个计划进度多为0/N（0/405、0/2891、0/325未执行）；接口用例执行通过率1.1%"),
    N("数据流转：TestPlan → TestPlanCase(3303) → TestExecution(pass/fail/skip) ↔ ApiExecutionTaskItem(passed/failed) 双轨互指 → TestCase.last_run_status(3处写入口径不一)", "report-arch-backend.md §3.1/§3.5"),
    N("API：/test-plans /test-plans/:id/execute /execute-all /auto-execute /batch-execute（三端点语义重叠）/executions /triage", "ARCH-13 三执行端点收敛建议"),
    N("问题（173）：①P0 单长事务——execute_all_cases 整个计划一个事务末尾commit（:1119），数百用例挂数分钟锁行，且被APScheduler线程调用阻塞cron；②P0 双Worker竞态——APScheduler轮询+api_task_worker守护线程并行认领，task_worker.py:82认领后return致僵尸任务；③P0 TOCTOU——claim_next_task无FOR UPDATE，PG下重复执行；④统计分裂——dashboard(8024执行记录) vs trace(3303用例) 通过率9.1% vs 22.1%", "report-arch-backend.md §3.3/§6.2"),
]
root_children.append(topic("3 计划与执行域（计划/编排/执行/分诊/失败自动链路）", children=plan_flow))

# ============ 4 质量域 ============
quality_flow = [
    N("功能流转：执行结果 → 缺陷(8: 3致命/1严重P1/4) → 状态机(open→confirmed→fixing→pending_review→closed/rejected) → 报告(5份) → 追溯(链路口径) → 定时任务(4) → 通知(邮件+飞书webhook)", "实测：缺陷新建POST200✅/详情✅/编辑✅；前端无删除入口（API有DELETE）；缺陷删除后知识切片残留(deprecated)"),
    N("数据流转：TestExecution → Defect(severity/assignee/case_id) → DefectTransition/DefectComment → TestReport(通过率/门禁) → TraceStats → TestSchedule/ScheduleRun → NotificationChannel/Log", "evidence/16-defect-module / 18-trace2 / 25-env-knowledge"),
    N("API：/defects /defects/:id/transitions /reports /reports/:id/gate(gate/check双端点) /trace/coverage /trace/trend /schedules /notify/channels", "ARCH-13 报告gate双端点"),
    N("问题（173）：①统计口径5套并存（工作台9.1% vs 追溯22.1% vs 报告27.1% vs 集成页67%）；②缺陷前端无删除（甲方需清理历史数据时只能API）；③缺陷删除级联不彻底（知识切片残留status=deprecated）；④报告5份全在8/12生成——无日常自动生成；⑤报告模板列全为'—'；⑥定时任务4个（2个执行中1个停用1个API回归）", "UI-04/UI-09/统计矛盾"),
]
root_children.append(topic("4 质量域（缺陷/报告/追溯/定时/通知）", children=quality_flow))

# ============ 5 测试执行域 ============
exec_flow = [
    N("功能流转：接口资产(899/7服务/45页) → 快速调试(选环境/URL/断言) → 接口用例(71) → 执行任务(批量/取消/重试/curl/失败分析) → UI自动化(任务10/用例脚本) → Playground(编译/批量编译/回写UI任务) → 音视频专项(已隐藏) → 性能监控(已隐藏)", "实测：apitest 4 tab正常；environments/datasets每次切tab重复请求×2；UI任务10个中2个完全重复；DSH任务页'服务未启用'但菜单可见"),
    N("数据流转：ApiAsset(OpenAPI导入) → ApiTestCase(71) → ApiExecutionTask/Item ↔ TestExecution(双轨) → UiTestJob/UiRun(Playwright子进程) → PlaygroundSpec(generated/*.spec.ts) → XHR捕获", "evidence/15-apitest-module / 19-uitest-cases / pages/uitest.txt"),
    N("API：/apitest/api-assets /apitest/api-execute /test-cases/:id/execute /apitest/tasks /ui-automation/jobs /playground/compile /open_api(CI Token)", "apitest.py 37KB/977行超大路由文件；open_api.py:300-304裸线程执行UI"),
    N("问题（173）：①UI执行三入口并存（ui_runner_queue+task_worker轮询+open_api裸线程）；②接口用例71 vs 资产899（3.8%用例化，批量生成效率低）；③UI任务重复数据2条无幂等；④Playground用例与UI任务关联字段存在但映射不完整；⑤特殊/性能路由隐藏但手册仍声称可用（DOC-02）", "ARCH-06/UI-03/ARCH-10"),
]
root_children.append(topic("5 测试执行域（接口测试/UI自动化/Playground/专项）", children=exec_flow))

# ============ 6 资产域 ============
asset_flow = [
    N("功能流转：蓝湖证据包(采集109页/OCR) → 知识中心(12 tab: 概览/项目知识/平台研发/检索/知识源/AI审核台/图谱/实体/迭代/Wiki/差异/Skills) → 图谱(989实体) → AI审核台(11待审) → Agent工作台(7种: 需求分析/影响分析/用例生成/失败分析/Wiki编译/知识差异/平台知识 + DSH执行) → 知识差异对比", "实测：Agent执行历史10条全成功（最快5.9s最慢40.4s）；DSH执行'暂不可用'；知识中心91源/311切片/989实体/12次Agent执行/99%采纳率"),
    N("数据流转：LanhuEvidenceJob → KnowledgeSource(91) → Chunk(311) → Vector(嵌入) → Entity/Relation(989) → AiArtifact(审核) → AgentRun/QueueItem → WikiRawSource/Page/Link → 差异DiffTask", "evidence/20-probe-more / 21-probe-extra / pages/knowledge.txt"),
    N("API：/knowledge/overview /knowledge/sources /knowledge/graph/entities /knowledge/ai-artifacts /agents /agents/trigger /wiki/* /lanhu-evidence/*", "knowledge.py 68KB/1668行路由内直连ORM（ARCH-14）"),
    N("问题（173）：①已删缺陷的知识切片残留（source id=113 status=deprecated）；②12 tab切页部分全量重拉（visitedTabs模式✅但SearchTab useEffect无cleanup×2）；③知识图谱实体989 vs 用例8984映射有限；④knowledge.py超大路由+直连ORM；⑤AI产物置信度/审核链路待验证", "P1-2(前端)/ARCH-14/ARCH-12"),
]
root_children.append(topic("6 资产域（蓝湖证据/知识中心/图谱/AI审核台/Agent工作台）", children=asset_flow))

# ============ 7 交付域 ============
deliver_flow = [
    N("功能流转：发布包(4: 16.0.0开发验收草稿18模块/15.0.0上线回归活跃0模块/需求基线45模块43页/功能地图草稿0) → 版本全景(panorama) → 模块树构建 → 生产差异 → 回归范围/触发 → 运维发布控制(只读未配置)", "实测：发布包详情✅（16.0.0含广告模块树）；运维发布控制页显示'当前环境未启用发布控制数据源'占位"),
    N("数据流转：ReleaseBundle(版本号/状态) → RequirementModule(45/43) → VersionPanorama → 差异DiffBundle → 知识图谱ingestion写入 → ops发布事件(未配置)", "evidence/20-bundle-detail / pages/release-bundles.txt"),
    N("API：/release-bundles /release-bundles/:id/panorama /requirement-modules /ops/deployments", "release_bundles.py 23KB；version-mission 重定向到 release-bundles"),
    N("问题（173）：①15.0.0活跃包0模块0页面空壳；②'版本测试任务'菜单重定向冗余入口；③运维控制未启用但整页占位无隐藏/引导；④发布包与测试计划双向关联（batch-157）已有但UI展示分散", "UI-15/UI-12/DOC-05"),
]
root_children.append(topic("7 交付域（发布包/版本全景/模块树/运维控制）", children=deliver_flow))

# ============ 8 平台域 ============
platform_flow = [
    N("功能流转：我的项目(4: cameltv/CAMELTV-VER/C165WALK/sports-live) → 项目切换(顶部) → 环境(3: 生产/站点UI/Test5) → 变量(加密) → 系统管理(5 tab: 用户13/角色3/审计/API Token/邀请码1) → 通知渠道(2) → 集成配置(0外部) → 数据集(4) → DSH任务(未启用)", "实测：系统5 tab全部正常；角色3个(admin/tester/viewer)；审计日志记录了我本次操作的plan:create/delete与case:delete；邀请码1个掩码显示****F4PY"),
    N("数据流转：sys_organization(_member) → sys_project(_member) → Environment/EnvironmentVariable(加密) → SysUser/Role/Permission/AuditLog/ApiToken/InviteCode → NotificationChannel → IntegrationConfig → Dataset", "evidence/20-probe-more / 22-cleanup-defect / pages/system.txt"),
    N("API：/projects /my-projects /organizations /environments /system/users /system/roles /system/audit /system/tokens /notify/channels /integrations /datasets", "project/、organization/ 路由重定向到 my-projects（前端死代码仍维护）"),
    N("问题（173）：①前端无删除入口的模块：缺陷/蓝湖任务（API有）；②环境页长变量值溢出无换行；③角色/邀请码 tab 初始空白无骨架屏；④DSH任务页'服务未启用'仍展示新建入口；⑤API Token掩码显示'****F4PY'（仅尾部4位可见，设计合理✅）；⑥权限码双份维护无CI校验", "UI-07/UI-10/UI-11/ARCH-11"),
]
root_children.append(topic("8 平台域（项目/组织/环境/系统管理/通知/集成/数据集）", children=platform_flow))

# ============ 9 四者关联优化 ============
opt_flow = [
    N("目标模型：功能用例(P0锚点) ↔ 接口用例(绑定ApiEndpoint) ↔ UI用例(绑定spec) ↔ 测试计划(混合编排) → 执行回填 → 失败自动转缺陷/报告/通知 → 单一口径追溯", "用户核心诉求：用例/功能/接口/UI自动化四者高效关联"),
    N("现状断裂：①接口资产899仅71用例化(3.8%)；②UI任务与用例关联仅Playground批量回写(385 UI用例vs 10任务)；③计划仅编排3303/8984(36.8%)，11计划大多0执行；④执行结果3处写TestCase.last_run_status口径不一；⑤统计5套口径", "report-arch-backend.md §3.5/§4.2"),
    N("关联方案①：用例模型加双向引用——TestCase.api_endpoint_ids[] / TestCase.ui_spec_id / TestPlanCase 统一；接口用例由资产生成时自动挂功能用例映射；UI任务按用例生成spec并回写结果到用例", "batch-151 已有失败自动链路基础"),
    N("关联方案②：计划维度四类型混合编排+强制环境绑定+批次执行（短事务）；执行结果单一事实源（api_execution_task_item/ui_test_run）收敛test_execution；统计统一statistics_service唯一入口", "报告/追溯/工作台/集成页共用同一聚合视图"),
    N("关联方案③：一键生成扩量——按服务/模块批量生成接口用例(71→覆盖P0资产)；UI任务按P0功能用例批量创建；Playground成为批量编译通道", "接口资产899中GET只读资产优先自动化"),
    N("效率度量：批量执行成功率≥95%、单条P95<5s、AI提取fallback=0、接口用例化率≥50%、计划执行率≥80%、统计口径100%一致", "建议下版本验收指标"),
]
root_children.append(topic("9 四者关联优化（用例/功能/接口/UI自动化高效联动）", children=opt_flow))

# ============ 10 请求冗余优化 ============
req_flow = [
    N("现状（实测+源码）：25页初始加载无重复GET✅（cachedGet会话缓存生效）；apitest切tab environments/datasets各×2（signal绕过缓存）；menus会话级1次✅；搜索回车触发无逐键请求✅", "evidence/09-load-requests.json / 15-apitest-log.json"),
    N("P1-1 cachedGet被AbortSignal绕过：全仓cachedGet仅3调用点，fetchEnvironments/fetchDomains/fetchMenus等10+处传signal走裸client.get → 60s缓存失效跨页重复请求（apitest 3 tab各拉environments）", "report-arch-frontend.md A.2 P1-1"),
    N("修复方案①：cachedGet支持signal——传signal也命中缓存，仅缓存未命中时发起可取消请求（in-flight promise的AbortController集合，abort只移除订阅不取消共享请求）", "client.ts:101 约定修改"),
    N("修复方案②：静态数据(menus/environments/domains/taxonomy/stats)统一接入缓存+失效策略；引入SWR/React Query评估（缓存/去重/轮询/失效一体化）", "预计请求量降40-50%"),
    N("修复方案③：轮询指数退避（dsh-tasks/uitest 3s固定→1s/2s/4s/8s退避）；page_size=200重型调用按需分页；useEffect无cleanup 4处补齐（DefectFormDialog/SearchTab×2/CaseDrawer）", "P1-2/P2-1/P2-2"),
    N("修复方案④：删除死代码（fetchProjects/fetchMe 0调用）；project/organization页面路由清理；超大页面拆分（AiResultModal 1424行/uitest 1072行/requirement 1147行）", "P3-1"),
]
root_children.append(topic("10 前后端请求冗余分析与优化方案", children=req_flow))

# ============ 11 架构收敛 ============
arch_flow = [
    N("P0-1 统一任务队列：9套调度/执行机制收敛为单一TaskQueue基类（status+locked_by+heartbeat+retry），APScheduler只留一个2s轮询分发；删除task_worker._process_api_tasks与api_task_worker._processor_loop之一", "report-arch-backend.md §7-1"),
    N("P0-2 认领原子化：UPDATE...WHERE status='pending' FOR UPDATE SKIP LOCKED（PG）/BEGIN IMMEDIATE（SQLite）；修复task_worker.py:82僵尸守卫；api_execution_task加stale回收", "report-arch-backend.md §7-2"),
    N("P0-3 计划执行短事务：execute_all_cases逐用例独立Session短事务或整体任务化（trigger_type=plan）；从APScheduler线程挪出", "report-arch-backend.md §7-3"),
    N("P1-4 执行事实源唯一：api_execution_task_item/ui_test_run为机器可读事实源，test_execution收敛为计划维度轻量索引；四表状态值统一pending/running/passed/failed/skipped/cancelled；report_aggregator/trace/dashboard同源", "report-arch-backend.md §7-4"),
    N("P1-5 服务层边界：8处私有符号引用提升公共API；requirement_service↔test_case_service断环（validate_source_doc下沉）；权限码单点常量+CI校验；路由层禁ORM（knowledge.py:675-693）", "report-arch-backend.md §7-5/7/6"),
    N("P1-6 同步长任务异步化：知识图谱extract/evolve、execute-all默认async_mode、接口批量生成BackgroundTasks；statement_timeout=30000配置；_in_new_session改名", "report-arch-backend.md §7-9"),
    N("P2-7 模型规范化：软删除统一is_deleted；跨域引用补FK（TestCase.source_doc_id/ApiExecutionTaskItem.case_id/TestSchedule.job_id）；删除重复端点（batch/batch-delete、execute-all三端点、gate双端点）；soft_delete_status死代码移除", "report-arch-backend.md §7-8/10"),
    N("本地搭建（用户点名）：docs/local-setup.md 已存在（仓库根 docs/，Batch 152）但手册引用路径有歧义（test-platform-v2/docs 相对解析不到）；start-platform-environment.ps1 已支持-InstallDeps/-InitializeLocal✅；建议：Docker一键(compose已存在)、种子数据脚本、前端gen:api自动化、环境变量7份收敛统一入口", "report-arch-frontend.md B.1#1 / start-platform-environment.ps1 / docs/local-setup.md"),
]
root_children.append(topic("11 架构收敛与本地搭建优化", children=arch_flow))

sheets = [sheet("平台功能流转与数据流转-四视角深度审查173", root_children)]

# ============ 附加 sheet：问题清单总表 ============
issues = [
    N("P0-1 API批量任务双Worker竞态+僵尸任务", "task_worker.py:53-62,81-82 + api_task_worker.py:290-316 并行认领；:82认领后return致任务永久running无stale回收"),
    N("P0-2 认领TOCTOU无锁", "api_task_worker.py:46-58 SELECT→UPDATE→commit无FOR UPDATE；PG双worker重复执行"),
    N("P0-3 计划执行单长事务", "execute_all_cases:924-1119/auto_execute_api_cases:465-610单事务末尾commit；数百用例挂数分钟锁行；APScheduler线程调用阻塞cron"),
    N("P0-4 用例内容渲染bug（数字拆行）", "caseListFormatters.ts:59 正则/(?=\\d+\\s*[、.．)）])/g 把'10000）'拆分→'2、1 3、0'；数据层正常（API返回10000）渲染层失真；影响AI生成用例可读性"),
    N("P1-1 统计口径5套分裂（通过率9.1% vs 22.1%；需求覆盖率0/33.3/67%）", "执行双轨：test_plan_service.py:521-544,1046-1079双写；report_aggregator只读task/run表 vs trace/dashboard读test_execution；口径收敛为唯一统计服务"),
    N("P1-2 执行记录双轨", "TestExecution.api_task_id ↔ ApiExecutionTaskItem.test_execution_id 双向互指；四表状态值4套取值"),
    N("P1-3 环依赖lazy压制+8处私有符号跨模块引用", "requirement_service.py:789 ⇄ test_case_service.py:106；_row_to_dict/_call_llm_sync/_extract_lanhu_content等"),
    N("P1-4 cachedGet被AbortSignal绕过（请求冗余）", "client.ts:101约定；10+处传signal走裸client.get；apitest切tab environments×2实测"),
    N("P1-5 4处异步useEffect无cleanup", "DefectFormDialog.tsx:61-81/SearchTab.tsx:63-67,70-86/CaseDrawer.tsx:125-154 + environment页切换竞态"),
    N("P1-6 文档硬伤：docs/local-setup.md不存在+手册声称special/perftest可用但路由已隐藏+完整PRD技术栈过时(React18.3 vs 19.2.8)", "手册:11,51/路由index.tsx:214-215,234-235/完整PRD:71,100"),
    N("P1-7 缺陷前端无删除入口+删除后知识切片残留", "行内仅详情/编辑；API有DELETE；删除后knowledge source id=113 status=deprecated残留"),
    N("P2 组：6套认领队列/UI执行三入口/权限码双份/软删除三套/重复端点4组/超大路由文件9个/无statement_timeout/UI任务重复数据2条/蓝湖失败任务无清理/所属域下拉无搜索/环境长变量溢出/角色tab无骨架屏/DSH未启用仍可点/发布包空壳2个/运维控制占位/轮询无退避/page_size=200重型调用/5个>800行页面/死代码fetchProjects等", "详见四份视角报告"),
    N("P3 组：严重度标签风格混用/追溯轴标签中英混排/域命名体系不统一/报告模板列空/缺陷严重程度双风格等打磨项", "详见四份视角报告"),
]
sheets.append(sheet("问题清单173（P0-P4，含证据定位）", issues))

# ============ 附加 sheet：四者关联设计 ============
link_flow = [
    N("总目标：用例/功能/接口/UI自动化四者形成可追溯闭环，避免各自为政", "甲方核心诉求"),
    N("现状：功能8528/接口71/UI385/计划3303编排/执行通过率22.1%——接口与UI自动化严重偏少，计划编排率低", "evidence/03-summary + 26-stats-compare"),
    N("方案：TestCase双向引用（api_endpoint_ids/ui_spec_id）→ 计划混合编排 → 执行单一事实源 → 结果回填用例 → 失败自动转缺陷/报告/通知", "batch-151基础+batch-157执行模型双向关联"),
    N("扩量路径：接口资产899按GET只读优先批量生成用例；P0功能用例批量创建UI任务（Playground编译）；数据集参数化注入（Batch154已打通）", "platform-feature-value-and-redundancy-audit.md §2.1"),
]
sheets.append(sheet("四者关联设计（用例↔功能↔接口↔UI自动化）", link_flow))

out_dir = "F:/CamelTv-batch173-review/test-platform-v2/docs"
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "平台功能流转与数据流转-四视角深度审查173.xmind")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("content.json", json.dumps(sheets, ensure_ascii=False))
    z.writestr("manifest.json", json.dumps({"file-entries": {"content.json": {}}, "id": nid()}, ensure_ascii=False))
    z.writestr("metadata.json", json.dumps({"creator": {"name": "CamelTv batch-173 review", "version": "1.0"}}, ensure_ascii=False))

with open(out.replace(".xmind", ".json"), "w", encoding="utf-8") as f:
    json.dump(sheets, f, ensure_ascii=False, indent=1)

print("written:", out)
