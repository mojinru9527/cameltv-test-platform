import { Button } from '@/ui'

/**
 * V30-107：409 STALE（乐观锁/状态冲突）内联提示。
 *
 * AITDE v2 后端在并发状态冲突时返回 409（契约已冻结、评审状态已变更、
 * fixture 租约冲突等）。此时页面持有的数据已过期，直接重试原操作必然
 * 再冲突——正确动作是刷新数据后基于最新状态重新决策，因此不提供
 * 「原样重试」，只提供「刷新后重试」。
 */
export function StaleConflictBanner({ onReload }: { onReload: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-status-warning-border bg-status-warning-muted px-3 py-2 text-sm"
    >
      <span className="text-status-warning">
        状态已变更（409 STALE）：数据已被其他操作更新，当前页面内容已过期。
      </span>
      <Button size="sm" variant="secondary" onClick={onReload}>
        刷新后重试
      </Button>
    </div>
  )
}
