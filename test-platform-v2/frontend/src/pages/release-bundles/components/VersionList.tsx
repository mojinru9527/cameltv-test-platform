import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchReleaseBundles } from '@/api/releaseBundles'
import type { ReleaseBundleListItem } from '@/types'
import { Button } from '@/ui'
import { Input } from '@/ui'
import { Badge } from '@/ui'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Search, Package, RefreshCw } from '@/lib/icons'
import { cn } from '@/lib/utils'

interface VersionListProps {
  projectId: number
  selectedBundleId: number | null
  onSelect: (bundleId: number) => void
}

export default function VersionList({
  projectId,
  selectedBundleId,
  onSelect,
}: VersionListProps) {
  const [versions, setVersions] = useState<ReleaseBundleListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const loadControllerRef = useRef<AbortController | null>(null)

  const loadVersions = useCallback(async () => {
    loadControllerRef.current?.abort()
    const controller = new AbortController()
    loadControllerRef.current = controller
    setLoading(true)
    setError(null)
    try {
      const data = await fetchReleaseBundles({
        page: 1,
        page_size: 100,
        keyword: search || undefined,
      }, controller.signal)
      if (controller.signal.aborted) return
      setVersions(data.items ?? [])
    } catch (err) {
      if (controller.signal.aborted) return
      setError(err instanceof Error ? err.message : '加载版本列表失败')
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [search])

  useEffect(() => {
    loadVersions()
    return () => loadControllerRef.current?.abort()
  }, [loadVersions, projectId])

  const statusBadge = (status: string) => {
    const config: Record<string, { className: string; label: string }> = {
      active: { className: 'border-status-success-border bg-status-success-muted text-status-success', label: '活跃' },
      draft: { className: 'border-status-warning-border bg-status-warning-muted text-status-warning', label: '草稿' },
      archived: { className: 'border-border bg-muted text-muted-foreground', label: '归档' },
    }
    const c = config[status] ?? { className: '', label: status }
    return <Badge tone="neutral" className={cn('text-xs', c.className)}>{c.label}</Badge>
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search */}
      <div className="p-3 border-b">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索版本..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-9 text-sm"
          />
        </div>
      </div>

      {/* List */}
      <ScrollArea className="flex-1">
        {loading ? (
          <div className="p-3 space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="p-4 text-center">
            <p className="text-sm text-destructive mb-2">{error}</p>
            <Button variant="secondary" size="sm" onClick={loadVersions}>
              <RefreshCw className="h-3 w-3 mr-1" /> 重试
            </Button>
          </div>
        ) : versions.length === 0 ? (
          <div className="p-4 text-center text-sm text-muted-foreground">
            暂无版本数据
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {versions.map((v) => {
              const isSelected = selectedBundleId === v.id
              return (
              <button
                key={v.id}
                onClick={() => onSelect(v.id)}
                className={cn(
                  'w-full text-left p-3 rounded-md transition-colors',
                  'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  isSelected
                    ? 'bg-accent text-accent-foreground ring-1 ring-ring/10'
                    : 'text-foreground',
                )}
              >
                <div className="flex items-center gap-2">
                  <Package className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="font-medium text-sm truncate">{v.name}</span>
                </div>
                <div className="flex items-center gap-2 mt-1.5 ml-6">
                  <span
                    className={cn(
                      'text-xs',
                      isSelected ? 'text-accent-foreground/85' : 'text-muted-foreground',
                    )}
                  >
                    用户端 {v.client_version ?? '—'}
                  </span>
                  {statusBadge(v.status)}
                </div>
                {v.release_date && (
                  <div
                    className={cn(
                      'mt-1 ml-6 text-xs',
                      isSelected ? 'text-accent-foreground/85' : 'text-muted-foreground',
                    )}
                  >
                    {v.release_date}
                  </div>
                )}
              </button>
              )
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
