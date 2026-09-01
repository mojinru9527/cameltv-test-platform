import type { ReactNode } from 'react'
import { Construction, Loader2, RefreshCw } from '@/lib/icons'
import { Button } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { useAitdeV3State, resolveAitdeV3, AITDE_V3_BUILD_OVERRIDE } from '@/config/aitde'

interface Props {
  /** 该路由对应的能力名，用于占位文案，如「测试任务（Mission）入口」。 */
  feature: string
  children: ReactNode
}

function Centered({ children }: { children: ReactNode }) {
  return <div className="flex flex-col items-center justify-center py-24 text-center">{children}</div>
}

/**
 * AITDE V3/V4 路由门（V4.0 生产黑盒复盘 P0-1 / P3-15）。
 *
 * 与旧实现的差别：
 *  1. 开关**运行时**取自后端 `/api/v2/health`，不再依赖从未透传的构建参数；
 *  2. 区分「探测中」「未开放」「探测失败」三态，不把后端不可达静默当作未开放；
 *  3. 未开放文案给出**可执行指引**（在哪配、谁来配），而不是只说"需启用开关"。
 */
export default function AitdeGate({ feature, children }: Props) {
  const state = useAitdeV3State()

  if (state === 'enabled') return <>{children}</>

  if (state === 'loading') {
    return (
      <Centered>
        <Loader2 className="size-8 animate-spin text-muted-foreground/50" />
        <p className="mt-3 text-sm text-muted-foreground">正在检测 AITDE 能力…</p>
      </Centered>
    )
  }

  if (state === 'unknown') {
    return <UnknownState feature={feature} />
  }

  return <DisabledState feature={feature} />
}

function UnknownState({ feature }: { feature: string }) {
  useDocumentTitle('AITDE 能力探测失败')
  return (
    <Centered>
      <Construction className="size-14 text-muted-foreground/40" />
      <h2 className="mt-4 text-lg font-semibold">AITDE 能力探测失败</h2>
      <p className="mt-2 max-w-lg text-sm text-muted-foreground">
        无法从后端读取 AITDE 开关状态（<code className="rounded bg-muted px-1">GET /api/v2/health</code> 未响应）。
        {feature}暂时不可用。请确认后端服务健康后重试。
      </p>
      <Button
        variant="secondary"
        size="sm"
        className="mt-4 gap-1.5"
        onClick={() => {
          void resolveAitdeV3().then(() => window.location.reload())
        }}
      >
        <RefreshCw className="size-3.5" />
        重新检测
      </Button>
    </Centered>
  )
}

function DisabledState({ feature }: { feature: string }) {
  useDocumentTitle('AITDE 未开放')
  return (
    <Centered>
      <Construction className="size-14 text-muted-foreground/40" />
      <h2 className="mt-4 text-lg font-semibold">AITDE 未开放</h2>
      <p className="mt-2 max-w-lg text-sm text-muted-foreground">
        {feature}需要平台开启 AITDE 能力后才可使用。
      </p>
      <div className="mt-4 max-w-lg rounded-lg border border-border bg-muted/40 px-4 py-3 text-left text-xs text-muted-foreground">
        <p className="font-medium text-foreground">如何开启</p>
        <p className="mt-1.5">
          由平台管理员在<strong className="text-foreground">后端</strong>环境变量设置{' '}
          <code className="rounded bg-background px-1">AITDE_V3_ENABLED=true</code> 并重启服务；
          开关状态以 <code className="rounded bg-background px-1">GET /api/v2/health</code> 为准，
          前端会自动跟随，无需重新构建前端。
        </p>
        {AITDE_V3_BUILD_OVERRIDE === false && (
          <p className="mt-2 text-status-warning">
            注意：当前前端构建显式设置了{' '}
            <code className="rounded bg-background px-1">VITE_AITDE_V3_ENABLED=false</code>，
            该覆盖优先于后端开关。需移除该构建参数才能跟随后端。
          </p>
        )}
      </div>
    </Centered>
  )
}
