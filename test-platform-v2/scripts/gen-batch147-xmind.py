# -*- coding: utf-8 -*-
"""batch-147 生成《平台功能流转与数据流转-四视角深度审查147.xmind》"""
import json, zipfile, uuid

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

# 0 审查总览
overview = [
    N("审查方法：四视角对抗（UI/测试工程师/架构师/甲方）× 双 AI 交叉验证 × 27 页面域深度使用 × 网络捕获", "batch-147，生产 cameltv-test-platform1.vercel.app，体育平台项目，sportsadmin"),
    N("问题热力图：P0×2（缺陷新建422崩溃/执行325失败根因不可见）P1×7 P2×24 P3×18（双AI去重后）", "详见四份视角报告与 findings JSONL"),
    N("146 复查：38 项发现 34 项仍存在、2 项部分改善、1 项部分改善但问题仍在、1 项判定预期；C146-1~6 全部未修复", "evidence/batch-147/architect/146-recheck.md"),
    N("主链路状态：需求✅→用例✅→计划⚠️(仅接口325,列表0/0)→执行❌(325失败根因不可见)→缺陷❌(新建即崩溃)→报告❌(0,手动可生成)→统计❌(7879/9429/325矛盾)"),
    N("交付结论：有条件通过（CONDITIONAL），P0 两项 + P1 三项修复后复验"),
]
root_children.append(topic("0 审查总览与问题热力图（147）", children=overview))

# 1 需求域
req_flow = [
    N("功能流转：蓝湖链接/文件上传 → 证据任务(采集/OCR/审核) → 需求文档(5) → AI 提取(476用例) → 模块树(54/660) → 生产差异(发布包) → 交互缺口(2217)"),
    N("数据流转：LanhuEvidenceJob → LanhuEvidencePage/Asset → RequirementDocument → RequirementModule → InteractionEdge → TestCase(source_doc_id)"),
    N("API：/lanhu-evidence/jobs /requirements /requirement-modules /interaction-coverage/gaps /test-cases/domains"),
    N("问题（146→147）：需求覆盖率 0%（54/660 已覆盖，C126-2 仍存在）；交互缺口 2217 全量无 P0 优先；缺口文本截断；两处「覆盖率」术语混淆；gaps 294KB 挂载即拉"),
]
root_children.append(topic("1 需求域（需求文档/评审/模块树/生产差异）", children=req_flow))

# 2 用例域
case_flow = [
    N("功能流转：用例库(7879: 功能7845/接口34/UI0) → 域/模块筛选 → 脑图(同源,page_size=10000全量10.1MB) → 计划编排(325=仅接口,列表0/0) → 评审/版本历史 → 导入导出(Excel/XMind)"),
    N("数据流转：TestCase(domain/module/P0-3) ↔ TestCaseVersion ↔ TestCaseReview ↔ TestPlanCase(325) ↔ 知识图谱(531/7879)"),
    N("API：/test-cases /test-cases/stats /test-cases/taxonomy /test-cases/domains /test-plans"),
    N("问题（146→147）：功能用例 7845 零入计划；UI 自动化用例 0；计划列表进度恒 0/0（新发现，PlanOut 缺 stats）；脑图全量 10.1MB；用例 CRUD 闭环✅"),
]
root_children.append(topic("2 用例域（用例库/脑图/评审/版本）", children=case_flow))

# 3 计划与执行域
plan_flow = [
    N("功能流转：测试计划(1: 体育平台-每日回归) → 一键执行 325/325 失败 → 执行历史(325) → 失败分诊(手动AI,置信度0%) → 报告(0,手动可生成带门禁警告)"),
    N("数据流转：TestPlan → TestPlanCase(325) → TestExecution(325, actual_result 含 error/error_type/status_code 但 UI 不暴露) ↔ ApiExecutionTask(双轨不可见)"),
    N("API：/test-plans /test-plans/:id/executions /test-plans/:id/execute /reports"),
    N("问题（146→147）：P0 TP-01 仍存在（根因不可见+无环境预检，URL http:/// 无法解析）；三执行按钮仍在；手动录入默认「通过」；执行双轨（test_execution vs api_execution_task）；dashboard 执行计数 0（恶化）"),
]
root_children.append(topic("3 计划与执行域（计划/执行/分诊/报告）", children=plan_flow))

# 4 质量域
quality_flow = [
    N("功能流转：执行失败(325) → 缺陷(0; 新建即 422 崩溃) → 报告(0) → 追溯(9429,口径矛盾) → 定时任务(2: UI 02:00启用/API 0 3 * * * 停用)"),
    N("数据流转：TestExecution → Defect(0, 关联用例/执行字段存在) → TestReport(0) → TraceStats(9429, 未过滤 is_deleted) → Schedule(2)"),
    N("API：/defects /reports /trace/coverage /trace/trend /schedules"),
    N("问题（146→147）：P0 缺陷新建 422+整页崩溃（新发现）；执行→缺陷→报告→通知全链路 0；统计口径 5 套（7879/9429/325 矛盾）；调度停用无原因；追溯轴标签中英混排"),
]
root_children.append(topic("4 质量域（缺陷/报告/追溯/定时）", children=quality_flow))

# 5 测试执行域（接口/UI/专项/性能/Playground）
exec_flow = [
    N("功能流转：接口资产(899/7服务) → 快速调试(58ms真实请求,生产守卫) → 接口用例(34) → 执行任务 → UI 自动化(3 job: 10/10,10/10,3/5) → 专项(仅音视频) → 性能(SoloX 未部署) → Playground(编译)"),
    N("数据流转：ApiAsset(OpenAPI) → ApiTestCase(34) → ApiExecutionTask ↔ UiJob(3)/UiRun ↔ MediaCheck → PerfSession(不可用) → PlaygroundSpec"),
    N("API：/apitest /api-assets /ui-automation/jobs /special /perftest /playground"),
    N("问题（146→147）：快速调试断言前置仍在（API-01 部分改善：新增生产守卫）；UI 自动化与用例零关联；接口资产 899 仅 34 用例（3.8%）；专项名不副实；性能不可用但入口未隐藏；Playground 未识别步骤静默生成 TODO"),
]
root_children.append(topic("5 测试执行域（接口/UI自动化/专项/性能/Playground）", children=exec_flow))

# 6 资产域
asset_flow = [
    N("功能流转：蓝湖证据包(采集→审核→导入) → 知识中心(69源/285切片/970实体) → 图谱(970节点,966/968关系) → AI审核台(86产物,置信度0%) → Wiki/差异对比 → Agent 工作台(队列)"),
    N("数据流转：LanhuEvidenceJob → KnowledgeSource/Chunk/Vector/Entity/Relation → WikiRawSource/Page → AiArtifact → AgentRun/QueueItem"),
    N("API：/knowledge/overview /knowledge/sources /knowledge/graph/entities /knowledge/ai-artifacts /agents"),
    N("问题（146→147）：图谱用例仅 531/7879 入库、需求实体 0、946/970 missing_source（C126-1）；AI 审核台置信度全 0%（C126-3）；graph_evolve 后端报错（新发现）；已删缺陷残留知识库（新发现）；12 tab 切页全量重拉"),
]
root_children.append(topic("6 资产域（蓝湖证据/知识中心/图谱/Agent）", children=asset_flow))

# 7 交付域
deliver_flow = [
    N("功能流转：发布包(16.0.0 草稿 0模块0页/需求基线 45/43/功能地图 draft 0/0) → 模块树构建 → 版本全景 → 运维发布控制(未配置只读占位)"),
    N("数据流转：ReleaseBundle → RequirementModule → VersionPanorama → ops 事件（知识图谱 ingestion 写入）"),
    N("API：/release-bundles /requirement-modules /ops/deployments"),
    N("问题（146→147）：发布包空壳无构建引导；运维控制不可用但降级提示✅；导航「版本测试任务」重定向冗余入口"),
]
root_children.append(topic("7 交付域（发布批次/全景/运维控制）", children=deliver_flow))

# 8 平台域
platform_flow = [
    N("功能流转：组织(1) → 项目(1 体育平台) → 环境(3: 生产/站点UI/Test5) → 系统(用户/角色/审计/Token/邀请码) → 通知(0渠道) → 集成(Test5不可达) → 数据集(0,参数化断链) → 我的项目"),
    N("数据流转：sys_organization(_member) → sys_project(_member) → Environment/Variable → SysUser/Role/AuditLog/ApiToken/InviteCode"),
    N("API：/organizations /projects /environments /system /notify /integrations /datasets"),
    N("问题（146→147）：通知 0 渠道（回归失败无人通知）；集成指向不可达 Test5；数据集参数化无 UI 入口（新发现）；menus 全页加载 ×53（恶化）；环境长变量值无换行"),
]
root_children.append(topic("8 平台域（组织/项目/系统/环境/通知/集成/数据集）", children=platform_flow))

# 9 关联优化
opt_flow = [
    N("四者关联方案：功能用例(P0锚点) ↔ 用例映射(绑定UI spec/接口用例ID) → 计划(功能+接口+UI混合) → 执行(强制绑定环境) → 结果回填功能用例 → 失败自动转缺陷+通知 → 报告自动生成 → 单一口径追溯"),
    N("请求冗余修复：menus/environments/domains 会话缓存；defect 搜索 300ms 防抖；轮询指数退避；mindmap 改服务端 taxonomy 聚合；integration 去 page_size=1 探针；client 层统一缓存+去重（请求量降 50%+，传输降 95%）"),
    N("架构收敛：统计 5→1 套；双 Worker 统一；执行双轨关联；覆盖率统一服务；AI 生成 4 路径统一；服务层环依赖治理；本地搭建 7 步文档化（docs/local-setup.md + launcher -InstallDeps）"),
    N("体育适配：接口用例 34→面级；音视频真实 URL(C101-2)；数据集驱动参数化（赛事/球队 ID）；每日 API 回归启用前置（环境/Token 就绪检查）；UI 任务按用例生成 spec 并回写"),
]
root_children.append(topic("9 关联优化建议（四者联动 + 请求冗余 + 架构收敛 + 体育适配）", children=opt_flow))

sheets = [sheet("平台功能流转与数据流转-四视角深度审查147", root_children)]

# 附加 sheet：问题清单总表（147，含 146 状态）
issues = [
    N("P0-1 缺陷新建默认路径 422 + 整页崩溃（新发现，AR-B-03/CL-B-01/UI-147-01）", "前端 DefectFormDialog assignee_id=null vs 后端 int 非 Optional；前端把错误对象渲染为 React child。修复：契约对齐 + 错误边界 + 表单提示"),
    N("P0-2 计划一键执行 325/325 失败根因不可见 + 无环境预检（TP-01/C146-1 仍存在）", "actual_result 已存 error/error_type/status_code 但 UI 不暴露；URL http:/// 无法解析；执行前无就绪检查"),
    N("P1-1 统计口径 5 套矛盾（7879/9429/325；dashboard 执行计数 0 恶化）", "收敛单一统计服务 + trace 补 is_deleted + 修复 dashboard 执行计数"),
    N("P1-2 计划列表进度恒 0/0（新发现，PlanOut 缺 stats 被 Pydantic 丢弃）"),
    N("P1-3 请求冗余（menus×53/environments×6/domains×4/defect 14键14请求/mindmap 10.1MB）", "C146-3 未修复且恶化；缓存+防抖+退避+服务端聚合"),
    N("P1-4 功能用例 7845 零入计划、UI 自动化用例 0、四者关联断裂"),
    N("P1-5 使用手册 v2.6 滞后（C146-4 未修复）；frontend README ant-design/React Router 6 过时标注"),
    N("P1-6 需求覆盖率 0% + AI 置信度 0%（C126-2/C126-3 未闭环）"),
    N("P2 组：三执行按钮/手动默认通过/Command Palette 泄漏/快速调试断言前置/数据集参数化断链/图谱 missing_source 946/graph_evolve 报错/已删缺陷残留知识库/音视频无删除/性能与运维入口未隐藏/组织占位等 24 项", "详见四份视角报告 + findings JSONL"),
    N("P3 组：404 语义/导航分组/缺口截断/时区 8h/门禁 999%/图标按钮无 aria-label/脑图键盘不可达/发布包空壳等 18 项"),
]
sheets.append(sheet("问题清单147（P0-P3，含146状态）", issues))

out = "F:/CamelTv-worktrees/codex-batch-147-quad-view-deep-review/test-platform-v2/docs/平台功能流转与数据流转-四视角深度审查147.xmind"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("content.json", json.dumps(sheets, ensure_ascii=False))
    z.writestr("manifest.json", json.dumps({"file-entries": {"content.json": {}}, "id": nid()}, ensure_ascii=False))
    z.writestr("metadata.json", json.dumps({"creator": {"name": "CamelTv Agent Team batch-147", "version": "1.0"}}, ensure_ascii=False))

with open(out.replace(".xmind", ".json"), "w", encoding="utf-8") as f:
    json.dump(sheets, f, ensure_ascii=False, indent=1)

print("written:", out)
