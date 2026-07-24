/**
 * 环境选择栏 — 环境下拉 + base_url 编辑 + 刷新
 * 被 ApiDebugPanel 等调试组件复用
 *
 * Props:
 * - envs: 环境列表
 * - envId: 当前选中环境 ID
 * - envBaseUrl: 当前环境 base_url（可编辑）
 * - onEnvChange: 环境切换回调
 * - onBaseUrlChange: base_url 编辑回调
 * - onBaseUrlBlur: base_url 失焦保存回调
 */
import { RefreshCw } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import type { Environment } from '@/types'

interface Props {
  envs: Environment[]
  envId?: number
  envBaseUrl: string
  onEnvChange: (id: number | undefined) => void
  onBaseUrlChange: (url: string) => void
  onBaseUrlBlur: () => void
  /** 可选的环境列表刷新回调，不传则不显示刷新按钮 */
  onRefresh?: () => void
}

export default function EnvironmentBar({
  envs,
  envId,
  envBaseUrl,
  onEnvChange,
  onBaseUrlChange,
  onBaseUrlBlur,
  onRefresh,
}: Props) {
  const envTypeLabel = (type?: string): string => {
    if (type === 'prod') return '生产'
    if (type === 'test') return '测试'
    if (type === 'staging') return '预发布'
    if (type === 'dev') return '开发'
    return type || ''
  }

  const selectedEnv = envs.find(e => e.id === envId)
  const isProduction = selectedEnv && (selectedEnv.is_production === true || selectedEnv.env_type === 'prod')

  return (
    <div>
      <div className="flex items-center gap-1.5">
        <Label className="text-[11px] text-muted-foreground shrink-0">环境</Label>
        {isProduction && (
          <Badge variant="destructive" className="text-[10px] px-1 py-0 leading-none">PROD</Badge>
        )}
        {onRefresh && (
          <Button type="button" size="icon-sm" variant="ghost" onClick={onRefresh} title="刷新环境列表">
            <RefreshCw className="size-3" />
          </Button>
        )}
      </div>
      <Select
        value={envId?.toString() || '_'}
        onValueChange={(v) => onEnvChange(v === '_' ? undefined : Number(v))}
      >
        <SelectTrigger className={`h-8 text-xs mt-1 ${isProduction ? 'border-red-300 dark:border-red-700 ring-1 ring-red-200 dark:ring-red-800' : ''}`}>
          <SelectValue placeholder="选择环境" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="_">未选择</SelectItem>
          {envs.map((e) => (
            <SelectItem key={e.id} value={e.id.toString()}>
              {e.name}
              {e.env_type ? ` (${envTypeLabel(e.env_type)})` : ''}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {envId && (
        <Input
          className={`h-8 text-xs mt-1 font-mono ${isProduction ? 'border-red-300 dark:border-red-700' : ''}`}
          value={envBaseUrl}
          onChange={(e) => onBaseUrlChange(e.target.value)}
          onBlur={onBaseUrlBlur}
          placeholder="环境 base_url"
        />
      )}
    </div>
  )
}
