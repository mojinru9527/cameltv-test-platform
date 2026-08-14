import { Badge, Button } from '@/ui'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Import, Link2, Loader2 } from '@/lib/icons'
import type { AIGeneratedCase, ApiMatchItem, ApiService } from '@/types'
import { PRIORITY_CLASSES } from './AiDisplayParts'

interface Props {
  apiCases: AIGeneratedCase[]
  selectedKeys: number[]
  apiServices: ApiService[]
  apiMatches: ApiMatchItem[]
  confirmedEndpointIds: Set<number>
  selectedServiceId: number | null
  loadingMatches: boolean
  savingMatches: boolean
  generatingApiFromEndpoints: boolean
  importing: boolean
  getDisplayCase: (c: AIGeneratedCase) => AIGeneratedCase
  onToggleAll: () => void
  onToggleOne: (index: number) => void
  onServiceChange: (value: string) => void
  onToggleEndpoint: (endpointId: number) => void
  onConfirmMatches: () => void
  onGenerateApiFromEndpoints: () => void
  onImport: (indices: number[]) => void
}

export default function AiApiCasesPanel({
  apiCases,
  selectedKeys,
  apiServices,
  apiMatches,
  confirmedEndpointIds,
  selectedServiceId,
  loadingMatches,
  savingMatches,
  generatingApiFromEndpoints,
  importing,
  getDisplayCase,
  onToggleAll,
  onToggleOne,
  onServiceChange,
  onToggleEndpoint,
  onConfirmMatches,
  onGenerateApiFromEndpoints,
  onImport,
}: Props) {
  return (
    <div className="max-h-[55vh] overflow-auto space-y-3 pr-1">
      {/* API Matches Banner */}
      <Alert className="border-status-success-border bg-status-success-muted">
        <Link2 className="size-4 text-status-success" />
        <AlertTitle className="text-status-success text-sm">
          候选匹配 {apiMatches.length} 个，已确认 {confirmedEndpointIds.size} 个
        </AlertTitle>
        <AlertDescription className="space-y-2 text-status-success text-xs">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Select
              value={selectedServiceId == null ? '' : String(selectedServiceId)}
              onValueChange={onServiceChange}
            >
              <SelectTrigger className="h-8 w-full bg-card sm:w-[240px]" aria-label="选择 API 服务">
                <SelectValue placeholder="选择 API 服务后确认匹配" />
              </SelectTrigger>
              <SelectContent>
                {apiServices.map((service) => (
                  <SelectItem key={service.id} value={String(service.id)}>
                    {service.display_name || service.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              variant="secondary"
              className="bg-card"
              onClick={onConfirmMatches}
              disabled={savingMatches || selectedServiceId == null}
            >
              {savingMatches && <Loader2 className="size-3.5 animate-spin" />}
              确认并保存匹配
            </Button>
            <Button
              size="sm"
              variant="secondary"
              className="bg-card"
              onClick={onGenerateApiFromEndpoints}
              disabled={generatingApiFromEndpoints}
            >
              {generatingApiFromEndpoints && <Loader2 className="size-3.5 animate-spin" />}
              按已导入接口生成用例
            </Button>
          </div>
          <div>
            {apiMatches.slice(0, 8).map((m) => {
              const selected = confirmedEndpointIds.has(m.endpoint_id)
              return (
                <button
                  key={`${m.req_id}-${m.endpoint_id}`}
                  type="button"
                  className="mr-1 mb-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={() => onToggleEndpoint(m.endpoint_id)}
                  aria-pressed={selected}
                  aria-label={`${selected ? '取消' : '选择'}匹配 ${m.method} ${m.path}`}
                >
                  <Badge
                    tone="neutral"
                    className={selected
                      ? 'border-status-success-border bg-status-success-muted text-status-success text-xs'
                      : 'border-status-success-border bg-card text-status-success text-xs'}
                  >
                    {m.method} {m.path}
                  </Badge>
                </button>
              )
            })}
            {apiMatches.length > 8 && <span className="text-muted-foreground">+{apiMatches.length - 8} 更多</span>}
          </div>
        </AlertDescription>
      </Alert>

      {loadingMatches && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
          <Loader2 className="size-3.5 animate-spin" />
          正在匹配 API 端点...
        </div>
      )}

      {/* API Cases Table */}
      <div className="border rounded-lg">
        <Table className="min-w-[900px]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={selectedKeys.length === apiCases.length && apiCases.length > 0}
                  onCheckedChange={onToggleAll}
                />
              </TableHead>
              <TableHead className="w-[80px]">方法</TableHead>
              <TableHead className="w-[210px]">接口路径/用例标题</TableHead>
              <TableHead className="w-[80px] text-center">优先级</TableHead>
              <TableHead className="w-[110px]">模块</TableHead>
              <TableHead className="w-[150px]">请求/前置条件</TableHead>
              <TableHead className="w-[240px]">预期结果</TableHead>
              <TableHead className="w-[60px] text-center">匹配</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {apiCases.map((c) => {
              const display = getDisplayCase(c)
              const matchedEndpoint = apiMatches.find(
                (m) => m.endpoint_id && display.api_endpoint && m.path === display.api_endpoint
              )
              return (
                <TableRow key={c.index}>
                  <TableCell>
                    <Checkbox
                      checked={selectedKeys.includes(c.index)}
                      onCheckedChange={() => onToggleOne(c.index)}
                    />
                  </TableCell>
                  <TableCell>
                    <Badge
                      tone="neutral"
                      className={`text-xs font-mono ${
                        display.api_method === 'GET' ? 'border-status-info-border bg-status-info-muted text-status-info' :
                        display.api_method === 'POST' ? 'border-status-success-border bg-status-success-muted text-status-success' :
                        display.api_method === 'PUT' ? 'border-status-warning-border bg-status-warning-muted text-status-warning' :
                        display.api_method === 'DELETE' ? 'border-status-danger-border bg-status-danger-muted text-status-danger' :
                        'border-border bg-muted text-muted-foreground'
                      }`}
                    >
                      {display.api_method || 'GET'}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium align-top whitespace-normal">
                    <div className="break-words max-w-[200px]">
                      {display.api_endpoint ? (
                        <span className="font-mono text-xs text-muted-foreground">{display.api_endpoint}</span>
                      ) : null}
                      <div className="text-sm mt-0.5">{display.title}</div>
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge tone="neutral" className={PRIORITY_CLASSES[display.priority] || 'border-border bg-muted text-muted-foreground'}>
                      {display.priority}
                    </Badge>
                  </TableCell>
                  <TableCell className="break-words max-w-[100px] text-xs align-top whitespace-normal">{display.module || '-'}</TableCell>
                  <TableCell className="break-words max-w-[140px] text-xs align-top whitespace-normal">{display.preconditions || '-'}</TableCell>
                  <TableCell className="break-words max-w-[230px] text-xs align-top whitespace-normal">{display.expected_result || '-'}</TableCell>
                  <TableCell className="text-center">
                    {matchedEndpoint ? (
                      <Badge
                        tone="neutral"
                        className={confirmedEndpointIds.has(matchedEndpoint.endpoint_id)
                          ? 'border-status-success-border bg-status-success-muted text-status-success text-xs'
                          : 'border-status-success-border bg-status-success-muted text-status-success text-xs'}
                        title={`${matchedEndpoint.method} ${matchedEndpoint.path} (${Math.round(matchedEndpoint.confidence * 100)}%)`}
                      >
                        <Link2 className="size-3" />
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground text-xs">-</span>
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          已选 {selectedKeys.length}/{apiCases.length} 条接口用例
        </span>
        <Button
          size="sm"
          onClick={() => onImport(selectedKeys)}
          disabled={importing || selectedKeys.length === 0}
        >
          {importing ? <Loader2 className="size-3.5 animate-spin" /> : <Import className="size-3.5" />}
          导入接口用例 ({selectedKeys.length})
        </Button>
      </div>
    </div>
  )
}
