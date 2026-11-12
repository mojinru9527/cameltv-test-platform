import { useEffect, useState } from 'react'
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  Tabs,
  TabsList,
  TabsTrigger,
} from '@/ui'
import {
  approveWorkflow,
  getWorkflow,
  listWorkflows,
  type WorkflowDetail,
  type WorkflowSummary,
} from '@/api/aiqeConsole'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import ConsoleTabs from './ConsoleTabs'

const FILTERS = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '待审批' },
  { value: 'approved', label: '已通过' },
] as const

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : '请求失败'
}

export default function WorkflowsPage() {
  useDocumentTitle('Workflow 审批')
  const [filter, setFilter] = useState<string>('all')
  const [rows, setRows] = useState<WorkflowSummary[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState('')
  const [detail, setDetail] = useState<WorkflowDetail | null>(null)

  useEffect(() => {
    let alive = true
    listWorkflows(filter === 'all' ? {} : { approval_status: filter })
      .then((data) => {
        if (!alive) return
        setRows(data.items)
        setTotal(data.total)
      })
      .catch((err: unknown) => {
        if (alive) setError(errorText(err))
      })
    return () => {
      alive = false
    }
  }, [filter])

  async function handleApprove(row: WorkflowSummary) {
    setError('')
    try {
      const updated = await approveWorkflow(row.id)
      setRows((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      if (detail?.id === updated.id) setDetail({ ...detail, ...updated })
    } catch (err: unknown) {
      setError(errorText(err))
    }
  }

  async function openDetail(row: WorkflowSummary) {
    setError('')
    try {
      setDetail(await getWorkflow(row.id))
    } catch (err: unknown) {
      setError(errorText(err))
    }
  }

  return (
    <div className="space-y-4 p-6">
      <header className="space-y-3">
        <div className="flex items-baseline justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Workflow 审批</h1>
            <p className="text-sm text-muted-foreground">
              审批通过后 graph / checksum 冻结；变更需新建 version。
            </p>
          </div>
          <span className="text-sm text-muted-foreground">共 {total} 条</span>
        </div>
        <ConsoleTabs />
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <Tabs onValueChange={setFilter} value={filter}>
        <TabsList>
          {FILTERS.map((item) => (
            <TabsTrigger key={item.value} value={item.value}>
              {item.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left">
            <tr>
              <th className="px-3 py-2">Workflow</th>
              <th className="px-3 py-2">version</th>
              <th className="px-3 py-2">节点</th>
              <th className="px-3 py-2">校验</th>
              <th className="px-3 py-2">审批状态</th>
              <th className="px-3 py-2">创建时间</th>
              <th className="px-3 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-center text-muted-foreground" colSpan={7}>
                  暂无 Workflow
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr className="border-t" key={row.id}>
                  <td className="px-3 py-2 font-mono text-xs">{row.id.slice(0, 8)}…</td>
                  <td className="px-3 py-2">v{row.version}</td>
                  <td className="px-3 py-2">{row.node_count}</td>
                  <td className="px-3 py-2">{row.validation_status}</td>
                  <td className="px-3 py-2">
                    {row.frozen ? (
                      <Badge tone="success">已通过</Badge>
                    ) : (
                      <Badge tone="warning">待审批</Badge>
                    )}
                  </td>
                  <td className="px-3 py-2">{new Date(row.created_at).toLocaleString()}</td>
                  <td className="space-x-2 px-3 py-2 text-right">
                    <Button onClick={() => void openDetail(row)} size="sm" variant="ghost">
                      详情
                    </Button>
                    <Button
                      disabled={row.frozen}
                      onClick={() => void handleApprove(row)}
                      size="sm"
                      variant="outline"
                    >
                      {row.frozen ? '已审批' : '审批'}
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Dialog onOpenChange={(open) => !open && setDetail(null)} open={detail !== null}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Workflow 详情</DialogTitle>
            <DialogDescription>
              {detail ? `checksum ${detail.checksum.slice(0, 16)}…` : ''}
            </DialogDescription>
          </DialogHeader>
          {detail ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">审批状态：</span>
                {detail.frozen ? <Badge tone="success">已冻结</Badge> : <Badge tone="warning">待审批</Badge>}
              </div>
              <pre className="max-h-80 overflow-auto rounded bg-muted/40 p-3 text-xs">
                {JSON.stringify(detail.graph_json, null, 2)}
              </pre>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
