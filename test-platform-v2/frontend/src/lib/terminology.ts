/**
 * 术语表（batch-214 / B4）—— 复用 docs/platform-refactor/03-terminology-map.md 核心词。
 * 普通用户界面禁止裸引擎术语；TermTip 用业务语言解释。
 */
export interface TermEntry {
  term: string
  label: string
  explanation: string
}

export const TERMINOLOGY: Record<string, TermEntry> = {
  mission: {
    term: 'Mission',
    label: '版本任务',
    explanation: '一个版本的验收任务：从放需求、AI 出方案，到执行、放行的整条线。',
  },
  contract: {
    term: 'Contract',
    label: '方案/契约',
    explanation: 'AI 根据需求生成的验收方案，你要逐条确认「采纳/改/删」。',
  },
  oracle: {
    term: 'Oracle',
    label: '判据',
    explanation: '判断一次执行「过/不过」的规则（比如接口返回码、页面文案）。',
  },
  run: {
    term: 'Run',
    label: '一次执行',
    explanation: '针对某个方案跑一遍，留下证据得出结论。',
  },
  evidence: {
    term: 'Evidence',
    label: '证据',
    explanation: '执行留下的截图/请求/记录，作为「过/不过」的依据。',
  },
  execution: {
    term: 'Execution',
    label: '执行记录',
    explanation: '一次真实跑动的结果记录，含成功/失败状态和证据。',
  },
}

export function getTerm(term: string): TermEntry | undefined {
  return TERMINOLOGY[term.toLowerCase()]
}
