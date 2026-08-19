import type { LucideIcon } from 'lucide-react'
import { FileText, ClipboardCheck, Code2, Monitor, MessageSquare } from '@/lib/icons'

export type SceneId = 'import_requirement' | 'functional' | 'api' | 'ui' | 'general'

export interface SceneDef {
  id: SceneId
  label: string
  description: string
  icon: LucideIcon
  inputLabel: string
  inputPlaceholder: string
  inputRows: number
  buildPrompt: (input: string) => string
}

export const SCENES: SceneDef[] = [
  {
    id: 'import_requirement',
    label: '导入需求',
    description: '分析需求文本/URL，输出功能模块拆分与验收要点',
    icon: FileText,
    inputLabel: '需求内容（文本或 URL）',
    inputPlaceholder: '粘贴需求文档内容或需求 URL…',
    inputRows: 8,
    buildPrompt: (input) =>
      `你是资深测试需求分析师。分析以下需求内容，输出：功能模块拆分、核心业务规则、验收要点、风险点。\n\n需求内容：\n${input}`,
  },
  {
    id: 'functional',
    label: '功能用例',
    description: '基于需求生成功能测试用例（正常/边界/异常）',
    icon: ClipboardCheck,
    inputLabel: '需求文本',
    inputPlaceholder: '粘贴需求内容…',
    inputRows: 8,
    buildPrompt: (input) =>
      `你是功能测试用例设计专家。基于以下需求，按测试用例标准（编号、前置条件、步骤、预期结果）设计覆盖正常/边界/异常的功能用例。\n\n需求内容：\n${input}`,
  },
  {
    id: 'api',
    label: '接口用例',
    description: '基于接口定义生成接口用例（参数/边界/断言）',
    icon: Code2,
    inputLabel: '接口定义（OpenAPI/JSON）',
    inputPlaceholder: '粘贴 OpenAPI/Swagger 定义或接口描述…',
    inputRows: 8,
    buildPrompt: (input) =>
      `你是接口测试专家。基于以下接口定义，设计接口用例（含参数校验、边界值、异常场景、断言要点）。\n\n接口定义：\n${input}`,
  },
  {
    id: 'ui',
    label: 'UI 自动化用例',
    description: '基于功能点生成 Playwright UI 自动化用例',
    icon: Monitor,
    inputLabel: '功能点描述',
    inputPlaceholder: '粘贴功能用例或页面交互描述…',
    inputRows: 8,
    buildPrompt: (input) =>
      `你是 UI 自动化测试专家。基于以下功能点，设计 Playwright UI 自动化用例（打开页面、操作步骤、断言）。\n\n功能点：\n${input}`,
  },
  {
    id: 'general',
    label: '通用任务',
    description: '自由输入自然语言任务，交给 DSH 执行',
    icon: MessageSquare,
    inputLabel: '任务描述',
    inputPlaceholder: '输入任意自然语言任务…',
    inputRows: 6,
    buildPrompt: (input) => input,
  },
]

export const SCENE_BY_ID: Record<string, SceneDef> = Object.fromEntries(
  SCENES.map((s) => [s.id, s]),
)

export function sceneLabel(id: string): string {
  return SCENE_BY_ID[id]?.label ?? id
}
