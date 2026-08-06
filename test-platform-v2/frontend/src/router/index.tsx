import { lazy, Suspense, useState, type FormEvent, type ReactNode } from 'react'
import { createBrowserRouter, Navigate, useNavigate } from 'react-router'
import { Loader2 } from '@/lib/icons'
import MainLayout from '@/layouts/MainLayout'
import Placeholder from '@/pages/Placeholder'
import RequireAuth from './guard'
import client from '@/api/client'
import { logoutApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { Button, Input } from '@/ui'

const LoginPage = lazy(() => import('@/pages/login'))
const RegisterPage = lazy(() => import('@/pages/register'))
const MyProjectsPage = lazy(() => import('@/pages/my-projects'))
const OrganizationPage = lazy(() => import('@/pages/organization'))
const SystemPage = lazy(() => import('@/pages/system'))
const TestCasePage = lazy(() => import('@/pages/testcase'))
const TestPlanPage = lazy(() => import('@/pages/testplan'))
const PlanDetail = lazy(() => import('@/pages/testplan/PlanDetail'))
const ReportPage = lazy(() => import('@/pages/report'))
const SchedulePage = lazy(() => import('@/pages/schedule'))
const Workbench = lazy(() => import('@/pages/workbench'))
const DefectPage = lazy(() => import('@/pages/defect'))
const SpecialPage = lazy(() => import('@/pages/special'))
const UiTestPage = lazy(() => import('@/pages/uitest'))
const ProjectPage = lazy(() => import('@/pages/project'))
const TracePage = lazy(() => import('@/pages/trace'))
const RequirementPage = lazy(() => import('@/pages/requirement'))
const RequirementReviewPage = lazy(() => import('@/pages/requirement/ReviewPage'))
const MindmapPage = lazy(() => import('@/pages/mindmap'))
const ApiTestPage = lazy(() => import('@/pages/apitest'))
const NotifyPage = lazy(() => import('@/pages/notify'))
const EnvironmentPage = lazy(() => import('@/pages/environment'))
const DatasetPage = lazy(() => import('@/pages/dataset'))
const IntegrationPage = lazy(() => import('@/pages/integration'))
const KnowledgePage = lazy(() => import('@/pages/knowledge'))
const AgentWorkbenchPage = lazy(() => import('@/pages/agent-workbench'))
const PerftestPage = lazy(() => import('@/pages/perftest'))
const OperationsReleasePage = lazy(() => import('@/pages/operations-release'))
const PlaygroundPage = lazy(() => import('@/pages/playground'))
const ReleaseBundlesPage = lazy(() => import('@/pages/release-bundles'))
const BundleDetailPage = lazy(() => import('@/pages/release-bundles/BundleDetail'))
const VersionPanoramaPage = lazy(() => import('@/pages/release-bundles/VersionPanorama'))
const ThemeLabPage = lazy(() => import('@/theme-lab/ThemeLab').then(m => ({ default: m.ThemeLab })))
const LanhuEvidencePage = lazy(() => import('@/pages/lanhu-evidence'))
const LanhuEvidenceJobDetail = lazy(() => import('@/pages/lanhu-evidence/JobDetail'))

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
      <RequireAuth>
        <PasswordChangeBoundary>
          <MainLayout />
        </PasswordChangeBoundary>
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/workbench" replace /> },
      { path: 'my-projects', element: <PageLoader><MyProjectsPage /></PageLoader> },
      { path: 'organizations', element: <PageLoader><OrganizationPage /></PageLoader> },
      { path: 'workbench', element: <PageLoader><Workbench /></PageLoader> },
      { path: 'trace', element: <PageLoader><TracePage /></PageLoader> },
      { path: 'requirement', element: <PageLoader><RequirementPage /></PageLoader> },
      { path: 'requirement/:id/review', element: <PageLoader><RequirementReviewPage /></PageLoader> },
      { path: 'testcase', element: <PageLoader><TestCasePage /></PageLoader> },
      { path: 'testplan', element: <PageLoader><TestPlanPage /></PageLoader> },
      { path: 'testplan/:id', element: <PageLoader><PlanDetail /></PageLoader> },
      { path: 'mindmap', element: <PageLoader><MindmapPage /></PageLoader> },
      { path: 'apitest', element: <PageLoader><ApiTestPage /></PageLoader> },
      { path: 'uitest', element: <PageLoader><UiTestPage /></PageLoader> },
      { path: 'special', element: <PageLoader><SpecialPage /></PageLoader> },
      { path: 'schedule', element: <PageLoader><SchedulePage /></PageLoader> },
      { path: 'defect', element: <PageLoader><DefectPage /></PageLoader> },
      { path: 'defect/:id', element: <PageLoader><DefectPage /></PageLoader> },
      { path: 'report', element: <PageLoader><ReportPage /></PageLoader> },
      { path: 'system', element: <PageLoader><SystemPage /></PageLoader> },
      { path: 'project', element: <PageLoader><ProjectPage /></PageLoader> },
      { path: 'notify', element: <PageLoader><NotifyPage /></PageLoader> },
      { path: 'environment', element: <PageLoader><EnvironmentPage /></PageLoader> },
      { path: 'dataset', element: <PageLoader><DatasetPage /></PageLoader> },
      { path: 'integration', element: <PageLoader><IntegrationPage /></PageLoader> },
      { path: 'knowledge', element: <PageLoader><KnowledgePage /></PageLoader> },
      { path: 'playground', element: <PageLoader><PlaygroundPage /></PageLoader> },
      { path: 'version-mission', element: <Navigate to="/release-bundles" replace /> },
      { path: 'release-bundles', element: <PageLoader><ReleaseBundlesPage /></PageLoader> },
      { path: 'release-bundles/:id', element: <PageLoader><BundleDetailPage /></PageLoader> },
      { path: 'release-bundles/:id/panorama', element: <PageLoader><VersionPanoramaPage /></PageLoader> },
      { path: 'agent-workbench', element: <PageLoader><AgentWorkbenchPage /></PageLoader> },
      { path: 'perftest', element: <PageLoader><PerftestPage /></PageLoader> },
      { path: 'lanhu-evidence', element: <PageLoader><LanhuEvidencePage /></PageLoader> },
      { path: 'lanhu-evidence/:id', element: <PageLoader><LanhuEvidenceJobDetail /></PageLoader> },
      { path: 'operations-release', element: <PageLoader><OperationsReleasePage /></PageLoader> },
      { path: 'theme-lab', element: <PageLoader><ThemeLabPage /></PageLoader> },
      { path: '*', element: <Placeholder title="页面建设中" /> },
    ],
  },
])
