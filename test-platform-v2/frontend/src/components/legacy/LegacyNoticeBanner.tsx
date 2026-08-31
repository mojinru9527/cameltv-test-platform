import { Link, useLocation } from 'react-router'
import { AITDE_V3_ENABLED } from '@/config/aitde'

// V40-019: legacy v1 surfaces being converged into the AITDE Mission chain. If the
// user lands on one of these, surface a read-only / redirect notice pointing to the
// canonical mission entry — history stays browsable, but the newer path is obvious.
const LEGACY_PREFIXES = [
  '/testcase',
  '/testplan',
  '/dataset',
  '/version-mission',
  '/release-bundles',
  '/apitest',
  '/uitest',
  '/schedule',
  '/defect',
  '/knowledge',
  '/dsh-tasks',
  '/environment',
]

export function LegacyNoticeBanner() {
  const { pathname } = useLocation()
  if (!AITDE_V3_ENABLED) return null
  if (!LEGACY_PREFIXES.some((p) => pathname.startsWith(p))) return null

  return (
    <div
      className="mb-4 flex items-start gap-3 rounded-lg border border-amber-300/60 bg-amber-50/60 px-4 py-3 text-sm text-amber-900"
      role="status"
      aria-label="V4.0 旧版入口收敛提示"
    >
      <span className="mt-0.5" aria-hidden>ⓘ</span>
      <div className="flex-1">
        <p className="font-medium">V4.0：旧版入口收敛中</p>
        <p className="mt-1 text-amber-800/90">
          此页面属于历史入口，当前版本正将「需求 → 场景 → 执行 → 验收」收敛到 AITDE
          Mission 主链；历史功能以只读 / 重定向方式保留。请优先使用新的任务工作台。
        </p>
        <Link
          to="/missions"
          className="mt-2 inline-flex items-center gap-1 font-medium text-amber-900 underline decoration-amber-400 underline-offset-2 hover:text-amber-700"
        >
          前往 Mission 工作台 →
        </Link>
      </div>
    </div>
  )
}
