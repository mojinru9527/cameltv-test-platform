import type { LucideIcon } from '@/lib/icons'
import {
  BarChart3,
  Bug,
  ClipboardCheck,
  FileText,
  FlaskConical,
  LayoutDashboard,
  Monitor,
  Play,
  TestTube2,
} from '@/lib/icons'

export type Concept = 'bright' | 'ops'
export type Surface =
  | 'overview'
  | 'requirement'
  | 'cases'
  | 'plan'
  | 'execution'
  | 'api'
  | 'automation'
  | 'report'
  | 'defect'

export type Status = '通过' | '失败' | '运行中' | '阻塞' | '未执行'

export interface NavItem {
  id: Surface
  label: string
  icon: LucideIcon
  group: 'quality' | 'engineering'
}

export interface RunRecord {
  id: string
  title: string
  type: string
  status: Status
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  environment: string
  owner: string
  startedAt: string
  duration: string
  progress: number
}

export interface CaseRecord {
  id: string
  title: string
  module: string
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  status: Status
  owner: string
  updatedAt: string
}

export const navItems: NavItem[] = [
  { id: 'overview', label: '工作台', icon: LayoutDashboard, group: 'quality' },
  { id: 'requirement', label: '需求管理', icon: FileText, group: 'quality' },
  { id: 'cases', label: '用例服务', icon: TestTube2, group: 'quality' },
  { id: 'plan', label: '测试计划', icon: ClipboardCheck, group: 'quality' },
  { id: 'execution', label: '运行中心', icon: Play, group: 'engineering' },
  { id: 'api', label: 'API 测试', icon: FlaskConical, group: 'engineering' },
  { id: 'automation', label: 'UI 自动化', icon: Monitor, group: 'engineering' },
  { id: 'report', label: '报告中心', icon: BarChart3, group: 'engineering' },
  { id: 'defect', label: '缺陷管理', icon: Bug, group: 'engineering' },
]

export const surfaceDescriptions: Record<Surface, string> = {
  overview: '跨需求、用例、计划与执行的质量总览',
  requirement: '需求解析、评审状态与覆盖进度',
  cases: '维护可追溯、可复用的测试用例资产',
  plan: '组织回归范围、执行批次与发布门禁',
  execution: '实时掌握任务进度、异常与测试产物',
  api: '管理接口资产、调试请求并沉淀自动化用例',
  automation: '编排浏览器任务并检查截图、视频与 Trace',
  report: '汇总质量结论并输出可审计报告',
  defect: '跟踪缺陷状态、修复进度与回归结论',
}

export const runs: RunRecord[] = [
  {
    id: 'RUN-5128',
    title: '核心回归计划_20250517',
    type: '测试计划',
    status: '运行中',
    priority: 'P1',
    environment: '生产环境',
    owner: 'admin',
    startedAt: '2025-05-17 15:42:31',
    duration: '00:18:24',
    progress: 58,
  },
  {
    id: 'RUN-5127',
    title: '用户中心 API 回归',
    type: 'API 测试',
    status: '通过',
    priority: 'P1',
    environment: '测试环境',
    owner: 'tester01',
    startedAt: '2025-05-17 15:30:10',
    duration: '00:12:08',
    progress: 100,
  },
  {
    id: 'RUN-5126',
    title: '首页 UI 自动化冒烟',
    type: 'UI 自动化',
    status: '失败',
    priority: 'P2',
    environment: '预发环境',
    owner: 'tester02',
    startedAt: '2025-05-17 15:20:45',
    duration: '00:09:31',
    progress: 100,
  },
  {
    id: 'RUN-5125',
    title: '播放服务接口验收',
    type: 'API 测试',
    status: '阻塞',
    priority: 'P1',
    environment: '测试环境',
    owner: 'tester03',
    startedAt: '2025-05-17 15:10:05',
    duration: '00:28:11',
    progress: 43,
  },
  {
    id: 'RUN-5124',
    title: '支付链路 E2E',
    type: '测试计划',
    status: '通过',
    priority: 'P0',
    environment: '预发环境',
    owner: 'admin',
    startedAt: '2025-05-17 14:58:00',
    duration: '00:21:09',
    progress: 100,
  },
]

export const cases: CaseRecord[] = [
  { id: 'TC-21034', title: '用户登录 - 正确账号登录', module: '账号模块', priority: 'P0', status: '通过', owner: '张三', updatedAt: '10:24' },
  { id: 'TC-21033', title: '用户登录 - 错误密码提示', module: '账号模块', priority: 'P1', status: '失败', owner: '李四', updatedAt: '10:20' },
  { id: 'TC-21032', title: '用户登出与会话失效', module: '账号模块', priority: 'P1', status: '通过', owner: '王五', updatedAt: '09:58' },
  { id: 'TC-21031', title: '首页推荐内容展示', module: '首页模块', priority: 'P2', status: '未执行', owner: '张三', updatedAt: '09:33' },
  { id: 'TC-21030', title: '搜索功能 - 关键词搜索', module: '搜索模块', priority: 'P1', status: '阻塞', owner: '赵六', updatedAt: '09:12' },
  { id: 'TC-21029', title: '弱网环境播放恢复', module: '播放模块', priority: 'P0', status: '运行中', owner: '陈七', updatedAt: '08:48' },
]

export const logLines = [
  ['INFO', '15:43:12.123', '开始执行：核心回归计划_20250517'],
  ['INFO', '15:43:12.456', '环境：生产环境'],
  ['INFO', '15:43:12.789', '开始用例：登录 - 正确账号'],
  ['DEBUG', '15:43:13.001', '请求：POST /api/v1/auth/login'],
  ['INFO', '15:43:13.215', '响应状态：200 OK（210ms）'],
  ['WARN', '15:43:13.447', '响应时间接近阈值：1287ms'],
  ['INFO', '15:43:14.090', '断言通过：status_code = 200'],
] as const
