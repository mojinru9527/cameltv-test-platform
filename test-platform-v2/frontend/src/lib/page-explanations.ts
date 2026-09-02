/**
 * 页面业务解释（batch-214 / B4 AskAi MVP）。
 * key = 路由 base（路径前缀匹配），value = 业务语言解释 + 常见动作。
 * 真实 LLM 随后续批次接入；本表为 MVP 内容骨架。
 */
export interface PageExplanation {
  title: string
  description: string
  actions: string[]
}

const EXPLANATIONS: Array<{ match: (p: string) => boolean; exp: PageExplanation }> = [
  {
    match: (p) => p === '/' || p === '/workbench',
    exp: {
      title: '我的待办（首页）',
      description: '今天要审什么、什么在跑、什么失败、哪个版本待放行，在这里一眼看到。',
      actions: ['点「待审」去看 AI 生成的用例', '点「在跑」看后台任务进度', '点「待放行」去验收版本'],
    },
  },
  {
    match: (p) => p.startsWith('/missions'),
    exp: {
      title: '版本验收',
      description: '从需求到放行的一条线：放需求 → AI 出方案 → 执行 → 下结论。',
      actions: ['新建版本任务', '评审 AI 方案', '看执行与证据'],
    },
  },
  {
    match: (p) => p.startsWith('/testcase'),
    exp: {
      title: '用例服务（资产）',
      description: '管理功能/接口/UI 用例：你的自动化与人工用例都在这，作为版本验收的资产。',
      actions: ['检索用例', '导入/生成用例', '查看执行历史'],
    },
  },
  {
    match: (p) => p.startsWith('/report'),
    exp: {
      title: '报告中心（结果与缺陷）',
      description: '看跑完的结果、通过率、证据，以及录了的缺陷。',
      actions: ['看执行趋势', '定位失败', '转缺陷'],
    },
  },
  {
    match: (p) => p.startsWith('/defect'),
    exp: {
      title: '缺陷管理（结果与缺陷）',
      description: '业务失败在这里归集、流转、关闭，导出到外部缺陷库。',
      actions: ['新建缺陷', '按状态筛选', '批量流转'],
    },
  },
  {
    match: (p) => p.startsWith('/knowledge'),
    exp: {
      title: '知识中心（知识复用）',
      description: '上版怎么测的、这版改了哪、哪些能直接复用，在这里沉淀与检索。',
      actions: ['检索上版方案', '看复用建议', '审核知识'],
    },
  },
  {
    match: (p) => p.startsWith('/release-bundles'),
    exp: {
      title: '版本发布包',
      description: '一个版本的用户端+运营后台+附件聚合，作为「待放行」的载体。',
      actions: ['创建发布包', '绑定需求/环境', '验收放行'],
    },
  },
]

export function getExplanation(pathname: string): PageExplanation {
  const hit = EXPLANATIONS.find((e) => e.match(pathname))
  if (hit) return hit.exp
  return {
    title: '测试平台',
    description: '这是平台的一个模块。你可以从左侧「我的待办/版本验收/结果与缺陷/知识复用/资产与更多」进入主线。',
    actions: ['回到我的待办', '去版本验收'],
  }
}
