import { Badge } from '@/ui'

export default function ApiDataPanel({ editing }: { editing: any }) {
  const pretty = (raw: string | undefined, fallback: string) => {
    if (!raw) return fallback
    try {
      return JSON.stringify(JSON.parse(raw), null, 2)
    } catch {
      return raw
    }
  }
  const runStatus = editing?.last_run_status
  const runTone = runStatus === 'success' ? 'success' : runStatus === 'error' ? 'danger' : runStatus === 'fail' ? 'danger' : 'neutral'
  const runLabel = runStatus === 'success' ? '成功' : runStatus === 'fail' ? '失败' : runStatus === 'error' ? '错误' : '未执行'

  return (
    <div className="max-h-[60vh] space-y-4 overflow-y-auto">
      <div className="flex flex-wrap items-center gap-2">
        {editing?.case_design_method && (
          <Badge tone="info">设计方法：{editing.case_design_method}</Badge>
        )}
        {editing?.positive_negative && (
          <Badge tone={editing.positive_negative === 'positive' ? 'success' : editing.positive_negative === 'boundary' ? 'warning' : 'danger'}>
            {editing.positive_negative === 'positive' ? '正向' : editing.positive_negative === 'boundary' ? '边界' : '负向'}
          </Badge>
        )}
        <Badge tone={runTone as any}>最近执行：{runLabel}</Badge>
      </div>

      {editing?.test_data_note && (
        <div className="rounded-md border p-3 text-sm">
          <p className="mb-1 font-medium">数据说明</p>
          <p className="text-muted-foreground whitespace-pre-wrap">{editing.test_data_note}</p>
        </div>
      )}

      <div>
        <p className="mb-1 text-sm font-medium">请求参数</p>
        <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">
          {pretty(editing?.api_body, '（空）')}
        </pre>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium">断言</p>
        <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">
          {pretty(editing?.api_assertions, '（空）')}
        </pre>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium">请求结果（最近执行回填）</p>
        <pre className="max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs">
          {pretty(editing?.last_response_json, '（尚未执行）')}
        </pre>
      </div>
    </div>
  )
}
