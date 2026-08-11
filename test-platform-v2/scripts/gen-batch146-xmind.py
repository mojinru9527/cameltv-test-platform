# -*- coding: utf-8 -*-
"""batch-146 生成《平台功能流转与数据流转-四视角审查.xmind》"""
import json, zipfile, uuid, sys

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

# 节点文案（标题, 备注）
def N(t, note=None): return topic(t, note)

# ============ 主图 ============
root_children = []

# 0 审查总览
overview = [
    N("审查方法：四视角对抗（UI/测试工程师/架构师/甲方）+ 24 页面域深度使用 + 网络捕获", "batch-146，生产 cameltv-test-platform1.vercel.app，体育平台项目"),
    N("问题热力图：P0×1（计划执行325全失败根因不可见）P1×4（统计口径/执行链路0/覆盖率0%/数据可信）P2×16 P3×14", "详见四份视角报告"),
    N("主链路状态：需求✅→用例✅→计划⚠️(仅接口325)→执行❌(325失败)→缺陷❌(0)→报告❌(0)→统计❌(0%)"),
    N("交付结论：有条件通过（CONDITIONAL），P0 两项修复后复验"),
]
root_children.append(topic("0 审查总览与问题热力图", children=overview))

# 1 需求域
req_flow = [
    N("功能流转：蓝湖链接/文件上传 → 证据任务(采集/OCR/审核) → 需求文档(5) → AI 提取(476用例) → 模块树(54/660) → 生产差异(发布包) → 交互缺口"),
    N("数据流转：LanhuEvidenceJob → LanhuEvidencePage/Asset → RequirementDocument → RequirementModule → InteractionEdge → TestCase(source_doc_id)"),
    N("API：/lanhu-evidence/jobs /requirements /requirement-modules /interaction-coverage/gaps /test-cases/domains"),
    N("问题：需求覆盖率 0%（54/660 已覆盖，C126-2）；交互缺口 2217 全量无 P0 优先；缺口文本截断；两处「覆盖率」术语混淆"),
]
root_children.append(topic("1 需求域（需求文档/评审/模块树/生产差异）", children=req_flow))

# 2 用例域
case_flow = [
    N("功能流转：用例库(7879: 功能7845/接口34/UI0) → 域/模块筛选 → 脑图(同源) → 计划编排(325=仅接口) → 评审/版本历史 → 导入导出(Excel/XMind)"),
    N("数据流转：TestCase(domain/module/P0-3) ↔ TestCaseVersion ↔ TestCaseReview ↔ TestPlanCase(325) ↔ 知识图谱(531/7879)"),
    N("API：/test-cases /test-cases/stats /test-cases/taxonomy /test-cases/domains /test-plans"),
    N("问题：功能用例 7845 零入计划；UI 自动化用例 0；脑图 page_size=10000 全量拉取；工作台 7879 vs 追溯 9424 口径不一"),
    N("CRUD 实测：创建→搜索→编辑→删除 全闭环 PASS（临时数据已清理）"),
]
root_children.append(topic("2 用例域（用例库/脑图/计划）", children=case_flow))

# 3 执行域
exec_flow = [
    N("接口执行：计划一键执行(325/325 失败 P0) / 单条手动录入(默认通过⚠️) / 执行任务(5) / 快速调试(200 PASS) / 生产守卫确认"),
    N("UI 执行：job(2) 交互路径回归每日 02:00 10/10×11 天 ✅ + P0 只读回归；产物目录隔离"),
    N("调度：UI 0 2 * * *(启用) / API 0 3 * * *(停用无原因提示)；专项(0 任务, HLS 表单)；性能(SoloX 不可用降级✅)"),
    N("数据流转：ApiExecutionTask(Item) ↔ TestExecution ↔ TestPlanCase；UiTestJob/Run/Script；AvCheckTask；PerfSession"),
    N("问题(P0)：计划执行失败根因不可见（无 HTTP 状态/错误摘要）；执行双轨（test_execution vs api_execution_task）互不可见；双 Worker 竞态（task_worker vs api_task_worker）"),
]
root_children.append(topic("3 执行域（接口测试/UI自动化/专项/调度/性能）", children=exec_flow))

# 4 质量域
qual_flow = [
    N("功能流转：执行结果 → 失败分诊(手动AI) → 缺陷(0) → 报告(0) → 追溯(执行0/通过0) → 工作台(通过率0%)"),
    N("数据流转：TestExecution → Defect(软链接 case_id/execution_id) → TestReport(plan_id FK) → TraceService 聚合 → Dashboard"),
    N("API：/defects /defects/stats /reports /reports/trends /trace/coverage /dashboard/stats /dashboard/cross-project"),
    N("问题(P1)：执行失败无下游动作（缺陷/报告/通知全 0）；统计 5 套实现口径不一；缺陷表单完备但空置"),
]
root_children.append(topic("4 质量域（缺陷/报告/追溯/工作台）", children=qual_flow))

# 5 资产域
asset_flow = [
    N("功能流转：蓝湖证据包(采集→审核→导入) → 知识中心(69源/285切片/970实体) → 图谱(965节点/968关系) → AI审核台 → Wiki/差异对比 → Agent 工作台(4 agent)"),
    N("数据流转：LanhuEvidenceJob → KnowledgeSource/Chunk/Vector/Entity/Relation → WikiRawSource/Page → AiArtifact → AgentRun"),
    N("API：/knowledge/overview /knowledge/sources /knowledge/graph/entities /agents /wiki"),
    N("问题：图谱用例仅 531/7879 入库、需求实体 0（C126-1）；AI 审核台置信度全 0%（C126-3）；知识 12 tab 切页全量重拉（B3）"),
]
root_children.append(topic("5 资产域（蓝湖证据/知识中心/图谱/Agent）", children=asset_flow))

# 6 交付域
deliver_flow = [
    N("功能流转：发布包(16.0.0 草稿 0模块0页) → 模块树构建(空) → 版本全景 → 运维发布控制(未配置只读占位)"),
    N("数据流转：ReleaseBundle → RequirementModule → VersionPanorama → ops 事件（知识图谱 ingestion 写入）"),
    N("API：/release-bundles /requirement-modules /ops/deployments"),
    N("问题：发布包空壳无构建引导；运维控制不可用但降级提示✅；导航「版本测试任务」重定向冗余入口"),
]
root_children.append(topic("6 交付域（发布批次/全景/运维控制）", children=deliver_flow))

# 7 平台域
platform_flow = [
    N("功能流转：组织(1) → 项目(1 体育平台) → 环境(3: 生产/站点UI/Test5) → 系统(用户/角色/审计/Token/邀请码) → 通知(0渠道) → 集成(Test5不可达) → 数据集(0)"),
    N("数据流转：sys_organization(_member) → sys_project(_member) → Environment/Variable → SysUser/Role/AuditLog/ApiToken/InviteCode"),
    N("API：/organizations /projects /environments /system /notify /integrations /datasets"),
    N("问题：通知 0 渠道（回归失败无人通知）；集成指向不可达 Test5；数据集空置；菜单端点每页重拉 15 次（ARCH）"),
]
root_children.append(topic("7 平台域（组织/项目/系统/环境/通知/集成/数据集）", children=platform_flow))

# 8 关联优化
opt_flow = [
    N("四者关联方案：功能用例(P0锚点) ↔ 用例映射(绑定UI spec/接口用例ID) → 计划(功能+接口+UI混合) → 执行 → 结果回填功能用例 → 失败自动转缺陷+通知 → 报告自动生成 → 单一口径追溯"),
    N("请求冗余修复：menus/environments/domains 会话缓存；防抖/退避；Tab 状态保留；client 层统一缓存+去重（请求量降 50%+）"),
    N("架构收敛：统计 5→1 套；双 Worker 统一；覆盖率统一服务；AI 生成 4 路径统一；本地搭建 7 步文档化"),
    N("体育适配：接口用例 34→面级；音视频真实 URL(C101-2)；数据集驱动参数化；每日 API 回归启用前置"),
]
root_children.append(topic("8 关联优化建议（四者联动 + 请求冗余 + 架构收敛 + 体育适配）", children=opt_flow))

sheets = [sheet("平台功能流转与数据流转-四视角审查", root_children)]

# 附加 sheet：问题清单总表
issues = [
    N("P0-1 计划一键执行 325/325 失败根因不可见（TP-01，视角2/4）", "执行历史无 HTTP 状态/错误摘要；建议执行记录加失败原因列+环境前置检查"),
    N("P1-1 统计口径不一：工作台 7879 vs 追溯 9424（TR-01/WB-01，架构 B-1）", "5 套统计实现收敛为 1 套"),
    N("P1-2 执行链路全 0：执行/通过/缺陷/报告 统计失真（WB-01/TR-02/RP-01）", "执行结果不回流统计与下游"),
    N("P1-3 需求覆盖率 0%（REQ-01，C126-2 未闭环）"),
    N("P1-4 图谱用例仅 531/7879 入库 + AI 置信度 0%（KN-01/KN-02，C126-1/C126-3）"),
    N("P2 组：Command Palette 泄漏/三执行按钮/手动默认通过/快速调试需先断言/术语混淆/缺口截断/通知0渠道/功能用例不入计划等 16 项", "详见四视角报告"),
    N("P3 组：Trace 列空/404 语义/表格密度/脑图键盘不可达/发布包空壳等 14 项"),
]
sheets.append(sheet("问题清单（P0-P3）", issues))

# 写入 xmind（ZIP）
out = "F:/CamelTv-worktrees/claude-batch-146-quad-view-review/test-platform-v2/docs/平台功能流转与数据流转-四视角审查.xmind"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("content.json", json.dumps(sheets, ensure_ascii=False))
    z.writestr("manifest.json", json.dumps({"file-entries": {"content.json": {}}, "id": nid()}, ensure_ascii=False))
    z.writestr("metadata.json", json.dumps({"creator": {"name": "CamelTv Agent Team batch-146", "version": "1.0"}}, ensure_ascii=False))

# 同时输出 JSON 源（供审查/复用）
with open(out.replace(".xmind", ".json"), "w", encoding="utf-8") as f:
    json.dump(sheets, f, ensure_ascii=False, indent=1)

print("written:", out)
