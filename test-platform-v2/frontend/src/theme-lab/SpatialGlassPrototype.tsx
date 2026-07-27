import { type CSSProperties, type PointerEvent, useMemo, useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  Bug,
  CheckCircle2,
  Clock,
  FileCheck,
  FileText,
  GitBranch,
  Layers,
  Play,
  RefreshCw,
  ShieldCheck,
  Target,
  TestTube2,
  TrendingUp,
  type LucideIcon,
} from '@/lib/icons'

type StageId = 'requirement' | 'case' | 'plan' | 'execution' | 'defect' | 'report'
type FilterId = 'all' | 'risk' | 'p0'
type StageTone = 'neutral' | 'success' | 'active' | 'risk'

interface StageDefinition {
  id: StageId
  label: string
  shortLabel: string
  count: string
  meta: string
  progress: number
  owner: string
  status: string
  summary: string
  action: string
  risk: boolean
  p0: boolean
  tone: StageTone
  icon: LucideIcon
}

interface SpatialGlassPrototypeProps {
  loading: boolean
  runProgress: number
  runState: 'idle' | 'starting' | 'complete'
  onStartRun: () => void
  onRefresh: () => void
  onShowSnackbar: (message: string, action?: string) => void
}

const stages: StageDefinition[] = [
  {
    id: 'requirement',
    label: '需求基线',
    shortLabel: '需求',
    count: '12',
    meta: '3 项本周变更',
    progress: 92,
    owner: '产品与 QA',
    status: '基线已锁定',
    summary: '发布范围、验收口径与影响链已完成关联，2 项需求仍需补充异常路径。',
    action: '复核变更影响',
    risk: true,
    p0: false,
    tone: 'neutral',
    icon: FileText,
  },
  {
    id: 'case',
    label: '用例资产',
    shortLabel: '用例',
    count: '2,345',
    meta: '覆盖率 86%',
    progress: 86,
    owner: '测试设计组',
    status: '持续补齐',
    summary: '核心链路已覆盖，新增支付降级策略缺少 14 条接口与弱网组合用例。',
    action: '打开覆盖缺口',
    risk: true,
    p0: true,
    tone: 'neutral',
    icon: TestTube2,
  },
  {
    id: 'plan',
    label: '计划编排',
    shortLabel: '计划',
    count: '6',
    meta: '4 个自动批次',
    progress: 100,
    owner: '质量负责人',
    status: '门禁就绪',
    summary: '冒烟、API、端到端、视觉与弱网专项已按依赖顺序编排，可直接启动。',
    action: '查看执行策略',
    risk: false,
    p0: false,
    tone: 'success',
    icon: GitBranch,
  },
  {
    id: 'execution',
    label: '测试执行',
    shortLabel: '执行',
    count: '4',
    meta: '3 个任务运行中',
    progress: 68,
    owner: '自动化集群',
    status: '实时执行',
    summary: '预发布环境正在执行核心链路回归，当前吞吐稳定，预计 18 分钟完成。',
    action: '进入运行指挥台',
    risk: false,
    p0: false,
    tone: 'active',
    icon: Play,
  },
  {
    id: 'defect',
    label: '缺陷归因',
    shortLabel: '缺陷',
    count: '3',
    meta: '2 个 P0 / P1',
    progress: 61,
    owner: '研发与 QA',
    status: '需要决策',
    summary: '登录超时与播放器恢复失败已聚类到两个根因，其中一个阻断发布门禁。',
    action: '处理阻断缺陷',
    risk: true,
    p0: true,
    tone: 'risk',
    icon: Bug,
  },
  {
    id: 'report',
    label: '报告签发',
    shortLabel: '报告',
    count: '1',
    meta: '615 份证据已归档',
    progress: 72,
    owner: '发布委员会',
    status: '等待结论',
    summary: '报告已聚合需求、用例、执行和缺陷证据，待阻断项关闭后生成最终结论。',
    action: '预览发布报告',
    risk: false,
    p0: false,
    tone: 'neutral',
    icon: FileCheck,
  },
]

const milestones: Array<{ time: string; label: string; stage: StageId; note: string }> = [
  { time: '07 / 23', label: '范围冻结', stage: 'requirement', note: 'R2026.07 基线' },
  { time: '07 / 24', label: '资产就绪', stage: 'case', note: '2,345 条用例' },
  { time: '07 / 25', label: '计划签发', stage: 'plan', note: '6 个执行计划' },
  { time: '今天 15:40', label: '全量回归', stage: 'execution', note: '当前进度 68%' },
  { time: '今天 16:10', label: '缺陷归因', stage: 'defect', note: '3 项待处理' },
]

const risks: Array<{ title: string; detail: string; stage: StageId; severity: string }> = [
  { title: '支付降级路径缺少 P0 组合用例', detail: '需求 RQ-118 · 影响发布门禁', stage: 'case', severity: 'P0' },
  { title: '登录会话超时后无法自动恢复', detail: 'DEF-2061 · 已复现 3 次', stage: 'defect', severity: 'P0' },
  { title: '视觉基线差异超过阈值', detail: 'header/avatar · 差异 4.8%', stage: 'execution', severity: 'P1' },
]

function setSpotlight(event: PointerEvent<HTMLElement>) {
  const bounds = event.currentTarget.getBoundingClientRect()
  event.currentTarget.style.setProperty('--spotlight-x', `${event.clientX - bounds.left}px`)
  event.currentTarget.style.setProperty('--spotlight-y', `${event.clientY - bounds.top}px`)
}

export function SpatialGlassPrototype({
  loading,
  runProgress,
  runState,
  onStartRun,
  onRefresh,
  onShowSnackbar,
}: SpatialGlassPrototypeProps) {
  const [selectedStage, setSelectedStage] = useState<StageId>('execution')
  const [filter, setFilter] = useState<FilterId>('all')

  const selected = stages.find((stage) => stage.id === selectedStage) ?? stages[3]
  const visibleStages = useMemo(() => {
    if (filter === 'risk') return stages.filter((stage) => stage.risk)
    if (filter === 'p0') return stages.filter((stage) => stage.p0)
    return stages
  }, [filter])

  const selectStage = (stage: StageDefinition, message?: string) => {
    setSelectedStage(stage.id)
    if (message) onShowSnackbar(message, '查看')
  }

  const applyFilter = (next: FilterId) => {
    setFilter(next)
    const firstMatch = next === 'all'
      ? stages.find((stage) => stage.id === selectedStage)
      : stages.find((stage) => next === 'risk' ? stage.risk : stage.p0)
    if (firstMatch && next !== 'all') setSelectedStage(firstMatch.id)
    onShowSnackbar(next === 'all' ? '已恢复全链路视图' : next === 'risk' ? '已聚焦 3 个风险节点' : '已聚焦 P0 阻断项')
  }

  return (
    <section
      className="obsidian-workbench"
      role="region"
      aria-label="黑曜流界交互实验"
      onPointerMove={setSpotlight}
    >
      <header className="obsidian-hero">
        <div className="obsidian-kicker"><span />QUALITY OPERATING SYSTEM · R2026.07</div>
        <div className="obsidian-title-row">
          <div>
            <span className="breadcrumbs">项目空间 / 质量工作台 / 发布门禁</span>
            <h1>把测试从页面集合，变成一条可操作的质量链。</h1>
            <p>需求、用例、计划、执行、缺陷和报告不再分散跳转；风险沿链路显形，证据在上下文中完成闭环。</p>
          </div>
          <div className="obsidian-hero-actions">
            <button className="secondary-action" onClick={onRefresh} disabled={loading}>
              <RefreshCw aria-hidden="true" />
              {loading ? '加载中' : '模拟加载'}
            </button>
            <button className="primary-action" onClick={onStartRun}>
              <Play aria-hidden="true" />
              启动回归
            </button>
          </div>
        </div>
        <div className="obsidian-status-line">
          <span className="obsidian-live"><i />{runState === 'starting' ? '正在编排 RUN-5130' : runState === 'complete' ? 'RUN-5130 已进入执行' : '质量链实时同步'}</span>
          <span>预发布环境</span>
          <span>最后同步 18 秒前</span>
        </div>
      </header>

      {loading ? (
        <ObsidianSkeleton />
      ) : (
        <>
          <div className="obsidian-metrics" aria-label="发布健康指标">
            <Metric icon={ShieldCheck} label="发布健康度" value="87%" note="+4.2% 本周" tone="positive" />
            <Metric icon={Play} label="运行任务" value="4" note={`${runProgress}% 全量回归`} tone="active" />
            <Metric icon={AlertTriangle} label="阻断风险" value="3" note="2 项 P0 / P1" tone="risk" />
            <Metric icon={FileCheck} label="证据归档" value="615" note="需求到报告可追溯" tone="neutral" />
          </div>

          <div className="obsidian-bento">
            <section className="obsidian-chain-plane obsidian-spotlight">
              <div className="obsidian-panel-heading">
                <div>
                  <span>QUALITY CHAIN</span>
                  <h2>发布质量链</h2>
                  <p>点击节点，在同一工作台查看状态、风险与下一步动作。</p>
                </div>
                <div className="obsidian-filters" aria-label="质量链筛选">
                  {([
                    ['all', '全链路'],
                    ['risk', '仅风险'],
                    ['p0', 'P0'],
                  ] as Array<[FilterId, string]>).map(([id, label]) => (
                    <button
                      key={id}
                      aria-pressed={filter === id}
                      className={filter === id ? 'is-active' : ''}
                      onClick={() => applyFilter(id)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className={`obsidian-chain filter-${filter}`} aria-label="发布质量阶段">
                {visibleStages.map((stage, index) => {
                  const Icon = stage.icon
                  return (
                    <button
                      key={stage.id}
                      className={`obsidian-stage stage-${stage.tone} ${selectedStage === stage.id ? 'is-selected' : ''}`}
                      style={{ '--stage-index': index } as CSSProperties}
                      aria-pressed={selectedStage === stage.id}
                      aria-label={`${stage.label}阶段：${stage.status}`}
                      onClick={() => selectStage(stage)}
                    >
                      <span className="obsidian-stage-index">0{stages.findIndex((item) => item.id === stage.id) + 1}</span>
                      <span className="obsidian-stage-icon"><Icon aria-hidden="true" /></span>
                      <span className="obsidian-stage-copy">
                        <small>{stage.shortLabel}</small>
                        <b>{stage.count}</b>
                        <em>{stage.status}</em>
                      </span>
                      <span className="obsidian-stage-progress" aria-label={`${stage.label}完成度 ${stage.progress}%`}>
                        <i style={{ transform: `scaleX(${stage.progress / 100})` }} />
                      </span>
                    </button>
                  )
                })}
              </div>

              <footer className="obsidian-chain-foot">
                <span><Layers aria-hidden="true" />一条链路 · 六种业务对象</span>
                <span><TrendingUp aria-hidden="true" />风险自动向发布结论传导</span>
              </footer>
            </section>

            <aside className={`obsidian-inspector inspector-${selected.tone} obsidian-spotlight`} aria-label="阶段检查器" aria-live="polite">
              <div className="obsidian-inspector-top">
                <span className="obsidian-inspector-icon"><selected.icon aria-hidden="true" /></span>
                <span><small>STAGE INSPECTOR</small><b>{selected.label}</b></span>
                <i>{selected.status}</i>
              </div>
              <div className="obsidian-inspector-value">
                <strong>{selected.count}</strong>
                <span><b>{selected.meta}</b><small>当前负责人 · {selected.owner}</small></span>
              </div>
              <p>{selected.summary}</p>
              <div className="obsidian-inspector-progress">
                <span><b>阶段完成度</b><em>{selected.progress}%</em></span>
                <span><i style={{ transform: `scaleX(${selected.progress / 100})` }} /></span>
              </div>
              <button onClick={() => onShowSnackbar(`${selected.action}已打开`, '关闭')}>
                {selected.action}<ArrowRight aria-hidden="true" />
              </button>
            </aside>

            <section className="obsidian-risk-plane">
              <div className="obsidian-panel-heading">
                <div><span>ATTENTION</span><h2>风险雷达</h2></div>
                <b>3 项需要动作</b>
              </div>
              <div className="obsidian-risk-list">
                {risks.map((risk) => {
                  const stage = stages.find((item) => item.id === risk.stage) ?? stages[0]
                  return (
                    <button
                      key={risk.title}
                      className={selectedStage === risk.stage ? 'is-active' : ''}
                      onClick={() => selectStage(stage, `已定位：${risk.title}`)}
                    >
                      <span>{risk.severity}</span>
                      <span><b>{risk.title}</b><small>{risk.detail}</small></span>
                      <ArrowRight aria-hidden="true" />
                    </button>
                  )
                })}
              </div>
            </section>

            <section className="obsidian-timeline-plane">
              <div className="obsidian-panel-heading">
                <div><span>RELEASE PULSE</span><h2>发布脉冲</h2></div>
                <span className="obsidian-decision"><i />待决策</span>
              </div>
              <div className="obsidian-timeline" aria-label="发布里程碑">
                {milestones.map((milestone) => {
                  const stage = stages.find((item) => item.id === milestone.stage) ?? stages[0]
                  return (
                    <button
                      key={milestone.label}
                      aria-label={milestone.label}
                      className={selectedStage === milestone.stage ? 'is-active' : ''}
                      onClick={() => selectStage(stage)}
                    >
                      <time>{milestone.time}</time>
                      <i />
                      <span><b>{milestone.label}</b><small>{milestone.note}</small></span>
                    </button>
                  )
                })}
              </div>
            </section>
          </div>
        </>
      )}
    </section>
  )
}

function Metric({
  icon: Icon,
  label,
  value,
  note,
  tone,
}: {
  icon: LucideIcon
  label: string
  value: string
  note: string
  tone: 'positive' | 'active' | 'risk' | 'neutral'
}) {
  return (
    <div className={`obsidian-metric metric-${tone}`}>
      <span><Icon aria-hidden="true" />{label}</span>
      <b>{value}</b>
      <small>{note}</small>
    </div>
  )
}

function ObsidianSkeleton() {
  return (
    <div className="obsidian-skeleton" aria-busy="true" aria-label="正在加载质量数据">
      <span className="obsidian-skeleton-metrics">{Array.from({ length: 4 }, (_, index) => <i key={index} />)}</span>
      <span className="obsidian-skeleton-chain"><i /><i /><i /><i /><i /><i /></span>
      <span className="obsidian-skeleton-inspector"><i /><i /><i /><i /></span>
      <span className="obsidian-skeleton-bottom"><i /><i /></span>
    </div>
  )
}
