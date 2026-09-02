export interface GuestModuleCapability {
  title: string
  description: string
}

export interface GuestModuleDefinition {
  title: string
  description: string
  capabilities: readonly GuestModuleCapability[]
}

function defineModule(
  title: string,
  description: string,
  capabilities: readonly (readonly [string, string])[],
): GuestModuleDefinition {
  return {
    title,
    description,
    capabilities: capabilities.map(([capabilityTitle, capabilityDescription]) => ({
      title: capabilityTitle,
      description: capabilityDescription,
    })),
  }
}

const GUEST_MODULES: Record<string, GuestModuleDefinition> = {
  '/workbench': defineModule('工作台', '集中查看项目质量状态、待办事项和关键测试进展。', [
    ['质量概览', '汇总用例、计划、缺陷和执行通过率，快速识别当前风险。'],
    ['测试待办', '呈现需要处理的评审、执行与异常任务，帮助安排当天工作。'],
    ['快捷入口', '从同一页面进入需求、用例、计划、报告等常用模块。'],
  ]),
  // (P2c) 质量追溯已并入报告中心 Tab（/trace → /report?tab=trace），访客目录并入报告中心
  '/requirement': defineModule('需求文档', '管理需求输入、结构化解析、评审与用例生成过程。', [
    ['文档解析', '上传需求并提取功能点、模块结构和可测试信息。'],
    ['AI 辅助生成', '按功能点分批生成用例，并展示覆盖矩阵与缺口。'],
    ['评审与导入', '人工确认生成结果后导入项目用例库，保留来源关联。'],
  ]),
  '/release-bundles': defineModule('版本测试任务', '围绕一个发布版本组织范围、证据、测试任务和质量结论。', [
    ['版本范围', '统一记录需求、用例、变更和环境等发布输入。'],
    ['测试任务', '组织版本级执行、日志和结果，跟踪完成进度。'],
    ['版本全景', '从版本视角查看覆盖、缺陷、风险和交付状态。'],
  ]),
  '/knowledge': defineModule('知识中心', '沉淀项目知识、平台研发经验、知识图谱和 AI 审核产物。', [
    ['知识采集与检索', '导入可信来源并通过关键词或语义方式检索。'],
    ['知识图谱', '查看模块、接口、需求、用例等实体及其关系。'],
    ['AI 审核台', '人工审核 AI 产物差异，决定采纳、驳回或继续补充。'],
  ]),
  // (P2a) 用例脑图已并入用例服务「脑图视图」Tab（/mindmap → /testcase?tab=mindmap），访客目录并入用例服务
  '/testcase': defineModule('用例服务', '集中管理功能、接口和 UI 自动化用例及其版本与评审。', [
    ['分类与检索', '按端别、业务域、子模块、优先级和关键字定位用例。'],
    ['评审与版本', '提交、审批或驳回用例，并查看每次修改的版本历史。'],
    ['批量与交换', '批量更新或删除，并通过 Excel、XMind 导入导出。'],
  ]),
  '/apitest': defineModule('接口测试', '从接口资产到用例设计、调试和真实执行管理 API 测试。', [
    ['契约导入', '导入 OpenAPI/Swagger 契约并整理服务、模块和端点。'],
    ['用例与断言', '配置请求参数、环境变量、依赖接口和结构化断言。'],
    ['调试与批量执行', '在授权环境中调试或批量执行，并回填请求与响应结果。'],
  ]),
  '/uitest': defineModule('UI 自动化', '管理浏览器自动化脚本、运行任务和可视化执行证据。', [
    ['脚本资产', '组织 Playwright 测试脚本、标签和运行配置。'],
    ['任务执行', '在指定环境触发 UI 回归并查看实时与最终状态。'],
    ['失败证据', '查看截图、控制台、网络和步骤信息，辅助复现问题。'],
  ]),
  // (P2b) Playground 已并入用例服务 Tab（/playground → /testcase?tab=playground），访客目录并入用例服务
  '/schedule': defineModule('定时任务', '按计划自动触发 API、UI 或其他回归任务。', [
    ['调度配置', '设置 Cron、任务类型、运行范围和启停状态。'],
    ['运行历史', '查看每次触发的时间、状态、耗时和结果。'],
    ['失败联动', '将失败结果接入通知和后续缺陷处理流程。'],
  ]),
  '/report': defineModule('报告中心', '把测试执行、缺陷和质量指标整理为可复核报告。', [
    ['报告生成', '基于计划与执行结果生成结构化测试报告。'],
    ['质量指标', '汇总通过率、缺陷分布、风险和结论。'],
    ['模板与导出', '使用项目模板组织章节，并导出交付材料。'],
  ]),
  '/system': defineModule('系统管理', '管理平台用户、角色、菜单权限和审计配置。', [
    ['用户与角色', '维护账号状态和角色分配，控制平台访问范围。'],
    ['权限配置', '按菜单与操作权限定义不同岗位的能力边界。'],
    ['平台审计', '查看关键管理操作并维护系统级配置。'],
  ]),
  '/my-projects': defineModule('我的项目', '创建、选择和管理自己可访问的测试项目。', [
    ['创建项目', '普通注册用户可创建第一个项目并成为负责人。'],
    ['项目切换', '选择当前工作项目，平台数据和操作随项目隔离。'],
    ['成员邀请', '通过成员管理或邀请链接协作，同时保留角色权限。'],
  ]),
  '/defect': defineModule('缺陷管理', '记录、分派、跟踪和关闭测试发现的问题。', [
    ['缺陷登记', '记录严重级、复现步骤、环境、负责人和关联资产。'],
    ['状态流转', '跟踪确认、修复、复测和关闭过程。'],
    ['关联分析', '从缺陷回看用例、执行和需求，判断影响范围。'],
  ]),
  '/dataset': defineModule('测试数据集', '集中维护测试执行中使用的结构化参数和样本。', [
    ['数据集管理', '创建不同场景、环境或边界条件的数据集合。'],
    ['变量复用', '在接口和自动化任务中复用统一测试参数。'],
    ['项目隔离', '数据集只在所属项目和授权成员范围内可见。'],
  ]),
  '/integration': defineModule('集成配置', '连接外部缺陷、协作或研发系统并控制同步方式。', [
    ['连接配置', '维护外部系统地址、认证方式和启停状态。'],
    ['字段映射', '定义平台资产与外部系统字段的对应关系。'],
    ['同步策略', '配置同步方向、频率和失败处理方式。'],
  ]),
  '/notify': defineModule('通知配置', '为测试事件配置邮件、机器人等通知通道。', [
    ['通知通道', '维护 SMTP 或机器人等项目通知目标。'],
    ['事件订阅', '选择计划完成、缺陷分派等需要通知的事件。'],
    ['发送记录', '查看通知发送状态和失败原因，便于排查。'],
  ]),
  '/environment': defineModule('目标环境', '维护开发、测试、预发和生产等执行目标。', [
    ['环境地址', '为不同环境配置基础地址和用途说明。'],
    ['变量管理', '维护执行所需变量，并对敏感值采用受控存储。'],
    ['生产保护', '标识生产环境并对高风险执行增加权限与确认。'],
  ]),
  // (P1b) Agent 工作台已收敛进 DSH 任务，访客目录不再单列（页面删除，路由重定向）
  '/lanhu-evidence': defineModule('蓝湖证据包', '从设计稿采集页面、OCR 文本和结构化需求证据。', [
    ['设计采集', '从授权的蓝湖项目提取页面、图片和层级信息。'],
    ['OCR 与审核', '识别设计文本并对缺失或低质量页面进行人工审核。'],
    ['需求入库', '把审核后的证据关联到需求、知识和后续用例生成。'],
  ]),
}

export function resolveGuestModule(
  pathname: string,
  _search = '',
  menuLabel = '',
): GuestModuleDefinition {
  const definition = GUEST_MODULES[pathname]
  if (definition) {
    return menuLabel && menuLabel !== definition.title
      ? { ...definition, title: menuLabel }
      : definition
  }
  const title = menuLabel.trim() || '平台功能'
  return defineModule(
    title,
    `${title} 的业务数据与操作需要登录并选择项目后使用。`,
    [
      ['功能说明', '访客可以先了解该模块的定位和使用边界。'],
      ['项目隔离', '登录后仅访问当前项目和权限允许的数据。'],
      ['安全操作', '新建、执行、修改和导出等动作需要身份与权限校验。'],
    ],
  )
}
