import {
  type KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  AlertTriangle,
  BarChart3,
  Bell,
  Bug,
  CheckCircle2,
  ChevronDown,
  Clock,
  Code2,
  Database,
  FileText,
  FlaskConical,
  FolderTree,
  GitBranch,
  LayoutDashboard,
  MoreHorizontal,
  Play,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Terminal,
  TestTube2,
  XCircle,
  Zap,
  type LucideIcon,
} from '@/lib/icons'
import { FadeContent } from '../ui-concepts/FadeContent'
import { DecryptedText } from './DecryptedText'

type ThemeId = 'crystal' | 'xlab' | 'column' | 'clay' | 'liquid'
type TabId = 'overview' | 'cases' | 'logs' | 'artifacts'
type DialogMode = 'run' | 'command' | null

interface ThemeDefinition {
  id: ThemeId
  number: string
  label: string
  name: string
  source: string
  scene: string
  tags: string[]
}

interface ModuleDefinition {
  id: string
  label: string
  description: string
  icon: LucideIcon
}

interface SnackbarState {
  message: string
  action?: string
}

const themes: ThemeDefinition[] = [
  {
    id: 'crystal',
    number: '01',
    label: '晶穹',
    name: 'Crystal Command',
    source: 'Apple × Liquid Glass',
    scene: '日间质量总览与管理协作',
    tags: ['内容优先', '功能层玻璃', '清晰留白'],
  },
  {
    id: 'xlab',
    number: '02',
    label: '黑域',
    name: 'X-Lab',
    source: 'xAI × 轻赛博',
    scene: '夜间运行值守与故障定位',
    tags: ['高对比', '终端证据', '克制霓虹'],
  },
  {
    id: 'column',
    number: '03',
    label: '列阵',
    name: 'Column Pulse',
    source: 'ClickHouse 工业数据',
    scene: '高密度用例、执行与缺陷处理',
    tags: ['黄黑识别', '数据密度', '技术可信'],
  },
  {
    id: 'clay',
    number: '04',
    label: '软体',
    name: 'Clay Studio',
    source: '企业化 Claymorphism',
    scene: '低代码编排与跨角色协作',
    tags: ['低学习压力', '触感反馈', '柔和分步'],
  },
  {
    id: 'liquid',
    number: '05',
    label: '液境',
    name: 'Liquid Spectrum',
    source: 'Liquid Glass × 全组件系统',
    scene: '跨模块连续操作与沉浸式质量协作',
    tags: ['全景玻璃', '折射层级', '丝滑衔接'],
  },
]

const modules: ModuleDefinition[] = [
  { id: 'dashboard', label: '质量工作台', description: '跨项目质量与运行总览', icon: LayoutDashboard },
  { id: 'cases', label: '用例资产', description: '用例、套件与覆盖关系', icon: FolderTree },
  { id: 'runs', label: '运行中心', description: '批次、日志与测试产物', icon: Play },
  { id: 'defects', label: '缺陷协同', description: '失败聚类与修复闭环', icon: Bug },
  { id: 'reports', label: '报告中心', description: '趋势、结论与审计记录', icon: BarChart3 },
]

const tabs: Array<{ id: TabId; label: string; count?: number }> = [
  { id: 'overview', label: '运行概览' },
  { id: 'cases', label: '用例分布', count: 2345 },
  { id: 'logs', label: '实时日志', count: 18 },
  { id: 'artifacts', label: '测试产物', count: 6 },
]

const runRows = [
  { id: 'RUN-5128', title: '核心链路全量回归', type: 'E2E', status: '运行中', progress: 68, duration: '18:24', owner: '张三' },
  { id: 'RUN-5127', title: '用户中心 API 回归', type: 'API', status: '通过', progress: 100, duration: '12:08', owner: '李四' },
  { id: 'RUN-5126', title: '首页 UI 冒烟', type: 'UI', status: '失败', progress: 100, duration: '09:31', owner: '王五' },
  { id: 'RUN-5125', title: '播放服务弱网验收', type: 'API', status: '阻塞', progress: 43, duration: '28:11', owner: '赵六' },
]

const caseRows = [
  { id: 'TC-21034', title: '正确账号登录并进入工作台', module: '账号模块', priority: 'P0', status: '通过' },
  { id: 'TC-21033', title: '错误密码触发安全提示', module: '账号模块', priority: 'P1', status: '失败' },
  { id: 'TC-21032', title: '会话超时后安全退出', module: '账号模块', priority: 'P1', status: '通过' },
  { id: 'TC-21031', title: '首页推荐内容按权限展示', module: '首页模块', priority: 'P2', status: '未执行' },
  { id: 'TC-21030', title: '弱网环境下恢复播放', module: '播放模块', priority: 'P0', status: '阻塞' },
]

const logRows = [
  ['INFO', '15:43:12.123', '开始执行：核心链路全量回归'],
  ['INFO', '15:43:12.456', '环境：预发布 / chrome-126'],
  ['DEBUG', '15:43:13.001', 'POST /api/v1/auth/login'],
  ['INFO', '15:43:13.215', '响应：200 OK · 210ms'],
  ['WARN', '15:43:13.447', '响应时间接近阈值：1287ms'],
  ['ERROR', '15:43:14.090', '视觉基线差异：header/avatar · 4.8%'],
] as const

const artifactRows = [
  { label: 'HTML 测试报告', detail: '生成中 · 72%', icon: FileText, progress: 72 },
  { label: '执行日志', detail: '18.3 MB · 可下载', icon: Terminal, progress: 100 },
  { label: '截图差异', detail: '120 张 · 4 个异常', icon: Database, progress: 100 },
  { label: 'Playwright Trace', detail: '6 个失败用例', icon: GitBranch, progress: 100 },
]

export function ThemeLab() {
  const [theme, setTheme] = useState<ThemeId>('crystal')
  const [activeModule, setActiveModule] = useState('dashboard')
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [dialog, setDialog] = useState<DialogMode>(null)
  const [environment, setEnvironment] = useState('预发布环境')
  const [loading, setLoading] = useState(false)
  const [queueBusy, setQueueBusy] = useState(true)
  const [runProgress, setRunProgress] = useState(68)
  const [runState, setRunState] = useState<'idle' | 'starting' | 'complete'>('idle')
  const [snackbar, setSnackbar] = useState<SnackbarState | null>(null)

  const themeDefinition = themes.find((item) => item.id === theme) ?? themes[0]
  const moduleDefinition = modules.find((item) => item.id === activeModule) ?? modules[0]

  const showSnackbar = useCallback((message: string, action?: string) => {
    setSnackbar({ message, action })
  }, [])

  useEffect(() => {
    if (!snackbar) return
    const timer = window.setTimeout(() => setSnackbar(null), 4200)
    return () => window.clearTimeout(timer)
  }, [snackbar])

  useEffect(() => {
    if (runState !== 'starting') return
    const timer = window.setInterval(() => {
      setRunProgress((current) => {
        const next = Math.min(100, current + 17)
        if (next === 100) {
          window.clearInterval(timer)
          setRunState('complete')
          setQueueBusy(false)
          showSnackbar('RUN-5130 已完成编排并进入执行', '查看')
        }
        return next
      })
    }, 460)
    return () => window.clearInterval(timer)
  }, [runState, showSnackbar])

  useEffect(() => {
    if (runState !== 'idle') return
    const timer = window.setTimeout(() => setQueueBusy(false), 1600)
    return () => window.clearTimeout(timer)
  }, [runState])

  useEffect(() => {
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setDialog('command')
      }
      if (event.key === 'Escape') setDialog(null)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const switchTheme = (next: ThemeId) => {
    const applyTheme = () => setTheme(next)
    const transitionDocument = document as Document & {
      startViewTransition?: (update: () => void) => unknown
    }
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (transitionDocument.startViewTransition && !reduceMotion) {
      transitionDocument.startViewTransition(applyTheme)
    } else {
      applyTheme()
    }
    const nextTheme = themes.find((item) => item.id === next)
    if (nextTheme) showSnackbar(`已切换：${nextTheme.name}`, '保留')
  }

  const simulateLoading = () => {
    if (loading) return
    setLoading(true)
    window.setTimeout(() => {
      setLoading(false)
      showSnackbar('质量数据已刷新', '查看变化')
    }, 900)
  }

  const confirmStartRun = () => {
    setDialog(null)
    setRunProgress(8)
    setRunState('starting')
    setQueueBusy(true)
    showSnackbar('已创建 RUN-5130，正在编排', '撤销')
  }

  const onTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, current: TabId) => {
    const currentIndex = tabs.findIndex((item) => item.id === current)
    let nextIndex = currentIndex
    if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length
    if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = tabs.length - 1
    if (nextIndex === currentIndex) return
    event.preventDefault()
    const nextTab = tabs[nextIndex].id
    setActiveTab(nextTab)
    document.getElementById(`theme-tab-${nextTab}`)?.focus()
  }

  const statusLine = useMemo(() => {
    if (runState === 'starting') return '正在编排新的回归批次'
    if (runState === 'complete') return '回归批次已进入执行 · RUN-5130'
    return '全部系统在线 · 3 个任务运行中'
  }, [runState])

  return (
    <div className={`theme-lab theme-${theme}`} data-theme={theme}>
      <a className="tl-skip-link" href="#theme-lab-workspace">跳到主要内容</a>

      <header className="lab-header">
        <div className="lab-title">
          <span className="lab-live-dot" />
          <div>
            <strong>测试平台 · 主题实验室</strong>
            <small>同一功能骨架 / 五种视觉系统</small>
          </div>
        </div>

        <div className="theme-switcher" aria-label="测试平台主题切换">
          {themes.map((item) => (
            <button
              key={item.id}
              className={theme === item.id ? 'is-active' : ''}
              aria-pressed={theme === item.id}
              aria-label={`${item.label}主题：${item.source}`}
              onClick={() => switchTheme(item.id)}
            >
              <span>{item.number}</span>
              <b>{item.label}</b>
            </button>
          ))}
        </div>

        <div className="lab-coverage">
          <span>组件覆盖</span>
          <b>8 / 8</b>
          <small>纯演示数据</small>
        </div>
      </header>

      <div className="lab-shell">
        <aside className="lab-sidebar" aria-label="平台模块">
          <div className="platform-brand">
            <span className="brand-symbol"><TestTube2 aria-hidden="true" /></span>
            <span><b>CamelTv</b><small>企业测试平台</small></span>
          </div>

          <nav className="module-nav">
            <span className="nav-caption">质量工程</span>
            {modules.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  className={activeModule === item.id ? 'is-active' : ''}
                  aria-current={activeModule === item.id ? 'page' : undefined}
                  onClick={() => {
                    setActiveModule(item.id)
                    setActiveTab(item.id === 'runs' ? 'logs' : 'overview')
                  }}
                >
                  <Icon aria-hidden="true" />
                  <span>{item.label}</span>
                  {item.id === 'runs' && <i>3</i>}
                </button>
              )
            })}
          </nav>

          <div className="sidebar-foot">
            <button><Settings aria-hidden="true" /><span>平台设置</span></button>
            <div className="environment-health"><ShieldCheck aria-hidden="true" /><span><b>服务正常</b><small>12 / 12 在线</small></span></div>
          </div>
        </aside>

        <div className="lab-main-column">
          <header className="platform-topbar">
            <div className="project-context">
              <label>
                <span>当前项目</span>
                <span className="select-control">
                  <select aria-label="当前项目" defaultValue="CamelTv 核心平台">
                    <option>CamelTv 核心平台</option>
                    <option>海外业务平台</option>
                    <option>增长实验项目</option>
                  </select>
                  <ChevronDown aria-hidden="true" />
                </span>
              </label>
              <label>
                <span>执行环境</span>
                <span className="select-control">
                  <select aria-label="执行环境" value={environment} onChange={(event) => {
                    setEnvironment(event.target.value)
                    showSnackbar(`已切换到${event.target.value}`)
                  }}>
                    <option>测试环境</option>
                    <option>预发布环境</option>
                    <option>生产只读</option>
                  </select>
                  <ChevronDown aria-hidden="true" />
                </span>
              </label>
            </div>

            <div className="topbar-actions">
              <button className="global-search" onClick={() => setDialog('command')}>
                <Search aria-hidden="true" />
                <span>搜索用例、任务、缺陷</span>
                <kbd>⌘ K</kbd>
              </button>
              <button className="icon-control" aria-label="通知"><Bell aria-hidden="true" /><i>6</i></button>
              <button className="profile-control"><span>张</span><b>张三</b><ChevronDown aria-hidden="true" /></button>
            </div>
          </header>

          <main className="lab-workspace" id="theme-lab-workspace">
            <section className="theme-manifest" aria-label="当前主题说明">
              <div>
                <span>{themeDefinition.number} / {String(themes.length).padStart(2, '0')}</span>
                <b>{themeDefinition.name}</b>
                <small>{themeDefinition.source}</small>
              </div>
              <p>{themeDefinition.scene}</p>
              <ul>{themeDefinition.tags.map((tag) => <li key={tag}>{tag}</li>)}</ul>
            </section>

            {theme === 'liquid' && (
              <LiquidComponentPanorama
                progress={runProgress}
                loading={loading}
                onLoading={simulateLoading}
                onSnackbar={() => showSnackbar('液态玻璃轻提示已就绪', '查看')}
                onBackdrop={() => setDialog('run')}
              />
            )}

            <div className="page-heading">
              <div>
                <span className="breadcrumbs">项目空间 / {moduleDefinition.label}</span>
                <h1>{moduleDefinition.label}</h1>
                <p>{moduleDefinition.description}</p>
                <div className="system-status">
                  <span className="status-signal" />
                  {theme === 'xlab' || theme === 'liquid' ? (
                    <DecryptedText text={statusLine} activeKey={`${statusLine}-${theme}`} />
                  ) : (
                    <span>{statusLine}</span>
                  )}
                </div>
              </div>
              <div className="heading-actions">
                <button className="secondary-action" onClick={simulateLoading} disabled={loading}>
                  <RefreshCw aria-hidden="true" />
                  {loading ? '加载中' : '模拟加载'}
                </button>
                <button className="primary-action" onClick={() => setDialog('run')}>
                  <Play aria-hidden="true" />
                  启动回归
                </button>
              </div>
            </div>

            <div className="content-tabs" role="tablist" aria-label="质量工作台视图">
              {tabs.map((item) => (
                <button
                  key={item.id}
                  id={`theme-tab-${item.id}`}
                  role="tab"
                  aria-selected={activeTab === item.id}
                  aria-controls={`theme-panel-${item.id}`}
                  tabIndex={activeTab === item.id ? 0 : -1}
                  className={activeTab === item.id ? 'is-active' : ''}
                  onKeyDown={(event) => onTabKeyDown(event, item.id)}
                  onClick={() => setActiveTab(item.id)}
                >
                  {item.label}
                  {item.count !== undefined && <span>{item.count}</span>}
                </button>
              ))}
            </div>

            <FadeContent transitionKey={`${theme}-${activeTab}-${loading}`}>
              <section
                className="tab-panel"
                id={`theme-panel-${activeTab}`}
                role="tabpanel"
                aria-labelledby={`theme-tab-${activeTab}`}
              >
                {loading ? (
                  <DashboardSkeleton />
                ) : (
                  <TabContent
                    activeTab={activeTab}
                    queueBusy={queueBusy}
                    runProgress={runProgress}
                    onShowSnackbar={showSnackbar}
                  />
                )}
              </section>
            </FadeContent>
          </main>
        </div>
      </div>

      {dialog === 'run' && (
        <RunDialog
          environment={environment}
          onClose={() => setDialog(null)}
          onConfirm={confirmStartRun}
        />
      )}

      {dialog === 'command' && (
        <CommandDialog
          onClose={() => setDialog(null)}
          onNavigate={(tab) => {
            setActiveTab(tab)
            setDialog(null)
            showSnackbar(`已打开：${tabs.find((item) => item.id === tab)?.label ?? tab}`)
          }}
        />
      )}

      <div className={`lab-snackbar ${snackbar ? 'is-visible' : ''}`} role="status" aria-live="polite">
        <CheckCircle2 aria-hidden="true" />
        <span>{snackbar?.message}</span>
        {snackbar?.action && <button onClick={() => setSnackbar(null)}>{snackbar.action}</button>}
      </div>
    </div>
  )
}

function LiquidComponentPanorama({
  progress,
  loading,
  onLoading,
  onSnackbar,
  onBackdrop,
}: {
  progress: number
  loading: boolean
  onLoading: () => void
  onSnackbar: () => void
  onBackdrop: () => void
}) {
  return (
    <section className="liquid-panorama" role="region" aria-label="液态组件全景">
      <div className="liquid-panorama-heading">
        <span>FULL COMPONENT LAYER</span>
        <b><DecryptedText text="液态组件全景已连接" activeKey="liquid-panorama" /></b>
        <small>八类组件共享原业务状态，仅改变材质、层级与过渡反馈。</small>
      </div>

      <div className="liquid-panorama-components">
        <div className="liquid-ring-sample">
          <ProgressRing value={progress} label="液态主题运行进度" />
          <span><b>Progress Ring</b><small>确定性进度</small></span>
        </div>

        <div className="liquid-linear-sample">
          <span><b>Progress Bar</b><small>{progress}% · 正在执行</small></span>
          <span className="liquid-mini-progress" aria-label={`线性执行进度：${progress}%`} role="img">
            <i style={{ transform: `scaleX(${progress / 100})` }} />
          </span>
        </div>

        <div className="liquid-spinner-sample">
          <span className="local-spinner" aria-hidden="true" />
          <span><b>Spinner</b><small>短时入队</small></span>
        </div>

        <div className="liquid-skeleton-sample" aria-label="Skeleton 结构占位示例">
          <span><i /><i /><i /></span>
          <span><b>Skeleton</b><small>保留数据布局</small></span>
        </div>
      </div>

      <div className="liquid-panorama-actions" aria-label="液态组件交互演示">
        <span>Tabs · 主视图已启用</span>
        <span>Decode · 状态揭示</span>
        <button className="secondary-action" onClick={onLoading} disabled={loading}>
          <RefreshCw aria-hidden="true" />{loading ? '骨架加载中' : '演示骨架屏'}
        </button>
        <button className="secondary-action" onClick={onSnackbar}>演示轻提示</button>
        <button className="primary-action" onClick={onBackdrop}>演示背景幕布</button>
      </div>
    </section>
  )
}

function TabContent({
  activeTab,
  queueBusy,
  runProgress,
  onShowSnackbar,
}: {
  activeTab: TabId
  queueBusy: boolean
  runProgress: number
  onShowSnackbar: (message: string, action?: string) => void
}) {
  if (activeTab === 'cases') return <CasesView onShowSnackbar={onShowSnackbar} />
  if (activeTab === 'logs') return <LogsView />
  if (activeTab === 'artifacts') return <ArtifactsView />
  return <OverviewView queueBusy={queueBusy} runProgress={runProgress} onShowSnackbar={onShowSnackbar} />
}

function OverviewView({ queueBusy, runProgress, onShowSnackbar }: { queueBusy: boolean; runProgress: number; onShowSnackbar: (message: string, action?: string) => void }) {
  return (
    <div className="overview-layout">
      <section className="suite-panel surface-panel">
        <div className="panel-heading">
          <div><span>发布门禁 · R2026.07</span><h2>核心链路回归</h2><p>覆盖 12 个服务、3 个端和 2,345 条用例</p></div>
          <button className="icon-control" aria-label="更多计划操作"><MoreHorizontal aria-hidden="true" /></button>
        </div>
        <div className="suite-summary">
          <ProgressRing value={runProgress} label="当前回归批次进度" />
          <div className="suite-stats">
            <div><span>已通过</span><b>1,838</b><small>78.4%</small></div>
            <div><span>失败</span><b>14</b><small>6 个 P0/P1</small></div>
            <div><span>阻塞</span><b>6</b><small>2 个等待环境</small></div>
            <div><span>待执行</span><b>487</b><small>预计 34 分钟</small></div>
          </div>
        </div>
      </section>

      <section className="queue-panel surface-panel">
        <div className="panel-heading"><div><span>执行队列</span><h2>实时调度</h2></div><span className="live-chip">LIVE</span></div>
        <div className="queue-current">
          {queueBusy ? <span className="local-spinner" aria-label="正在加入执行队列" /> : <CheckCircle2 aria-hidden="true" />}
          <div><b>{queueBusy ? '正在准备运行容器' : '执行队列准备完成'}</b><small>{queueBusy ? '短时未知进度使用 Spinner' : '节点已分配 · 可开始执行'}</small></div>
        </div>
        <div className="queue-list">
          <div><span><i className="tone-blue" />API 回归</span><b>8 / 12</b></div>
          <div><span><i className="tone-violet" />UI 自动化</span><b>3 / 6</b></div>
          <div><span><i className="tone-amber" />弱网专项</span><b>1 / 4</b></div>
        </div>
        <button className="text-action" onClick={() => onShowSnackbar('执行队列已暂停 30 秒', '恢复')}>暂停调度</button>
      </section>

      <div className="metric-strip">
        <Metric icon={Zap} label="今日执行" value="128" detail="较昨日 +12" tone="blue" />
        <Metric icon={CheckCircle2} label="通过率" value="78.4%" detail="较昨日 +3.6%" tone="green" />
        <Metric icon={Clock} label="平均耗时" value="18m" detail="目标 ≤ 20m" tone="amber" />
        <Metric icon={AlertTriangle} label="高风险失败" value="6" detail="需要立即处理" tone="red" />
      </div>

      <section className="run-table-panel surface-panel">
        <div className="panel-heading">
          <div><span>运行与证据</span><h2>最近执行</h2><p>统一查看 E2E、API 与 UI 自动化结果</p></div>
          <div className="panel-actions"><button onClick={() => onShowSnackbar('筛选视图“今日高风险”已保存', '撤销')}>保存视图</button><button><FileText aria-hidden="true" />导出</button></div>
        </div>
        <div className="data-table-wrap">
          <table>
            <thead><tr><th>运行编号</th><th>任务</th><th>类型</th><th>状态</th><th>进度</th><th>耗时</th><th>负责人</th><th><span className="sr-only">操作</span></th></tr></thead>
            <tbody>{runRows.map((row, index) => {
              const progress = index === 0 ? runProgress : row.progress
              return (
                <tr key={row.id}>
                  <td><code>{row.id}</code></td>
                  <td><b>{row.title}</b></td>
                  <td>{row.type}</td>
                  <td><StatusPill status={index === 0 && runProgress < 100 ? '运行中' : row.status} /></td>
                  <td><div className="table-progress"><span><i style={{ transform: `scaleX(${progress / 100})` }} /></span><b>{progress}%</b></div></td>
                  <td>{row.duration}</td>
                  <td>{row.owner}</td>
                  <td><button className="row-action" aria-label={`查看 ${row.id}`}><MoreHorizontal aria-hidden="true" /></button></td>
                </tr>
              )
            })}</tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

function CasesView({ onShowSnackbar }: { onShowSnackbar: (message: string, action?: string) => void }) {
  return (
    <section className="surface-panel cases-view">
      <div className="filter-toolbar">
        <label><Search aria-hidden="true" /><input aria-label="搜索用例" placeholder="搜索编号、标题、模块" /></label>
        <button className="filter-chip is-active">全部状态</button>
        <button className="filter-chip">P0 / P1</button>
        <button className="filter-chip">本周变更</button>
        <button className="primary-action" onClick={() => onShowSnackbar('已创建用例草稿 TC-21035', '编辑')}>新建用例</button>
      </div>
      <div className="case-list" role="list">
        {caseRows.map((row) => (
          <div key={row.id} role="listitem">
            <button onClick={() => onShowSnackbar(`已打开 ${row.id}`, '查看详情')}>
              <span className={`priority priority-${row.priority.toLowerCase()}`}>{row.priority}</span>
              <span><code>{row.id}</code><b>{row.title}</b><small>{row.module}</small></span>
              <StatusPill status={row.status} />
              <MoreHorizontal aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </section>
  )
}

function LogsView() {
  return (
    <section className="surface-panel logs-view">
      <div className="log-toolbar"><div><span className="terminal-mark"><Terminal aria-hidden="true" /></span><div><h2>RUN-5128 / 实时日志</h2><small>自动跟随已开启 · 18 条事件</small></div></div><div><button className="filter-chip is-active">全部</button><button className="filter-chip">WARN</button><button className="filter-chip">ERROR</button></div></div>
      <div className="log-console" aria-label="实时执行日志">
        {logRows.map(([level, time, message]) => <div key={`${time}-${level}`} className={`log-${level.toLowerCase()}`}><span>{level}</span><time>{time}</time><code>{message}</code></div>)}
        <div className="log-cursor"><span className="local-spinner" aria-hidden="true" /><code>等待下一条运行事件…</code></div>
      </div>
    </section>
  )
}

function ArtifactsView() {
  return (
    <div className="artifact-grid">
      {artifactRows.map((row) => {
        const Icon = row.icon
        return (
          <button key={row.label} className="surface-panel artifact-card">
            <span className="artifact-icon"><Icon aria-hidden="true" /></span>
            <span><b>{row.label}</b><small>{row.detail}</small></span>
            <span className="artifact-progress"><i style={{ transform: `scaleX(${row.progress / 100})` }} /></span>
          </button>
        )
      })}
      <section className="surface-panel artifact-note"><Sparkles aria-hidden="true" /><div><h2>产物查看器建议补齐</h2><p>截图、视频、Trace、请求响应与基线 Diff 应在同一 Inspector 内预览，避免反复下载和跳转。</p></div></section>
    </div>
  )
}

function ProgressRing({ value, label }: { value: number; label: string }) {
  return (
    <div className="progress-ring" role="img" aria-label={`${label}：${value}%`}>
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle className="ring-track" cx="60" cy="60" r="50" pathLength="100" />
        <circle className="ring-value" cx="60" cy="60" r="50" pathLength="100" strokeDasharray="100" strokeDashoffset={100 - value} />
      </svg>
      <span><b>{value}%</b><small>整体进度</small></span>
    </div>
  )
}

function Metric({ icon: Icon, label, value, detail, tone }: { icon: LucideIcon; label: string; value: string; detail: string; tone: string }) {
  return <div className={`metric-cell metric-${tone}`}><span className="metric-icon"><Icon aria-hidden="true" /></span><span><small>{label}</small><b>{value}</b><em>{detail}</em></span></div>
}

function StatusPill({ status }: { status: string }) {
  const icon = status === '通过' ? <CheckCircle2 aria-hidden="true" /> : status === '失败' ? <XCircle aria-hidden="true" /> : status === '阻塞' ? <AlertTriangle aria-hidden="true" /> : status === '未执行' ? <Clock aria-hidden="true" /> : <span className="pulse-dot" />
  return <span className={`status-pill status-${status}`}>{icon}{status}</span>
}

function DashboardSkeleton() {
  return (
    <div className="dashboard-skeleton" aria-busy="true" aria-label="正在加载质量数据">
      <div className="skeleton-block skeleton-hero"><i /><i /><i /><i /></div>
      <div className="skeleton-block skeleton-side"><i /><i /><i /></div>
      <div className="skeleton-metrics">{Array.from({ length: 4 }, (_, index) => <div className="skeleton-block" key={index}><i /><i /></div>)}</div>
      <div className="skeleton-block skeleton-table">{Array.from({ length: 5 }, (_, index) => <i key={index} />)}</div>
    </div>
  )
}

function RunDialog({ environment, onClose, onConfirm }: { environment: string; onClose: () => void; onConfirm: () => void }) {
  return (
    <div className="tl-backdrop" onMouseDown={onClose}>
      <section className="run-dialog" role="dialog" aria-modal="true" aria-label="启动回归确认" onMouseDown={(event) => event.stopPropagation()}>
        <span className="dialog-icon"><FlaskConical aria-hidden="true" /></span>
        <div className="dialog-copy"><span>新建运行批次</span><h2>启动核心链路回归？</h2><p>系统将在本地原型中演示编排、短时 Spinner、确定进度和 Snackbar，不会连接生产数据。</p></div>
        <dl><div><dt>执行环境</dt><dd>{environment}</dd></div><div><dt>测试范围</dt><dd>2,345 条用例 / 12 个服务</dd></div><div><dt>预计耗时</dt><dd>34–42 分钟</dd></div></dl>
        <div className="dialog-warning"><AlertTriangle aria-hidden="true" /><span><b>安全说明</b><small>所有操作均为前端演示状态，可刷新页面复位。</small></span></div>
        <div className="dialog-actions"><button className="secondary-action" autoFocus onClick={onClose}>取消</button><button className="primary-action" onClick={onConfirm}><Play aria-hidden="true" />确认启动</button></div>
      </section>
    </div>
  )
}

function CommandDialog({ onClose, onNavigate }: { onClose: () => void; onNavigate: (tab: TabId) => void }) {
  return (
    <div className="tl-backdrop" onMouseDown={onClose}>
      <section className="command-dialog" role="dialog" aria-modal="true" aria-label="全局命令面板" onMouseDown={(event) => event.stopPropagation()}>
        <label className="command-search"><Search aria-hidden="true" /><input autoFocus aria-label="搜索全局命令" placeholder="输入页面或操作名称…" /><kbd>ESC</kbd></label>
        <div className="command-group"><span>快速前往</span>
          <button onClick={() => onNavigate('overview')}><LayoutDashboard aria-hidden="true" /><span><b>运行概览</b><small>查看质量趋势与执行队列</small></span><kbd>↵</kbd></button>
          <button onClick={() => onNavigate('cases')}><FolderTree aria-hidden="true" /><span><b>用例分布</b><small>筛选和查看测试资产</small></span><kbd>↵</kbd></button>
          <button onClick={() => onNavigate('logs')}><Code2 aria-hidden="true" /><span><b>实时日志</b><small>定位警告、错误和请求证据</small></span><kbd>↵</kbd></button>
          <button onClick={() => onNavigate('artifacts')}><Database aria-hidden="true" /><span><b>测试产物</b><small>报告、截图与 Trace</small></span><kbd>↵</kbd></button>
        </div>
        <footer><span><ShieldCheck aria-hidden="true" />原型命令不会执行真实操作</span><span>↑ ↓ 导航 · Enter 打开</span></footer>
      </section>
    </div>
  )
}
