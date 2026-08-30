import { lazy, Suspense, useState, type FormEvent, type ReactNode } from 'react'
import { createBrowserRouter, Navigate, useNavigate } from 'react-router'
import { Loader2 } from '@/lib/icons'
import MainLayout from '@/layouts/MainLayout'
import NotFound from '@/pages/NotFound'
import Unavailable from '@/pages/Unavailable'
import RequireAuth from './guard'
import { isThemeLabEnabled } from './themeLabAvailability'
import { AITDE_V3_ENABLED } from '@/config/aitde'
import client from '@/api/client'
import { logoutApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { Button, Input } from '@/ui'

const LoginPage = lazy(() => import('@/pages/login'))
const RegisterPage = lazy(() => import('@/pages/register'))
const MyProjectsPage = lazy(() => import('@/pages/my-projects'))
const SystemPage = lazy(() => import('@/pages/system'))
const TestCasePage = lazy(() => import('@/pages/testcase'))
const TestPlanPage = lazy(() => import('@/pages/testplan'))
const PlanDetail = lazy(() => import('@/pages/testplan/PlanDetail'))
const ReportPage = lazy(() => import('@/pages/report'))
const SchedulePage = lazy(() => import('@/pages/schedule'))
const Workbench = lazy(() => import('@/pages/workbench'))
const DefectPage = lazy(() => import('@/pages/defect'))
const UiTestPage = lazy(() => import('@/pages/uitest'))
const RequirementPage = lazy(() => import('@/pages/requirement'))
const RequirementReviewPage = lazy(() => import('@/pages/requirement/ReviewPage'))
const ApiTestPage = lazy(() => import('@/pages/apitest'))
const NotifyPage = lazy(() => import('@/pages/notify'))
const EnvironmentPage = lazy(() => import('@/pages/environment'))
const DatasetPage = lazy(() => import('@/pages/dataset'))
const IntegrationPage = lazy(() => import('@/pages/integration'))
const KnowledgePage = lazy(() => import('@/pages/knowledge'))
const DshTasksPage = lazy(() => import('@/pages/dsh-tasks'))
const AiConfigPage = lazy(() => import('@/pages/ai-config'))
const ReleaseBundlesPage = lazy(() => import('@/pages/release-bundles'))
const BundleDetailPage = lazy(() => import('@/pages/release-bundles/BundleDetail'))
const VersionPanoramaPage = lazy(() => import('@/pages/release-bundles/VersionPanorama'))
const ThemeLabPage = lazy(() => import('@/theme-lab/ThemeLab').then(m => ({ default: m.ThemeLab })))
const LanhuEvidencePage = lazy(() => import('@/pages/lanhu-evidence'))
const LanhuEvidenceJobDetail = lazy(() => import('@/pages/lanhu-evidence/JobDetail'))
const MissionListPage = lazy(() => import('@/pages/missions'))
const MissionCreatePage = lazy(() => import('@/pages/missions/CreateMissionPage'))
const MissionLayout = lazy(() => import('@/pages/missions/MissionLayout'))
const MissionOverviewPage = lazy(() => import('@/pages/missions/overview'))
const MissionSourcesPage = lazy(() => import('@/pages/missions/sources'))
const MissionScopePage = lazy(() => import('@/pages/missions/scope'))
const MissionContractPage = lazy(() => import('@/pages/missions/contract'))
const MissionScenariosPage = lazy(() => import('@/pages/missions/scenarios'))
const MissionDataPage = lazy(() => import('@/pages/missions/data'))
const ScenarioLayout = lazy(() => import('@/pages/missions/ScenarioLayout'))
const MissionManualPage = lazy(() => import('@/pages/missions/manual'))
const ObservatePage = lazy(() => import('@/pages/missions/observe'))
const MissionActionPlanPage = lazy(() => import('@/pages/missions/action-plan'))
const HybridRunPage = lazy(() => import('@/pages/missions/hybrid-run'))
const MissionBuildsPage = lazy(() => import('@/pages/missions/builds'))
const MissionAcceptancePage = lazy(() => import('@/pages/missions/acceptance'))
const MissionChangesPage = lazy(() => import('@/pages/missions/changes'))
const MissionImpactPage = lazy(() => import('@/pages/missions/impact'))
const MissionTracePage = lazy(() => import('@/pages/missions/trace'))
const MissionGapsPage = lazy(() => import('@/pages/missions/gaps'))
const AiSuggestionsPage = lazy(() => import('@/pages/ai-suggestions'))
const FlakyPage = lazy(() => import('@/pages/flaky'))
const AiEvaluationsPage = lazy(() => import('@/pages/admin/ai-evaluations'))
const RegressionSelectionPage = lazy(() => import('@/pages/regression-selections'))
const CampaignDetailPage = lazy(() => import('@/pages/campaigns/CampaignDetail'))
const HealingReviewPage = lazy(() => import('@/pages/healing'))
const DataSourcesPage = lazy(() => import('@/pages/data-sources'))
const FixturesPage = lazy(() => import('@/pages/fixtures'))
const FixtureDetailPage = lazy(() => import('@/pages/fixtures/[fixtureId]'))
const ExecutionCenterPage = lazy(() => import('@/pages/executions'))
const RunDetailPage = lazy(() => import('@/pages/executions/run/[runId]'))
const ReplayPage = lazy(() => import('@/pages/executions/replay'))
const MissionExecutionsPage = lazy(() => import('@/pages/executions/mission'))
const RuntimeAdminPage = lazy(() => import('@/pages/runtime'))
const ProductionEvidencePage = lazy(() => import('@/pages/production'))
const ProductionJourneysPage = lazy(() => import('@/pages/production/journeys'))
const ProductionTemplatesPage = lazy(() => import('@/pages/production/templates'))
const ProductionMaskingPage = lazy(() => import('@/pages/production/masking'))
const MissionProductionEvidencePage = lazy(() => import('@/pages/production/missionEvidence'))
const themeLabEnabled = isThemeLabEnabled(import.meta.env.DEV, import.meta.env.VITE_ENABLE_THEME_LAB)

function PageLoader({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="grid min-h-[280px] place-items-center">
          <Loader2 className="size-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      {children}
    </Suspense>
  )
}

export function PasswordChangeBoundary({ children }: { children: ReactNode }) {
  const mustChangePassword = useAuthStore((state) => state.mustChangePassword)
  if (mustChangePassword) return <Navigate to="/change-password" replace />
  return <>{children}</>
}

function PlatformHomeEntry() {
  const user = useAuthStore((state) => state.user)
  return user ? <Navigate to="/workbench" replace /> : null
}

function ForcedPasswordChangePage() {
  const navigate = useNavigate()
  const mustChangePassword = useAuthStore((state) => state.mustChangePassword)
  const completePasswordChange = useAuthStore((state) => state.completePasswordChange)
  const logout = useAuthStore((state) => state.logout)
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  if (!mustChangePassword) return <Navigate to="/workbench" replace />

  const signOut = async () => {
    await logoutApi().catch(() => undefined)
    logout()
    navigate('/login', { replace: true })
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (pending) return
    if (newPassword.length < 6) {
      setError('新密码至少 6 位')
      return
    }
    if (newPassword !== confirmation) {
      setError('两次输入的新密码不一致')
      return
    }
    setPending(true)
    setError('')
    try {
      await client.post('/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
      })
      completePasswordChange()
      await signOut()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '修改密码失败')
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-background p-4">
      <section className="w-full max-w-md rounded-xl border bg-card p-6 text-card-foreground">
        <h1 className="text-xl font-semibold tracking-[-0.02em]">首次登录，请修改密码</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          完成修改前，仅可执行修改密码或退出登录。修改成功后需使用新密码重新登录。
        </p>
        <form className="mt-6 space-y-4" onSubmit={submit} noValidate>
          <div className="space-y-1.5">
            <label htmlFor="forced-old-password" className="text-sm font-medium">原密码</label>
            <Input
              id="forced-old-password"
              type="password"
              autoComplete="current-password"
              value={oldPassword}
              onChange={(event) => setOldPassword(event.target.value)}
              required
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="forced-new-password" className="text-sm font-medium">新密码</label>
            <Input
              id="forced-new-password"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              aria-describedby="forced-password-help"
              required
              minLength={6}
            />
            <p id="forced-password-help" className="text-xs text-muted-foreground">至少 6 位，且不能与原密码相同。</p>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="forced-confirm-password" className="text-sm font-medium">确认新密码</label>
            <Input
              id="forced-confirm-password"
              type="password"
              autoComplete="new-password"
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              required
            />
          </div>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button type="submit" className="flex-1" disabled={pending}>
              {pending ? '修改中…' : '修改密码'}
            </Button>
            <Button type="button" variant="secondary" onClick={() => void signOut()} disabled={pending}>
              退出登录
            </Button>
          </div>
        </form>
      </section>
    </main>
  )
}

export const router = createBrowserRouter([
  { path: '/login', element: <PageLoader><LoginPage /></PageLoader> },
  { path: '/register', element: <PageLoader><RegisterPage /></PageLoader> },
  {
    path: '/change-password',
    element: <RequireAuth><ForcedPasswordChangePage /></RequireAuth>,
  },
  {
    path: '/',
    element: (
      <PasswordChangeBoundary>
        <MainLayout />
      </PasswordChangeBoundary>
    ),
    children: [
      { index: true, element: <PlatformHomeEntry /> },
      { path: 'my-projects', element: <PageLoader><MyProjectsPage /></PageLoader> },
      { path: 'organizations', element: <Navigate to="/my-projects" replace /> },
      { path: 'workbench', element: <PageLoader><Workbench /></PageLoader> },
      // (P2c) 质量追溯已并入报告中心 Tab，旧书签重定向
      { path: 'trace', element: <Navigate to="/report?tab=trace" replace /> },
      { path: 'requirement', element: <PageLoader><RequirementPage /></PageLoader> },
      { path: 'requirement/:id/review', element: <PageLoader><RequirementReviewPage /></PageLoader> },
      { path: 'testcase', element: <PageLoader><TestCasePage /></PageLoader> },
      { path: 'testplan', element: <PageLoader><TestPlanPage /></PageLoader> },
      { path: 'testplan/:id', element: <PageLoader><PlanDetail /></PageLoader> },
      // (P2a) 思维导图已并入用例服务「脑图视图」Tab，旧书签重定向
      { path: 'mindmap', element: <Navigate to="/testcase?tab=mindmap" replace /> },
      { path: 'apitest', element: <PageLoader><ApiTestPage /></PageLoader> },
      { path: 'uitest', element: <PageLoader><UiTestPage /></PageLoader> },
      { path: 'schedule', element: <PageLoader><SchedulePage /></PageLoader> },
      { path: 'defect', element: <PageLoader><DefectPage /></PageLoader> },
      { path: 'defect/:id', element: <PageLoader><DefectPage /></PageLoader> },
      { path: 'report', element: <PageLoader><ReportPage /></PageLoader> },
      { path: 'system', element: <PageLoader><SystemPage /></PageLoader> },
      { path: 'project', element: <Navigate to="/my-projects" replace /> },
      { path: 'notify', element: <PageLoader><NotifyPage /></PageLoader> },
      { path: 'environment', element: <PageLoader><EnvironmentPage /></PageLoader> },
      { path: 'dataset', element: <PageLoader><DatasetPage /></PageLoader> },
      { path: 'integration', element: <PageLoader><IntegrationPage /></PageLoader> },
      { path: 'knowledge', element: <PageLoader><KnowledgePage /></PageLoader> },
      // (P2b) Playground 已并入用例服务 Tab，旧书签重定向
      { path: 'playground', element: <Navigate to="/testcase?tab=playground" replace /> },
      { path: 'dsh-tasks', element: <PageLoader><DshTasksPage /></PageLoader> },
      { path: 'ai-config', element: <PageLoader><AiConfigPage /></PageLoader> },
      { path: 'version-mission', element: <Navigate to="/release-bundles" replace /> },
      { path: 'release-bundles', element: <PageLoader><ReleaseBundlesPage /></PageLoader> },
      { path: 'release-bundles/:id', element: <PageLoader><BundleDetailPage /></PageLoader> },
      { path: 'release-bundles/:id/panorama', element: <PageLoader><VersionPanoramaPage /></PageLoader> },
      // (P1b) Agent 工作台已收敛进 DSH 任务，旧书签重定向
      { path: 'agent-workbench', element: <Navigate to="/dsh-tasks" replace /> },
      { path: 'lanhu-evidence', element: <PageLoader><LanhuEvidencePage /></PageLoader> },
      { path: 'lanhu-evidence/:id', element: <PageLoader><LanhuEvidenceJobDetail /></PageLoader> },
      // ── AITDE V3: Mission 主链（V30-102）──
      {
        path: 'missions',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><MissionListPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="测试任务（Mission）入口需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      {
        path: 'missions/new',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><MissionCreatePage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="测试任务（Mission）入口需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      {
        path: 'missions/:id',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><MissionLayout /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="测试任务（Mission）入口需启用 AITDE V3 功能开关后开放。"
          />
        ),
        children: [
          { index: true, element: <Navigate to="overview" replace /> },
          { path: 'overview', element: <PageLoader><MissionOverviewPage /></PageLoader> },
          { path: 'sources', element: <PageLoader><MissionSourcesPage /></PageLoader> },
          { path: 'scope', element: <PageLoader><MissionScopePage /></PageLoader> },
          { path: 'contract', element: <PageLoader><MissionContractPage /></PageLoader> },
          { path: 'scenarios', element: <PageLoader><MissionScenariosPage /></PageLoader> },
          { path: 'data', element: <PageLoader><MissionDataPage /></PageLoader> },
          { path: 'executions', element: <PageLoader><MissionExecutionsPage /></PageLoader> },
          { path: 'builds', element: <PageLoader><MissionBuildsPage /></PageLoader> },
          { path: 'acceptance', element: <PageLoader><MissionAcceptancePage /></PageLoader> },
          { path: 'changes', element: <PageLoader><MissionChangesPage /></PageLoader> },
          { path: 'impact', element: <PageLoader><MissionImpactPage /></PageLoader> },
          { path: 'trace', element: <PageLoader><MissionTracePage /></PageLoader> },
          { path: 'gaps', element: <PageLoader><MissionGapsPage /></PageLoader> },
        ],
      },
      // ── AITDE V3.8: AI QA Closed Loop（AI Suggestions / Flaky / 模型评估）──
      {
        path: 'ai-suggestions',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><AiSuggestionsPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="AI 建议收件箱需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      {
        path: 'flaky',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><FlakyPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="Flaky 分析需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      {
        path: 'admin/ai-evaluations',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><AiEvaluationsPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="AI 模型评估需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      // ── AITDE V3.5: Campaign 详情（V35-013）──
      {
        path: 'campaigns/:id',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><CampaignDetailPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="Campaign 详情需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      // ── AITDE V3.7: Regression Selection 详情（V37-013）──
      {
        path: 'regression-selections/:id',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><RegressionSelectionPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="回归选择详情需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      // ── AITDE V3.6: Production Evidence & Real-World Data Template（V36-013/014）──
      {
        path: 'production/evidence',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><ProductionEvidencePage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="生产证据需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      {
        path: 'production/journeys',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><ProductionJourneysPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="Production Journey 需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      {
        path: 'production/templates',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><ProductionTemplatesPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="生产模板需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      {
        path: 'admin/masking',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><ProductionMaskingPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="脱敏配置需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      {
        path: 'missions/:id/production-evidence',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><MissionProductionEvidencePage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="Mission 生产证据需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      // ── AITDE V3.3: Browser + Hybrid + Assisted Manual（V33-012..016）──
      {
        path: 'missions/:missionId/scenarios/:scenarioId',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><ScenarioLayout /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="场景执行（Browser / Hybrid / Assisted Manual）需启用 AITDE V3 功能开关后开放。"
          />
        ),
        children: [
          { index: true, element: <Navigate to="manual" replace /> },
          { path: 'manual', element: <PageLoader><MissionManualPage /></PageLoader> },
          { path: 'observe', element: <PageLoader><ObservatePage /></PageLoader> },
          { path: 'action-plan', element: <PageLoader><MissionActionPlanPage /></PageLoader> },
          { path: 'hybrid-run', element: <PageLoader><HybridRunPage /></PageLoader> },
        ],
      },
      {
        path: 'healing',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><HealingReviewPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="愈合评审需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      // ── AITDE V3.1: Unified Execution + Proof Replay（V31-xxx）──
      {
        path: 'executions',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><ExecutionCenterPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="执行中心需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      {
        path: 'executions/:runId',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><RunDetailPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="执行详情需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      {
        path: 'executions/:runId/replay',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><ReplayPage /></PageLoader>
        ) : (
          <Unavailable
            title="AITDE V3 未开放"
            description="执行回放需启用 AITDE V3 功能开关后开放。"
          />
        ),
      },
      // ── AITDE V3.2: Data + DB Runtime（V32-016..V32-018）──
      {
        path: 'data-sources',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><DataSourcesPage /></PageLoader>
        ) : (
          <Unavailable title="AITDE V3 未开放" description="数据源管理需启用 AITDE V3 功能开关后开放。" />
        ),
      },
      {
        path: 'fixtures',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><FixturesPage /></PageLoader>
        ) : (
          <Unavailable title="AITDE V3 未开放" description="Fixture 查看需启用 AITDE V3 功能开关后开放。" />
        ),
      },
      {
        path: 'fixtures/:fixtureId',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><FixtureDetailPage /></PageLoader>
        ) : (
          <Unavailable title="AITDE V3 未开放" description="Fixture 查看需启用 AITDE V3 功能开关后开放。" />
        ),
      },
      {
        path: 'admin/workers',
        element: AITDE_V3_ENABLED ? (
          <PageLoader><RuntimeAdminPage /></PageLoader>
        ) : (
          <Unavailable title="AITDE V3 未开放" description="Durable Runtime 需启用 AITDE V3 功能开关后开放。" />
        ),
      },
      {
        path: 'theme-lab',
        element: themeLabEnabled
          ? <PageLoader><ThemeLabPage /></PageLoader>
          : <Unavailable title="主题实验室未开放" description="全局主题切换不受影响；主题实验室需在开发模式或配置 VITE_ENABLE_THEME_LAB=true 后开放。" />,
      },
      { path: '*', element: <NotFound /> },
    ],
  },
])
