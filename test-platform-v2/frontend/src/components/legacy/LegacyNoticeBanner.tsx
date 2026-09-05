import { Link, useLocation, useMatches } from 'react-router'
import { useAitdeV3Enabled } from '@/config/aitde'

// V40-019: legacy v1 surfaces being converged into the AITDE Mission chain. If the
// user lands on one of these, surface a read-only / redirect notice pointing to the
// canonical mission entry — history stays browsable, but the newer path is obvious.
// Uses only semantic tokens (theme governance: no fixed Tailwind palettes).
const LEGACY_PREFIXES = [
  '/testcase',
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
  const matches = useMatches()
  const aitdeEnabled = useAitdeV3Enabled()
  if (!aitdeEnabled) return null
  // 404 splat 叶子（router/index.tsx 的 `path: '*'`）不是历史入口。/defects 这类未知路径
  // 会因前缀匹配命中 '/defect'，让 404 页叠加收敛横幅（DEF-20260905-009）。
  // useMatches() 给出当前 URL 的完整匹配分支，与横幅在树中的挂载位置无关。
  if (matches[matches.length - 1]?.params?.['*'] !== undefined) return null
  if (!LEGACY_PREFIXES.some((p) => pathname.startsWith(p))) return null

  return (
    <div
      className="mb-4 flex items-start gap-3 rounded-lg border bg-card px-4 py-3 text-sm text-card-foreground"
      role="status"
      aria-label="V4.0 旧版入口收敛提示"
    >
      <div className="flex-1">
        <p className="font-medium">V4.0：旧版入口收敛中</p>
        <p className="mt-1 text-muted-foreground">
          此页面属于历史入口，当前版本正将「需求 → 场景 → 执行 → 验收」收敛到 AITDE
          Mission 主链；历史功能以只读 / 重定向方式保留。请优先使用新的任务工作台。
        </p>
        <Link
          to="/missions"
          className="mt-2 inline-flex items-center gap-1 font-medium text-primary underline underline-offset-2 hover:text-primary/80"
        >
          前往 Mission 工作台 →
        </Link>
      </div>
    </div>
  )
}
