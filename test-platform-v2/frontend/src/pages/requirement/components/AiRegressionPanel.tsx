import { Badge } from '@/ui'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent } from '@/components/ui/card'
import { BarChart3, ClipboardCheck, Link2, Monitor, Server, Zap } from '@/lib/icons'
import type { TestModule } from '@/types'
import { ClientScopeBadges } from './AiDisplayParts'

interface Props {
  extractionModules: TestModule[]
}

export default function AiRegressionPanel({ extractionModules }: Props) {
  return (
    <div className="max-h-[55vh] overflow-auto space-y-3 pr-1">
      <Alert className="border-status-warning-border bg-status-warning-muted">
        <Zap className="size-4 text-status-warning" />
        <AlertTitle className="text-status-warning text-sm">UI 回归测试建议</AlertTitle>
        <AlertDescription className="text-status-warning text-xs">
          基于需求的功能拆分结果，以下模块涉及集成/接口类功能点，建议在对应 release-bundle 发版时触发 UI 回归测试。
        </AlertDescription>
      </Alert>

      {extractionModules
        .filter((mod) => mod.function_points?.some((fp) => fp.type === 'integration'))
        .map((mod) => {
          const integrationFps = mod.function_points?.filter((fp) => fp.type === 'integration') || []
          const otherFps = mod.function_points?.filter((fp) => fp.type !== 'integration') || []
          return (
            <Card key={mod.id} size="sm" className="border-status-warning-border">
              <CardContent className="pt-3">
                <div className="flex items-center gap-2 mb-2">
                  <Badge tone="neutral" className="font-mono text-xs">{mod.id}</Badge>
                  <span className="font-medium text-sm">{mod.name}</span>
                  <Badge tone="neutral" className="text-xs border-status-warning-border bg-status-warning-muted text-status-warning">
                    {integrationFps.length} 个集成功能点
                  </Badge>
                </div>

                {/* Integration function points */}
                <div className="space-y-2 mb-3">
                  <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground"><Link2 className="size-3.5" />集成功能点（建议回归）:</p>
                  {integrationFps.map((fp) => (
                    <div key={fp.id} className="flex items-start gap-2 border rounded p-2 bg-status-warning-muted">
                      <Badge tone="neutral" className="font-mono text-xs shrink-0">{fp.id}</Badge>
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{fp.title}</p>
                        <p className="text-xs text-muted-foreground">{fp.description}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <ClientScopeBadges clients={fp.client_scope} />
                          <span className="text-xs text-muted-foreground">
                            建议: Playwright UI 脚本 + API 接口回归
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Related function points */}
                {otherFps.length > 0 && (
                  <div>
                    <p className="mb-1 flex items-center gap-1 text-xs font-medium text-muted-foreground"><ClipboardCheck className="size-3.5" />关联功能点:</p>
                    <div className="flex flex-wrap gap-1">
                      {otherFps.map((fp) => (
                        <Badge key={fp.id} tone="neutral" className="text-xs">
                          {fp.id} {fp.title}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}

      {/* Regression Summary */}
      <Card size="sm" className="border-status-info-border bg-status-info-muted">
        <CardContent className="pt-3">
          <p className="mb-2 flex items-center gap-1.5 text-sm font-medium text-status-info"><BarChart3 className="size-4" aria-hidden="true" />回归测试清单</p>
          <div className="grid grid-cols-2 gap-2 text-xs text-status-info">
            <div className="flex items-center gap-1">
              <Monitor className="size-3" /> 建议 UI 自动化回归脚本
            </div>
            <div className="flex items-center gap-1">
              <Server className="size-3" /> 建议 API 接口回归用例
            </div>
            <div className="flex items-center gap-1">
              <Link2 className="size-3" /> 关联 release-bundle 版本差异
            </div>
            <div className="flex items-center gap-1">
              <Zap className="size-3" /> 自动触发回归测试执行
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
