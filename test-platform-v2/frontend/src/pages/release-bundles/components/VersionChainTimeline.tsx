import { useNavigate } from 'react-router-dom'
import type { ReleaseBundleVersionChain } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Package, ChevronRight, ExternalLink, ArrowUp } from '@/lib/icons'
import { cn } from '@/lib/utils'

const STATUS_VARIANT: Record<string, { variant: 'secondary' | 'outline'; className?: string; label: string }> = {
  draft: { variant: 'secondary', className: 'border-yellow-200 bg-yellow-50 text-yellow-700', label: '草稿' },
  active: { variant: 'outline', className: 'border-green-200 bg-green-50 text-green-700', label: '活跃' },
  archived: { variant: 'secondary', label: '已归档' },
}

interface Props {
  chain: ReleaseBundleVersionChain[]
  currentId: number
}

export default function VersionChainTimeline({ chain, currentId }: Props) {
  const navigate = useNavigate()

  // Chain comes sorted: newest → oldest (from backend)
  const sorted = [...chain].reverse() // oldest → newest for timeline display

  return (
    <div className="relative">
      {/* Vertical timeline line */}
      <div className="absolute left-[19px] top-0 bottom-0 w-0.5 bg-muted" />

      <div className="space-y-0">
        {sorted.map((item, idx) => {
          const isCurrent = item.id === currentId
          const isLatest = idx === sorted.length - 1

          return (
            <div key={item.id} className="relative flex items-start gap-4 pb-5 last:pb-0">
              {/* Timeline dot */}
              <div
                className={cn(
                  'relative z-10 mt-1.5 size-[10px] rounded-full border-2 shrink-0',
                  isCurrent
                    ? 'bg-primary border-primary ring-2 ring-primary/20'
                    : 'bg-background border-muted-foreground/30',
                )}
              />

              {/* Content card */}
              <Card
                className={cn(
                  'flex-1 transition-colors',
                  isCurrent && 'border-primary/50 bg-primary/5',
                )}
              >
                <CardContent className="p-3 flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <Package
                        className={cn(
                          'size-4 shrink-0',
                          isCurrent ? 'text-primary' : 'text-muted-foreground',
                        )}
                      />
                      <span
                        className={cn(
                          'font-medium text-sm truncate',
                          isCurrent && 'text-primary',
                        )}
                      >
                        {item.name}
                      </span>
                      <Badge
                        variant={STATUS_VARIANT[item.status]?.variant ?? 'secondary'}
                        className={cn(
                          'text-[10px] shrink-0',
                          STATUS_VARIANT[item.status]?.className,
                        )}
                      >
                        {STATUS_VARIANT[item.status]?.label ?? item.status}
                      </Badge>
                      {isCurrent && (
                        <Badge variant="outline" className="text-[10px] border-primary/50 text-primary">
                          当前
                        </Badge>
                      )}
                      {isLatest && !isCurrent && (
                        <Badge variant="outline" className="text-[10px]">
                          最新
                        </Badge>
                      )}
                    </div>

                    <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                      {item.client_version && (
                        <span>
                          📱 用户端 {item.client_version}
                        </span>
                      )}
                      {item.admin_version && (
                        <span>
                          ⚙️ 运营后台 {item.admin_version}
                        </span>
                      )}
                      {item.release_date && (
                        <span className="text-muted-foreground/60">
                          {new Date(item.release_date).toLocaleDateString('zh-CN')}
                        </span>
                      )}
                    </div>
                  </div>

                  {!isCurrent && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="shrink-0"
                      onClick={() => navigate(`/release-bundles/${item.id}`)}
                    >
                      查看
                      <ChevronRight className="size-4 ml-0.5" />
                    </Button>
                  )}
                </CardContent>
              </Card>

              {/* Connector arrow between consecutive items */}
              {idx < sorted.length - 1 && (
                <div className="absolute left-[15px] top-[42px] z-10">
                  <ArrowUp className="size-3 text-muted-foreground/40 rotate-180" />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
