import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  BarChart3,
  Bell,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  Columns2,
  Database,
  Eye,
  FileText,
  FlaskConical,
  FolderTree,
  Key,
  Loader2,
  Maximize2,
  MoreHorizontal,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  Send,
  Settings,
  Terminal,
  TestTube2,
  User,
  XCircle,
} from '@/lib/icons'
import { FadeContent } from './FadeContent'
import {
  cases,
  logLines,
  navItems,
  runs,
  surfaceDescriptions,
  type CaseRecord,
  type Concept,
  type RunRecord,
  type Status,
  type Surface,
} from './model'

type DrawerMode = 'detail' | 'create' | null
type LogLevel = 'ALL' | 'INFO' | 'WARN' | 'DEBUG'

const surfaceTitle = (surface: Surface) => navItems.find((item) => item.id === surface)?.label ?? '工作台'

export function InteractionPrototype() {
  const [concept, setConcept] = useState<Concept>('bright')
  const [surface, setSurface] = useState<Surface>('overview')
  const [project, setProject] = useState('CamelTv 核心平台')
  const [environment, setEnvironment] = useState('测试环境')
  const [pendingEnvironment, setPendingEnvironment] = useState<string | null>(null)
  const [selectedRunId, setSelectedRunId] = useState('RUN-5128')
  const [selectedCaseId, setSelectedCaseId] = useState('TC-21034')
  const [drawerMode, setDrawerMode] = useState<DrawerMode>(null)
  const [commandOpen, setCommandOpen] = useState(false)
  const [navCollapsed, setNavCollapsed] = useState(false)
  const [paused, setPaused] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [caseSearch, setCaseSearch] = useState('')
  const [caseStatus, setCaseStatus] = useState('全部状态')
  const [logLevel, setLogLevel] = useState<LogLevel>('ALL')
  const [apiSending, setApiSending] = useState(false)
  const [apiSent, setApiSent] = useState(false)

  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0]
  const selectedCase = cases.find((item) => item.id === selectedCaseId) ?? cases[0]

  const filteredCases = useMemo(() => {
    const keyword = caseSearch.trim().toLowerCase()
    return cases.filter((item) => {
      const matchesKeyword = !keyword || `${item.id}${item.title}${item.module}`.toLowerCase().includes(keyword)
      const matchesStatus = caseStatus === '全部状态' || item.status === caseStatus
      return matchesKeyword && matchesStatus
    })
  }, [caseSearch, caseStatus])

  const visibleLogs = logLines.filter(([level]) => logLevel === 'ALL' || level === logLevel)

  const announce = (message: string) => setFeedback(message)

  useEffect(() => {
    if (!feedback) return
    const timer = window.setTimeout(() => setFeedback(''), 2400)
    return () => window.clearTimeout(timer)
  }, [feedback])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCommandOpen(true)
      }
      if (event.key === 'Escape') {
        setCommandOpen(false)
        setDrawerMode(null)
        setPendingEnvironment(null)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const switchConcept = (next: Concept) => {
    setConcept(next)
    setDrawerMode(null)
    announce(next === 'bright' ? '已切换到明亮企业方案' : '已切换到深色运维方案')
  }

  const switchSurface = (next: Surface) => {
    setSurface(next)
    setDrawerMode(null)
  }

  const requestEnvironment = (next: string) => {
    if (next === '生产环境' && environment !== '生产环境') {
      setPendingEnvironment(next)
      return
    }
    setEnvironment(next)
    announce(`已切换到${next}`)
  }

  const sendApiRequest = () => {
    if (apiSending) return
    setApiSending(true)
    setApiSent(false)
    window.setTimeout(() => {
      setApiSending(false)
      setApiSent(true)
      announce('请求成功：200 OK · 132ms')
    }, 650)
  }

  return (
    <div className={`prototype concept-${concept}`}>
      <a className="skip-link" href="#prototype-workspace">跳到主内容</a>
      <ComparisonBar concept={concept} onChange={switchConcept} />

      <div className={`app-frame ${navCollapsed ? 'nav-is-collapsed' : ''}`}>
        <Sidebar
          concept={concept}
          surface={surface}
          collapsed={navCollapsed}
          onToggle={() => setNavCollapsed((value) => !value)}
          onNavigate={switchSurface}
        />

        <div className="app-column">
          <Topbar
            concept={concept}
            project={project}
            environment={environment}
            onProjectChange={(next) => {
              setProject(next)
              announce(`项目上下文已切换到 ${next}`)
            }}
            onEnvironmentChange={requestEnvironment}
            onOpenCommand={() => setCommandOpen(true)}
          />

          <main className="workspace" id="prototype-workspace">
            <FadeContent transitionKey={`${concept}-${surface}`}>
              <PageHeading
                surface={surface}
                concept={concept}
                paused={paused}
                onCreate={() => setDrawerMode('create')}
                onPause={() => {
                  setPaused((value) => !value)
                  announce(paused ? '执行已继续' : '执行已暂停')
                }}
                onRetry={() => {
                  setPaused(false)
                  announce('任务已重新进入执行队列')
                }}
              />

              {surface === 'overview' && (
                <OverviewView
                  concept={concept}
                  selectedRunId={selectedRunId}
                  onSelectRun={(id) => {
                    setSelectedRunId(id)
                    setDrawerMode('detail')
                  }}
                />
              )}

              {surface === 'cases' && (
                <CasesView
                  concept={concept}
                  rows={filteredCases}
                  selectedCaseId={selectedCaseId}
                  search={caseSearch}
                  status={caseStatus}
                  onSearchChange={setCaseSearch}
                  onStatusChange={setCaseStatus}
                  onSelectCase={(id) => {
                    setSelectedCaseId(id)
                    setDrawerMode('detail')
                  }}
                  onCreate={() => setDrawerMode('create')}
                />
              )}

              {surface === 'execution' && (
                <ExecutionView
                  concept={concept}
                  selectedRun={selectedRun}
                  selectedRunId={selectedRunId}
                  paused={paused}
                  logLevel={logLevel}
                  visibleLogs={visibleLogs}
                  onSelectRun={setSelectedRunId}
                  onLogLevelChange={setLogLevel}
                  onPause={() => {
                    setPaused((value) => !value)
                    announce(paused ? '执行已继续' : '执行已暂停')
                  }}
                  onRetry={() => {
                    setPaused(false)
                    announce('执行进度已重置，任务重新排队')
                  }}
                />
              )}

              {surface === 'api' && (
                <ApiView
                  apiSending={apiSending}
                  apiSent={apiSent}
                  onSend={sendApiRequest}
                />
              )}

              {!['overview', 'cases', 'execution', 'api'].includes(surface) && (
                <ModuleView surface={surface} onNavigate={switchSurface} />
              )}
            </FadeContent>
          </main>
        </div>
      </div>

      {drawerMode && surface !== 'execution' && (
        <ContextDrawer
          mode={drawerMode}
          concept={concept}
          selectedCase={selectedCase}
          selectedRun={selectedRun}
          surface={surface}
          onClose={() => setDrawerMode(null)}
          onSave={() => {
            setDrawerMode(null)
            announce(drawerMode === 'create' ? '用例草稿已创建' : '修改已保存')
          }}
        />
      )}

      {commandOpen && (
        <CommandPalette
          onClose={() => setCommandOpen(false)}
          onNavigate={(next) => {
            switchSurface(next)
            setCommandOpen(false)
          }}
        />
      )}

      {pendingEnvironment && (
        <EnvironmentDialog
          onCancel={() => setPendingEnvironment(null)}
          onConfirm={() => {
            setEnvironment(pendingEnvironment)
            setPendingEnvironment(null)
            announce('已切换到生产环境，危险操作保护已开启')
          }}
        />
      )}

      <div className={`prototype-toast ${feedback ? 'is-visible' : ''}`} role="status" aria-live="polite">
        <CheckCircle2 aria-hidden="true" />
        <span>{feedback}</span>
      </div>
    </div>
  )
}

function ComparisonBar({ concept, onChange }: { concept: Concept; onChange: (next: Concept) => void }) {
  return (
    <div className="comparison-bar">
      <div className="preview-label">
        <span className="preview-dot" />
        交互样机 · 独立预览
      </div>
      <div className="concept-switcher" aria-label="设计方案切换">
        <button className={concept === 'bright' ? 'is-active' : ''} onClick={() => onChange('bright')}>
          方案一 · 明亮企业
        </button>
        <button className={concept === 'ops' ? 'is-active' : ''} onClick={() => onChange('ops')}>
          方案二 · 深色运维
        </button>
      </div>
      <div className="preview-meta">
        <span>{concept === 'bright' ? '明亮企业工作台' : '深色运维指挥台'}</span>
        <span className="preview-safe">不连接生产数据</span>
      </div>
    </div>
  )
}

function Sidebar({
  concept,
  surface,
  collapsed,
  onToggle,
  onNavigate,
}: {
  concept: Concept
  surface: Surface
  collapsed: boolean
  onToggle: () => void
  onNavigate: (next: Surface) => void
}) {
  const qualityItems = navItems.filter((item) => item.group === 'quality')
  const engineeringItems = navItems.filter((item) => item.group === 'engineering')

  const renderGroup = (label: string, items: typeof navItems) => (
    <div className="nav-group">
      <div className="nav-group-label">{label}</div>
      {items.map((item) => {
        const Icon = item.icon
        return (
          <button
            key={item.id}
            className={`nav-item ${surface === item.id ? 'is-active' : ''}`}
            aria-current={surface === item.id ? 'page' : undefined}
            aria-label={item.label}
            title={collapsed ? item.label : undefined}
            onClick={() => onNavigate(item.id)}
          >
            <Icon aria-hidden="true" />
            <span>{item.label}</span>
            {item.id === 'execution' && concept === 'ops' && <i className="live-marker" aria-label="3 个任务运行中">3</i>}
          </button>
        )
      })}
    </div>
  )

  return (
    <aside className="sidebar" aria-label="主导航">
      <div className="brand">
        <span className="brand-mark"><TestTube2 aria-hidden="true" /></span>
        <span className="brand-copy">
          <b>CamelTv</b>
          <small>测试平台</small>
        </span>
      </div>

      <nav className="nav-scroll">
        {renderGroup('质量协作', qualityItems)}
        {renderGroup('工程能力', engineeringItems)}
      </nav>

      <div className="sidebar-footer">
        <button className="nav-item">
          <Settings aria-hidden="true" />
          <span>系统设置</span>
        </button>
        <button className="collapse-button" onClick={onToggle} aria-label={collapsed ? '展开导航' : '收起导航'}>
          {collapsed ? <ChevronRight aria-hidden="true" /> : <ChevronLeft aria-hidden="true" />}
          <span>{collapsed ? '' : '收起'}</span>
        </button>
      </div>
    </aside>
  )
}

function Topbar({
  concept,
  project,
  environment,
  onProjectChange,
  onEnvironmentChange,
  onOpenCommand,
}: {
  concept: Concept
  project: string
  environment: string
  onProjectChange: (next: string) => void
  onEnvironmentChange: (next: string) => void
  onOpenCommand: () => void
}) {
  return (
    <header className="topbar">
      <div className="context-controls">
        {concept === 'ops' && <span className="environment-signal" aria-hidden="true" />}
        <label>
          <span className="control-label">当前项目</span>
          <span className="select-wrap">
            <select value={project} onChange={(event) => onProjectChange(event.target.value)} aria-label="当前项目">
              <option>CamelTv 核心平台</option>
              <option>海外业务平台</option>
              <option>增长实验项目</option>
            </select>
            <ChevronDown aria-hidden="true" />
          </span>
        </label>
        <label>
          <span className="control-label">执行环境</span>
          <span className="select-wrap">
            <select value={environment} onChange={(event) => onEnvironmentChange(event.target.value)} aria-label="执行环境">
              <option>测试环境</option>
              <option>预发环境</option>
              <option>生产环境</option>
            </select>
            <ChevronDown aria-hidden="true" />
          </span>
        </label>
      </div>

      <div className="topbar-actions">
        <button className="command-trigger" onClick={onOpenCommand}>
          <Search aria-hidden="true" />
          <span>搜索用例、接口、任务</span>
          <kbd>⌘ K</kbd>
        </button>
        <button className="icon-button" aria-label="通知">
          <Bell aria-hidden="true" />
          <i>12</i>
        </button>
        <button className="profile-button">
          <span className="avatar">张</span>
          <span>张三</span>
          <ChevronDown aria-hidden="true" />
        </button>
      </div>
    </header>
  )
}

function PageHeading({
  surface,
  concept,
  paused,
  onCreate,
  onPause,
  onRetry,
}: {
  surface: Surface
  concept: Concept
  paused: boolean
  onCreate: () => void
  onPause: () => void
  onRetry: () => void
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="breadcrumbs">项目空间 / {surfaceTitle(surface)}</div>
        <div className="heading-line">
          <h1>{surfaceTitle(surface)}</h1>
          {surface === 'execution' && <StatusPill status={paused ? '阻塞' : '运行中'} label={paused ? '已暂停' : '实时更新'} />}
        </div>
        <p>{surfaceDescriptions[surface]}</p>
      </div>
      <div className="page-actions">
        {surface === 'execution' ? (
          <>
            <button className="secondary-button" aria-label={paused ? '继续当前执行' : '暂停当前执行'} onClick={onPause}>
              {paused ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}
              {paused ? '继续' : '暂停'}
            </button>
            <button className="primary-button" onClick={onRetry}>
              <RefreshCw aria-hidden="true" />
              重试
            </button>
          </>
        ) : surface === 'cases' ? (
          <button className="primary-button" onClick={onCreate}>
            <Plus aria-hidden="true" />
            新建用例
          </button>
        ) : (
          <button className="secondary-button">
            <Maximize2 aria-hidden="true" />
            {concept === 'ops' ? '全屏值守' : '自定义视图'}
          </button>
        )}
      </div>
    </div>
  )
}

function OverviewView({
  concept,
  selectedRunId,
  onSelectRun,
}: {
  concept: Concept
  selectedRunId: string
  onSelectRun: (id: string) => void
}) {
  return (
    <div className="overview-stack">
      <div className="metrics-strip">
        <Metric label={concept === 'ops' ? '今日执行' : '执行中'} value="128" delta="较昨日 +12" tone="blue" />
        <Metric label="通过率" value="78.4%" delta="较昨日 +3.6%" tone="green" />
        <Metric label="失败" value="14" delta="需优先处理" tone="red" />
        <Metric label="阻塞" value="6" delta="2 个等待环境" tone="amber" />
      </div>

      <div className="overview-grid">
        <section className="panel trend-panel">
          <div className="panel-heading">
            <div>
              <h2>质量趋势</h2>
              <p>近 7 天执行通过率</p>
            </div>
            <button className="text-button">查看报告 <ChevronRight aria-hidden="true" /></button>
          </div>
          <MiniTrendChart />
        </section>
        <section className="panel activity-panel">
          <div className="panel-heading"><h2>活动动态</h2><button className="text-button">全部</button></div>
          <ActivityFeed />
        </section>
      </div>

      <section className="panel table-panel">
        <div className="panel-heading">
          <div><h2>{concept === 'ops' ? '执行队列' : '最近执行'}</h2><p>跨 API、UI 与计划任务统一追踪</p></div>
          <div className="compact-actions">
            <button className="secondary-button"><Columns2 aria-hidden="true" />列设置</button>
            <button className="icon-button" aria-label="刷新列表"><RefreshCw aria-hidden="true" /></button>
          </div>
        </div>
        <RunTable rows={runs.slice(0, 4)} selectedRunId={selectedRunId} onSelectRun={onSelectRun} />
      </section>
    </div>
  )
}

function CasesView({
  concept,
  rows,
  selectedCaseId,
  search,
  status,
  onSearchChange,
  onStatusChange,
  onSelectCase,
  onCreate,
}: {
  concept: Concept
  rows: CaseRecord[]
  selectedCaseId: string
  search: string
  status: string
  onSearchChange: (value: string) => void
  onStatusChange: (value: string) => void
  onSelectCase: (id: string) => void
  onCreate: () => void
}) {
  return (
    <div className="cases-layout">
      <aside className="panel taxonomy-panel">
        <div className="panel-heading"><h2>模块分类</h2><button className="icon-button" aria-label="管理分类"><Settings aria-hidden="true" /></button></div>
        <div className="tree-list">
          <button className="is-active"><FolderTree aria-hidden="true" /><span>全部用例</span><b>2,345</b></button>
          <button><ChevronRight aria-hidden="true" /><span>账号模块</span><b>342</b></button>
          <button><ChevronRight aria-hidden="true" /><span>首页模块</span><b>186</b></button>
          <button><ChevronRight aria-hidden="true" /><span>搜索模块</span><b>274</b></button>
          <button><ChevronRight aria-hidden="true" /><span>播放模块</span><b>518</b></button>
        </div>
      </aside>

      <section className="panel cases-panel">
        <div className="filter-row">
          <label className="search-field">
            <Search aria-hidden="true" />
            <input value={search} onChange={(event) => onSearchChange(event.target.value)} placeholder="搜索标题、编号或模块" aria-label="搜索用例" />
          </label>
          <select value={status} onChange={(event) => onStatusChange(event.target.value)} aria-label="用例状态">
            <option>全部状态</option><option>通过</option><option>失败</option><option>运行中</option><option>阻塞</option><option>未执行</option>
          </select>
          <select aria-label="优先级"><option>全部优先级</option><option>P0</option><option>P1</option><option>P2</option></select>
          <button className="secondary-button"><Settings aria-hidden="true" />高级筛选</button>
          <span className="filter-spacer" />
          {concept === 'ops' && <button className="secondary-button"><Play aria-hidden="true" />批量执行</button>}
          <button className="primary-button compact-create" onClick={onCreate}><Plus aria-hidden="true" />新建</button>
        </div>

        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th><input type="checkbox" aria-label="全选用例" /></th><th>用例编号</th><th>用例标题</th><th>所属模块</th><th>优先级</th><th>执行状态</th><th>负责人</th><th>更新时间</th><th aria-label="操作" /></tr></thead>
            <tbody>
              {rows.map((item) => (
                <tr key={item.id} className={selectedCaseId === item.id ? 'is-selected' : ''}>
                  <td><input type="checkbox" aria-label={`选择 ${item.id}`} /></td>
                  <td><button className="row-link" onClick={() => onSelectCase(item.id)}>{item.id}</button></td>
                  <td>{item.title}</td><td>{item.module}</td><td><PriorityPill value={item.priority} /></td>
                  <td><StatusPill status={item.status} /></td><td>{item.owner}</td><td>{item.updatedAt}</td>
                  <td><button className="icon-button row-action" aria-label={`查看 ${item.id}`} onClick={() => onSelectCase(item.id)}><MoreHorizontal aria-hidden="true" /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pagination"><span>共 {rows.length || 0} 条筛选结果</span><span className="filter-spacer" /><button disabled><ChevronLeft aria-hidden="true" /></button><button className="is-active">1</button><button>2</button><button>3</button><button><ChevronRight aria-hidden="true" /></button></div>
      </section>
    </div>
  )
}

function ExecutionView({
  concept,
  selectedRun,
  selectedRunId,
  paused,
  logLevel,
  visibleLogs,
  onSelectRun,
  onLogLevelChange,
  onPause,
  onRetry,
}: {
  concept: Concept
  selectedRun: RunRecord
  selectedRunId: string
  paused: boolean
  logLevel: LogLevel
  visibleLogs: typeof logLines[number][]
  onSelectRun: (id: string) => void
  onLogLevelChange: (value: LogLevel) => void
  onPause: () => void
  onRetry: () => void
}) {
  return (
    <div className={`execution-grid ${concept === 'ops' ? 'is-ops' : ''}`}>
      <div className="execution-main">
        <div className="run-summary">
          <div className="run-ring"><b>{paused ? 'Ⅱ' : '58%'}</b><span>{paused ? '已暂停' : '执行进度'}</span></div>
          <div className="run-stat"><StatusPill status="通过" /><b>68</b><small>56.7%</small></div>
          <div className="run-stat"><StatusPill status="失败" /><b>10</b><small>8.3%</small></div>
          <div className="run-stat"><StatusPill status="运行中" /><b>{paused ? 0 : 18}</b><small>14.1%</small></div>
          <div className="summary-chart"><MiniBarChart /></div>
        </div>

        <section className="panel table-panel execution-table-panel">
          <div className="panel-heading">
            <div><h2>执行队列</h2><p>状态变化会同步到详情与实时日志</p></div>
            <div className="compact-actions"><button className="secondary-button" onClick={onPause}>{paused ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}{paused ? '继续' : '暂停'}</button><button className="secondary-button" onClick={onRetry}><RefreshCw aria-hidden="true" />重试</button></div>
          </div>
          <RunTable rows={runs} selectedRunId={selectedRunId} onSelectRun={onSelectRun} />
        </section>

        <div className="operations-bottom">
          <section className="panel request-panel">
            <div className="console-tabs"><button className="is-active">API 请求</button><button>执行步骤</button><button>测试数据</button></div>
            <div className="request-line"><span>POST</span><code>/api/v1/auth/login</code><button>发送</button></div>
            <div className="code-editor"><span>1</span><code>{`{`}</code><span>2</span><code>  <em>"username"</em>: <strong>"test_admin"</strong>,</code><span>3</span><code>  <em>"password"</em>: <strong>"••••••••"</strong></code><span>4</span><code>{`}`}</code></div>
          </section>
          <section className="panel log-panel">
            <div className="console-tabs">
              <button className="is-active">实时日志</button><button>运行步骤</button><button>产物</button>
              <select value={logLevel} onChange={(event) => onLogLevelChange(event.target.value as LogLevel)} aria-label="日志级别"><option>ALL</option><option>INFO</option><option>WARN</option><option>DEBUG</option></select>
            </div>
            <div className="log-lines" aria-live="polite">
              {visibleLogs.map(([level, time, message]) => <div key={`${time}-${message}`}><time>{time}</time><b className={`log-${level.toLowerCase()}`}>{level}</b><span>{message}</span></div>)}
            </div>
          </section>
        </div>
      </div>

      <RunInspector selectedRun={selectedRun} paused={paused} onPause={onPause} onRetry={onRetry} />
    </div>
  )
}

function ApiView({ apiSending, apiSent, onSend }: { apiSending: boolean; apiSent: boolean; onSend: () => void }) {
  return (
    <div className="api-workspace">
      <aside className="panel endpoint-tree">
        <div className="panel-heading"><h2>接口资产</h2><button className="icon-button" aria-label="新建接口"><Plus aria-hidden="true" /></button></div>
        <label className="search-field"><Search aria-hidden="true" /><input aria-label="搜索接口" placeholder="搜索接口或目录" /></label>
        <div className="endpoint-list"><button><ChevronDown aria-hidden="true" /><b>用户中心</b><i>12</i></button><button className="endpoint is-active"><span>POST</span>/api/v1/login</button><button className="endpoint"><span>GET</span>/api/v1/user/info</button><button className="endpoint"><span>POST</span>/api/v1/logout</button><button><ChevronRight aria-hidden="true" /><b>内容服务</b><i>18</i></button></div>
      </aside>

      <section className="panel api-editor">
        <div className="api-tabs"><button className="is-active"><i /> POST 登录接口</button><button>GET 用户信息</button><button aria-label="新建标签"><Plus aria-hidden="true" /></button></div>
        <div className="api-address"><select aria-label="请求方法"><option>POST</option><option>GET</option></select><input aria-label="请求地址" defaultValue="{{baseUrl}}/api/v1/login" /><button className="primary-button" disabled={apiSending} onClick={onSend}>{apiSending ? <Loader2 className="spin" aria-hidden="true" /> : <Send aria-hidden="true" />}{apiSending ? '发送中' : '发送'}</button></div>
        <div className="editor-tabs"><button>Params</button><button>Headers <i>9</i></button><button className="is-active">Body <i>1</i></button><button>Pre-request</button><button>Tests</button></div>
        <div className="body-type"><label><input type="radio" name="body-type" /> none</label><label><input type="radio" name="body-type" /> form-data</label><label><input type="radio" name="body-type" defaultChecked /> raw</label><select aria-label="请求体格式"><option>JSON</option></select></div>
        <div className="code-editor api-code"><span>1</span><code>{`{`}</code><span>2</span><code>  <em>"username"</em>: <strong>"test_admin"</strong>,</code><span>3</span><code>  <em>"password"</em>: <strong>"••••••••"</strong>,</code><span>4</span><code>  <em>"remember"</em>: <strong>true</strong></code><span>5</span><code>{`}`}</code></div>
      </section>

      <section className="panel response-panel">
        <div className="panel-heading"><h2>响应</h2><div className="response-meta"><b>{apiSent ? '200 OK' : '等待发送'}</b>{apiSent && <><span>132 ms</span><span>1.23 KB</span></>}</div></div>
        <div className="editor-tabs"><button className="is-active">Pretty</button><button>Raw</button><button>Preview</button></div>
        {apiSent ? (
          <div className="code-editor response-code"><span>1</span><code>{`{`}</code><span>2</span><code>  <em>"code"</em>: <strong>200</strong>,</code><span>3</span><code>  <em>"message"</em>: <strong>"success"</strong>,</code><span>4</span><code>  <em>"data"</em>: {`{`}</code><span>5</span><code>    <em>"token"</em>: <strong>"eyJhbGci..."</strong></code><span>6</span><code>  {`}`}</code><span>7</span><code>{`}`}</code></div>
        ) : (
          <div className="response-empty"><FlaskConical aria-hidden="true" /><b>发送请求后查看响应</b><span>状态码、耗时和断言结果会显示在这里</span></div>
        )}
      </section>
    </div>
  )
}

function ModuleView({ surface, onNavigate }: { surface: Surface; onNavigate: (next: Surface) => void }) {
  const lanes = surface === 'requirement'
    ? [['等待解析', '12'], ['评审中', '8'], ['已确认', '36'], ['已归档', '128']]
    : surface === 'plan'
      ? [['草稿', '6'], ['待执行', '14'], ['执行中', '3'], ['已完成', '82']]
      : surface === 'defect'
        ? [['待确认', '11'], ['修复中', '19'], ['待回归', '8'], ['已关闭', '126']]
        : [['今日新增', '18'], ['处理中', '24'], ['待审核', '7'], ['已完成', '96']]

  return (
    <div className="module-surface">
      <section className="workflow-strip">
        {lanes.map(([label, value], index) => <div key={label}><span>{index + 1}</span><b>{label}</b><strong>{value}</strong>{index < lanes.length - 1 && <ChevronRight aria-hidden="true" />}</div>)}
      </section>
      <div className="module-grid">
        <section className="panel module-list"><div className="panel-heading"><div><h2>{surfaceTitle(surface)}列表</h2><p>该模块保留自己的字段、状态和操作方式</p></div><button className="primary-button"><Plus aria-hidden="true" />新建</button></div><div className="skeleton-table">{[0, 1, 2, 3, 4].map((row) => <button key={row}><i /><span><b>{surfaceTitle(surface)}记录 #{1024 + row}</b><small>模块专属字段与说明内容</small></span><StatusPill status={row === 1 ? '失败' : row === 3 ? '运行中' : '通过'} /><ChevronRight aria-hidden="true" /></button>)}</div></section>
        <section className="panel module-context"><div className="context-hero"><FileText aria-hidden="true" /><h2>保留模块差异</h2><p>两套设计只统一导航、层级、反馈和组件语言，不强行统一各模块的信息结构。</p></div><button className="secondary-button" onClick={() => onNavigate('api')}><FlaskConical aria-hidden="true" />查看编辑型交互</button><button className="secondary-button" onClick={() => onNavigate('execution')}><Terminal aria-hidden="true" />查看运行型交互</button></section>
      </div>
    </div>
  )
}

function RunTable({ rows, selectedRunId, onSelectRun }: { rows: RunRecord[]; selectedRunId: string; onSelectRun: (id: string) => void }) {
  return (
    <div className="table-scroll">
      <table className="data-table run-table">
        <thead><tr><th>ID</th><th>任务 / 计划名称</th><th>类型</th><th>状态</th><th>优先级</th><th>执行环境</th><th>执行人</th><th>开始时间</th><th>耗时</th><th aria-label="操作" /></tr></thead>
        <tbody>{rows.map((run) => <tr key={run.id} className={selectedRunId === run.id ? 'is-selected' : ''}><td><button className="row-link" onClick={() => onSelectRun(run.id)}>{run.id}</button></td><td>{run.title}</td><td>{run.type}</td><td><StatusPill status={run.status} /></td><td><PriorityPill value={run.priority} /></td><td>{run.environment}</td><td>{run.owner}</td><td>{run.startedAt.slice(5)}</td><td className="numeric">{run.duration}</td><td><button className="icon-button row-action" aria-label={`查看 ${run.id}`} onClick={() => onSelectRun(run.id)}><Eye aria-hidden="true" /></button></td></tr>)}</tbody>
      </table>
    </div>
  )
}

function RunInspector({ selectedRun, paused, onPause, onRetry }: { selectedRun: RunRecord; paused: boolean; onPause: () => void; onRetry: () => void }) {
  return (
    <aside className="run-inspector" aria-label="执行详情">
      <div className="inspector-header"><div><small>执行详情</small><h2>{selectedRun.title}</h2><code>{selectedRun.id}</code></div><StatusPill status={paused ? '阻塞' : selectedRun.status} label={paused ? '已暂停' : selectedRun.status} /></div>
      <div className="inspector-actions"><button aria-label={paused ? '继续详情任务' : '暂停详情任务'} onClick={onPause}>{paused ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}{paused ? '继续' : '暂停'}</button><button onClick={onRetry}><RefreshCw aria-hidden="true" />重试</button><button className="is-primary"><BarChart3 aria-hidden="true" />查看报告</button></div>
      <div className="inspector-tabs"><button className="is-active">概览</button><button>详情</button><button>关联缺陷</button><button>附件</button></div>
      <dl className="detail-list"><div><dt>执行环境</dt><dd>{selectedRun.environment}</dd></div><div><dt>执行人</dt><dd>{selectedRun.owner}</dd></div><div><dt>开始时间</dt><dd>{selectedRun.startedAt}</dd></div><div><dt>耗时</dt><dd>{selectedRun.duration}</dd></div><div><dt>优先级</dt><dd><PriorityPill value={selectedRun.priority} /></dd></div><div><dt>触发方式</dt><dd>手动触发</dd></div></dl>
      <div className="progress-section"><div><span>进度</span><b>{paused ? selectedRun.progress : selectedRun.progress}%</b></div><div className="progress-track"><i style={{ width: `${selectedRun.progress}%` }} /></div></div>
      <div className="artifact-list"><h3>产物</h3><button><FileText aria-hidden="true" /><span><b>测试报告</b><small>生成中 · 60%</small></span><ChevronRight aria-hidden="true" /></button><button><Database aria-hidden="true" /><span><b>日志文件</b><small>18.3 MB</small></span><ChevronRight aria-hidden="true" /></button><button><MonitorIcon /><span><b>截图</b><small>120 张</small></span><ChevronRight aria-hidden="true" /></button></div>
    </aside>
  )
}

function MonitorIcon() {
  return <Eye aria-hidden="true" />
}

function ContextDrawer({ mode, concept, selectedCase, selectedRun, surface, onClose, onSave }: { mode: Exclude<DrawerMode, null>; concept: Concept; selectedCase: CaseRecord; selectedRun: RunRecord; surface: Surface; onClose: () => void; onSave: () => void }) {
  const isCreate = mode === 'create'
  return (
    <aside className="context-drawer" aria-label={isCreate ? '新建用例' : '详情面板'}>
      <div className="drawer-header"><div><small>{concept === 'bright' ? '保持列表上下文' : '快速检查'}</small><h2>{isCreate ? '新建用例' : surface === 'cases' ? selectedCase.title : selectedRun.title}</h2></div><button className="icon-button" aria-label="关闭详情" onClick={onClose}><XCircle aria-hidden="true" /></button></div>
      {isCreate ? <CaseForm /> : surface === 'cases' ? <CaseDetail selectedCase={selectedCase} /> : <RunDetail selectedRun={selectedRun} />}
      <div className="drawer-footer"><button className="secondary-button" onClick={onClose}>取消</button><button className="primary-button" onClick={onSave}>{isCreate ? '创建草稿' : '保存修改'}</button></div>
    </aside>
  )
}

function CaseForm() {
  return <div className="drawer-body form-stack"><label><span>用例标题</span><input autoFocus placeholder="请输入清晰、可检索的标题" /></label><div className="form-grid"><label><span>所属模块</span><select><option>账号模块</option><option>首页模块</option><option>播放模块</option></select></label><label><span>优先级</span><select><option>P0</option><option>P1</option><option>P2</option></select></label></div><label><span>前置条件</span><textarea rows={3} defaultValue="用户已进入登录页面" /></label><label><span>操作步骤</span><textarea rows={6} defaultValue={'1. 输入正确账号\n2. 输入正确密码\n3. 点击登录按钮'} /></label><label><span>预期结果</span><textarea rows={3} defaultValue="成功进入工作台，并记录登录审计日志" /></label></div>
}

function CaseDetail({ selectedCase }: { selectedCase: CaseRecord }) {
  return <div className="drawer-body"><div className="detail-hero"><code>{selectedCase.id}</code><StatusPill status={selectedCase.status} /></div><dl className="detail-list"><div><dt>所属模块</dt><dd>{selectedCase.module}</dd></div><div><dt>优先级</dt><dd><PriorityPill value={selectedCase.priority} /></dd></div><div><dt>负责人</dt><dd>{selectedCase.owner}</dd></div><div><dt>更新时间</dt><dd>2025-05-16 {selectedCase.updatedAt}</dd></div></dl><div className="detail-section"><h3>操作步骤</h3><ol><li>打开登录页面</li><li>输入正确的账号与密码</li><li>点击登录并等待页面跳转</li></ol></div><div className="detail-section"><h3>预期结果</h3><p>成功进入工作台，用户信息与项目权限加载正确。</p></div></div>
}

function RunDetail({ selectedRun }: { selectedRun: RunRecord }) {
  return <div className="drawer-body"><div className="detail-hero"><code>{selectedRun.id}</code><StatusPill status={selectedRun.status} /></div><dl className="detail-list"><div><dt>任务类型</dt><dd>{selectedRun.type}</dd></div><div><dt>执行环境</dt><dd>{selectedRun.environment}</dd></div><div><dt>执行人</dt><dd>{selectedRun.owner}</dd></div><div><dt>耗时</dt><dd>{selectedRun.duration}</dd></div></dl></div>
}

function CommandPalette({ onClose, onNavigate }: { onClose: () => void; onNavigate: (next: Surface) => void }) {
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="command-dialog" role="dialog" aria-modal="true" aria-label="全局命令" onMouseDown={(event) => event.stopPropagation()}>
        <div className="command-input"><Search aria-hidden="true" /><input autoFocus placeholder="搜索页面或执行命令…" aria-label="搜索命令" /><kbd>ESC</kbd></div>
        <div className="command-section"><span>快速前往</span>{navItems.slice(0, 6).map((item) => { const Icon = item.icon; return <button key={item.id} onClick={() => onNavigate(item.id)}><Icon aria-hidden="true" /><span>{item.label}</span><small>{surfaceDescriptions[item.id]}</small><kbd>↵</kbd></button> })}</div>
        <div className="command-footer"><span><Key aria-hidden="true" />支持键盘导航</span><span>独立原型不会执行真实操作</span></div>
      </div>
    </div>
  )
}

function EnvironmentDialog({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: () => void }) {
  return (
    <div className="modal-backdrop">
      <div className="confirm-dialog" role="dialog" aria-modal="true" aria-label="切换到生产环境">
        <span className="warning-icon"><AlertTriangle aria-hidden="true" /></span><h2>切换到生产环境</h2><p>生产环境会启用更严格的运行保护和操作确认。此原型不会发送真实请求。</p><div className="confirm-note"><b>将发生的变化</b><span>环境标签变为生产环境</span><span>执行与删除操作增加二次确认</span></div><div className="dialog-actions"><button className="secondary-button" onClick={onCancel}>取消</button><button className="danger-button" onClick={onConfirm}>确认切换</button></div>
      </div>
    </div>
  )
}

function Metric({ label, value, delta, tone }: { label: string; value: string; delta: string; tone: string }) {
  return <div className={`metric metric-${tone}`}><span>{label}</span><div><b>{value}</b><MiniSpark tone={tone} /></div><small>{delta}</small></div>
}

function MiniSpark({ tone }: { tone: string }) {
  return <svg className={`spark spark-${tone}`} viewBox="0 0 90 30" role="img" aria-label="趋势上升"><path d="M2 24 L14 19 L25 21 L36 13 L47 16 L58 7 L69 11 L79 4 L88 9" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
}

function MiniTrendChart() {
  return <div className="trend-chart"><div className="chart-y"><span>100%</span><span>75%</span><span>50%</span><span>25%</span></div><svg viewBox="0 0 600 150" preserveAspectRatio="none" role="img" aria-label="近七天通过率从 62% 上升到 78%"><defs><linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="currentColor" stopOpacity="0.18"/><stop offset="1" stopColor="currentColor" stopOpacity="0"/></linearGradient></defs><path className="trend-area" d="M0 116 L100 98 L200 78 L300 56 L400 88 L500 48 L600 66 L600 150 L0 150 Z" fill="url(#trend-fill)"/><path className="trend-line" d="M0 116 L100 98 L200 78 L300 56 L400 88 L500 48 L600 66" fill="none" stroke="currentColor" strokeWidth="3" vectorEffect="non-scaling-stroke"/>{[0,100,200,300,400,500,600].map((x, index) => <circle key={x} cx={x} cy={[116,98,78,56,88,48,66][index]} r="4" fill="currentColor" />)}</svg><div className="chart-x"><span>05-10</span><span>05-11</span><span>05-12</span><span>05-13</span><span>05-14</span><span>05-15</span><span>05-16</span></div></div>
}

function MiniBarChart() {
  return <div className="mini-bars" aria-label="近七次执行通过与失败数量">{[52,72,68,61,76,58,82,70,65,88,73].map((height, index) => <i key={index} style={{ height: `${height}%` }}><b style={{ height: `${Math.max(8, 34 - index * 2)}%` }} /></i>)}</div>
}

function ActivityFeed() {
  return <div className="activity-feed"><div><i className="dot-blue" /><span>接口自动化计划执行完成</span><time>2 分钟前</time></div><div><i className="dot-red" /><span>用例 TC-21034 执行失败</span><time>6 分钟前</time></div><div><i className="dot-green" /><span>缺陷 BUG-1056 已修复</span><time>15 分钟前</time></div><div><i className="dot-amber" /><span>需求 REQ-3021 状态更新</span><time>30 分钟前</time></div></div>
}

function StatusPill({ status, label }: { status: Status; label?: string }) {
  return <span className={`status-pill status-${status}`}>{status === '通过' && <CheckCircle2 aria-hidden="true" />}{status === '失败' && <XCircle aria-hidden="true" />}{status === '运行中' && <span className="pulse-dot" />}{status === '阻塞' && <AlertTriangle aria-hidden="true" />}{status === '未执行' && <Clock aria-hidden="true" />}{label ?? status}</span>
}

function PriorityPill({ value }: { value: CaseRecord['priority'] | RunRecord['priority'] }) {
  return <span className={`priority-pill priority-${value}`}>{value}</span>
}
