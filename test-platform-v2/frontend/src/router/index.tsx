import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { Loader2 } from '@/lib/icons'
import MainLayout from '@/layouts/MainLayout'
import Placeholder from '@/pages/Placeholder'
import RequireAuth from './guard'

const LoginPage = lazy(() => import('@/pages/login'))
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
const MindmapPage = lazy(() => import('@/pages/mindmap'))
const ApiTestPage = lazy(() => import('@/pages/apitest'))
const NotifyPage = lazy(() => import('@/pages/notify'))
const EnvironmentPage = lazy(() => import('@/pages/environment'))
const DatasetPage = lazy(() => import('@/pages/dataset'))
const IntegrationPage = lazy(() => import('@/pages/integration'))
const KnowledgePage = lazy(() => import('@/pages/knowledge'))
const AgentWorkbenchPage = lazy(() => import('@/pages/agent-workbench'))
const PerftestPage = lazy(() => import('@/pages/perftest'))

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

export const router = createBrowserRouter([
  { path: '/login', element: <PageLoader><LoginPage /></PageLoader> },
  {
    path: '/',
    element: (
      <RequireAuth>
        <MainLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/workbench" replace /> },
      { path: 'workbench', element: <PageLoader><Workbench /></PageLoader> },
      { path: 'trace', element: <PageLoader><TracePage /></PageLoader> },
      { path: 'requirement', element: <PageLoader><RequirementPage /></PageLoader> },
      { path: 'testcase', element: <PageLoader><TestCasePage /></PageLoader> },
      { path: 'testplan', element: <PageLoader><TestPlanPage /></PageLoader> },
      { path: 'testplan/:id', element: <PageLoader><PlanDetail /></PageLoader> },
      { path: 'mindmap', element: <PageLoader><MindmapPage /></PageLoader> },
      { path: 'apitest', element: <PageLoader><ApiTestPage /></PageLoader> },
      { path: 'uitest', element: <PageLoader><UiTestPage /></PageLoader> },
      { path: 'special', element: <PageLoader><SpecialPage /></PageLoader> },
      { path: 'schedule', element: <PageLoader><SchedulePage /></PageLoader> },
      { path: 'report', element: <PageLoader><ReportPage /></PageLoader> },
      { path: 'system', element: <PageLoader><SystemPage /></PageLoader> },
      { path: 'project', element: <PageLoader><ProjectPage /></PageLoader> },
      { path: 'notify', element: <PageLoader><NotifyPage /></PageLoader> },
      { path: 'environment', element: <PageLoader><EnvironmentPage /></PageLoader> },
      { path: 'dataset', element: <PageLoader><DatasetPage /></PageLoader> },
      { path: 'integration', element: <PageLoader><IntegrationPage /></PageLoader> },
      { path: 'knowledge', element: <PageLoader><KnowledgePage /></PageLoader> },
      { path: 'agent-workbench', element: <PageLoader><AgentWorkbenchPage /></PageLoader> },
      { path: 'perftest', element: <PageLoader><PerftestPage /></PageLoader> },
      { path: '*', element: <Placeholder title="页面建设中" /> },
    ],
  },
])
