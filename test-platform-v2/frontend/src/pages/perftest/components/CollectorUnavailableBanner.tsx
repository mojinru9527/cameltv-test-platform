import { Button } from '@/ui'
import { AlertCircle, Loader2 } from '@/lib/icons'

interface CollectorUnavailableBannerProps {
  loading: boolean
  onRetry: () => void
}

export default function CollectorUnavailableBanner({ loading, onRetry }: CollectorUnavailableBannerProps) {
  return (
    <div
      role="alert"
      aria-labelledby="perf-collector-unavailable-title"
      className="flex flex-col gap-3 rounded-lg border border-status-warning/40 bg-status-warning/10 p-4 text-sm sm:flex-row sm:items-start"
    >
      <AlertCircle className="mt-0.5 size-5 shrink-0 text-status-warning" aria-hidden="true" />
      <div className="min-w-0 flex-1 space-y-1">
        <h2 id="perf-collector-unavailable-title" className="font-semibold">
          真实性能采集不可用
        </h2>
        <p className="text-muted-foreground">
          当前服务未安装或未启用 SoloX。平台不会生成模拟数据；请完成 SoloX 部署并连接已授权设备后重试。
        </p>
      </div>
      <Button
        variant="secondary"
        size="sm"
        onClick={onRetry}
        disabled={loading}
        className="shrink-0"
      >
        {loading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
        重新检测采集器
      </Button>
    </div>
  )
}
