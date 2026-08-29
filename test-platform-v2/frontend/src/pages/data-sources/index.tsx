import { useState } from 'react'
import { toast } from 'sonner'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input, Skeleton } from '@/ui'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchDataSources,
  createDataSource,
  testDataSourceConnection,
  type DataSource,
  type DataSourceConnectionResult,
} from '@/api/dataSources'
import { DataSourceConnectionBadge } from '@/components/data/DataSourceConnectionBadge'

const SOURCE_TYPES = ['STATIC', 'MYSQL', 'POSTGRES', 'API', 'WORKFLOW']
const ACCESS_MODES = ['READONLY', 'READWRITE']

export default function DataSourcesPage() {
  useDocumentTitle('数据源')
  const [rows, setRows] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [sourceType, setSourceType] = useState('STATIC')
  const [accessMode, setAccessMode] = useState('READONLY')
  const [secretRef, setSecretRef] = useState('')
  const [creating, setCreating] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [results, setResults] = useState<Record<number, DataSourceConnectionResult>>({})

  useAbortableEffect((signal) => {
    fetchDataSources(signal)
      .then(setRows)
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [refreshKey])

  const doCreate = async () => {
    if (creating || !name) return
    setCreating(true)
    try {
      await createDataSource({
        source_type: sourceType,
        name,
        access_mode: accessMode,
        secret_ref: secretRef || null,
      })
      toast.success('数据源已创建')
      setName('')
      setLoading(true)
      setRefreshKey((k) => k + 1)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败')
    } finally {
      setCreating(false)
    }
  }

  const doTest = async (ds: DataSource) => {
    try {
      const result = await testDataSourceConnection(ds.id)
      setResults((prev) => ({ ...prev, [ds.id]: result }))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '连接测试失败')
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold tracking-[-0.02em]">数据源管理</h2>

      <Card>
        <CardHeader>
          <CardTitle>新增数据源</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium">名称</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="订单只读库" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium">类型</label>
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
            >
              {SOURCE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium">访问模式</label>
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={accessMode}
              onChange={(e) => setAccessMode(e.target.value)}
            >
              {ACCESS_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium">secret_ref</label>
            <Input value={secretRef} onChange={(e) => setSecretRef(e.target.value)} placeholder="sec/…" />
          </div>
          <Button onClick={doCreate} disabled={creating || !name}>{creating ? '创建中…' : '创建'}</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>数据源列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>访问模式</TableHead>
                <TableHead>连接</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.name}</TableCell>
                  <TableCell><Badge variant="outline">{row.source_type}</Badge></TableCell>
                  <TableCell>{row.access_mode}</TableCell>
                  <TableCell>
                    <DataSourceConnectionBadge result={results[row.id] ?? null} />
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="secondary" size="sm" onClick={() => doTest(row)}>测试连接</Button>
                  </TableCell>
                </TableRow>
              ))}
              {rows.length === 0 && (
                <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground">暂无数据源</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
