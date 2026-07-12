import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  fetchIterations,
  createIteration,
  closeIteration,
  fetchSnapshots,
  compareIterations,
  type KnowledgeIteration,
  type KnowledgeSnapshot,
  type CompareSnapshots,
} from '@/api/knowledge'
import { Plus, Inbox, RefreshCw, ArrowLeftRight, TrendingUp, ArrowDown } from '@/lib/icons'

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  active: { label: '进行中', color: 'bg-green-100 text-green-700' },
  closed: { label: '已关闭', color: 'bg-muted text-muted-foreground' },
}

export default function IterationTab() {
  const [iterations, setIterations] = useState<KnowledgeIteration[]>([])
  const [loading, setLoading] = useState(true)

  // Create dialog
  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newVersion, setNewVersion] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [creating, setCreating] = useState(false)

  // Snapshots side panel
  const [selectedIter, setSelectedIter] = useState<KnowledgeIteration | null>(null)
  const [snapshots, setSnapshots] = useState<KnowledgeSnapshot[]>([])
  const [snapLoading, setSnapLoading] = useState(false)

  // Compare
  const [compareBase, setCompareBase] = useState<number | null>(null)
  const [compareResult, setCompareResult] = useState<CompareSnapshots | null>(null)
  const [comparing, setComparing] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    fetchIterations({ page_size: 50 })
      .then((res) => setIterations(res.items))
      .catch(() => toast.error('加载迭代列表失败'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      await createIteration({ iteration_name: newName.trim(), version: newVersion.trim(), description: newDesc.trim() })
      toast.success('迭代已创建')
      setCreateOpen(false)
      setNewName(''); setNewVersion(''); setNewDesc('')
      load()
    } catch (e: any) {
      toast.error(e?.message || '创建失败')
    } finally {
      setCreating(false)
    }
  }

  const handleClose = async (id: number) => {
    try {
      await closeIteration(id)
      toast.success('迭代已关闭，快照已生成')
      load()
    } catch (e: any) {
      toast.error(e?.message || '关闭失败')
    }
  }

  const handleViewSnapshots = async (iter: KnowledgeIteration) => {
    setSelectedIter(iter)
    setCompareResult(null)
    setSnapLoading(true)
    try {
      const snaps = await fetchSnapshots(iter.id)
      setSnapshots(snaps)
    } catch {
      toast.error('加载快照失败')
    } finally {
      setSnapLoading(false)
    }
  }

  const handleCompare = async () => {
    if (!selectedIter || !compareBase) return
    setComparing(true)
    try {
      const result = await compareIterations(selectedIter.id, compareBase)
      setCompareResult(result)
    } catch (e: any) {
      toast.error(e?.message || '对比失败')
    } finally {
      setComparing(false)
    }
  }

  const safeParse = (s: string) => {
    try { return JSON.parse(s) } catch { return {} }
  }

  return (
    <div className="space-y-4">
      {/* 顶部操作栏 */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">
          迭代列表
          <span className="ml-2 text-xs text-muted-foreground">
            {iterations.length} 个迭代
          </span>
        </h3>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`size-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="size-4 mr-1" />
            新建迭代
          </Button>
        </div>
      </div>

      {/* 迭代列表 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>迭代名称</TableHead>
                <TableHead className="w-20">版本</TableHead>
                <TableHead className="w-24">状态</TableHead>
                <TableHead className="w-32">时间范围</TableHead>
                <TableHead className="w-32">创建时间</TableHead>
                <TableHead className="w-36">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                  </TableRow>
                ))
              ) : iterations.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                    暂无迭代。创建迭代来追踪知识增长。
                  </TableCell>
                </TableRow>
              ) : (
                iterations.map((it) => {
                  const badge = STATUS_BADGE[it.status] ?? { label: it.status, color: '' }
                  return (
                    <TableRow key={it.id}>
                      <TableCell className="font-medium text-sm">{it.iteration_name}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{it.version || '-'}</TableCell>
                      <TableCell><Badge className={badge.color}>{badge.label}</Badge></TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {it.start_date?.slice(0, 10) || '-'} ~ {it.end_date?.slice(0, 10) || '-'}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {it.created_at?.slice(0, 19)?.replace('T', ' ') || '-'}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => handleViewSnapshots(it)}>
                            快照
                          </Button>
                          {it.status === 'active' && (
                            <Button variant="ghost" size="sm" className="h-7 text-xs text-amber-600" onClick={() => handleClose(it.id)}>
                              <Inbox className="size-3 mr-1" />
                              关闭
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 快照/对比面板 */}
      {selectedIter && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">
                快照浏览 — {selectedIter.iteration_name}
              </CardTitle>
              <Button variant="ghost" size="sm" className="h-7" onClick={() => { setSelectedIter(null); setSnapshots([]); setCompareResult(null) }}>
                关闭
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 快照列表 */}
            <div>
              <h4 className="text-xs font-medium mb-2">快照数据</h4>
              {snapLoading ? (
                <Skeleton className="h-20 w-full" />
              ) : snapshots.length === 0 ? (
                <p className="text-xs text-muted-foreground">暂无快照（关闭迭代时自动生成）</p>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  {snapshots.map((snap) => {
                    const data = safeParse(snap.data_json)
                    return (
                      <Card key={snap.id} className="border border-muted">
                        <CardContent className="p-3">
                          <div className="flex items-center justify-between mb-1">
                            <Badge variant="outline" className="text-xs">{snap.snapshot_type}</Badge>
                          </div>
                          <pre className="text-xs text-muted-foreground max-h-24 overflow-auto">
                            {JSON.stringify(data, null, 2)}
                          </pre>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              )}
            </div>

            {/* 跨迭代对比 */}
            <div className="border-t pt-4">
              <h4 className="text-xs font-medium mb-2">跨迭代对比</h4>
              <div className="flex items-center gap-2 mb-3">
                <Label className="text-xs">基准迭代:</Label>
                <Select value={compareBase?.toString() || ''} onValueChange={(v) => setCompareBase(Number(v))}>
                  <SelectTrigger className="w-48 h-8 text-xs">
                    <SelectValue placeholder="选择基准迭代" />
                  </SelectTrigger>
                  <SelectContent>
                    {iterations.filter((it) => it.id !== selectedIter.id).map((it) => (
                      <SelectItem key={it.id} value={it.id.toString()}>
                        {it.iteration_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button size="sm" className="h-7 text-xs" onClick={handleCompare} disabled={!compareBase || comparing}>
                  <ArrowLeftRight className="size-3 mr-1" />
                  对比
                </Button>
              </div>

              {compareResult && (
                <div className="space-y-3">
                  <div className="text-xs text-muted-foreground">
                    对比: {compareResult.base_iteration_name} → {compareResult.target_iteration_name}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="rounded-md bg-muted p-3">
                      <div className="text-xs text-muted-foreground mb-1">实体变化</div>
                      <div className={`text-lg font-bold flex items-center gap-1 ${(compareResult.deltas.entity_total ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {(compareResult.deltas.entity_total ?? 0) >= 0 ? <TrendingUp className="size-4" /> : <ArrowDown className="size-4" />}
                        {(compareResult.deltas.entity_total ?? 0) > 0 ? '+' : ''}{compareResult.deltas.entity_total ?? 0}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        增长率: {((compareResult.trends.entity_growth_rate ?? 0) * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="rounded-md bg-muted p-3">
                      <div className="text-xs text-muted-foreground mb-1">关系变化</div>
                      <div className={`text-lg font-bold flex items-center gap-1 ${(compareResult.deltas.relation_total ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {(compareResult.deltas.relation_total ?? 0) >= 0 ? <TrendingUp className="size-4" /> : <ArrowDown className="size-4" />}
                        {(compareResult.deltas.relation_total ?? 0) > 0 ? '+' : ''}{compareResult.deltas.relation_total ?? 0}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        增长率: {((compareResult.trends.relation_growth_rate ?? 0) * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  <pre className="text-xs bg-muted p-3 rounded-md max-h-40 overflow-auto">
                    {JSON.stringify(compareResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 创建迭代 Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建迭代</DialogTitle>
            <DialogDescription>创建一个知识迭代，用于追踪知识增长和变更。</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <div>
              <Label>迭代名称 *</Label>
              <Input
                placeholder="如: 2026-07 Sprint 1"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div>
              <Label>版本号</Label>
              <Input
                placeholder="如: v14.1.0"
                value={newVersion}
                onChange={(e) => setNewVersion(e.target.value)}
              />
            </div>
            <div>
              <Label>描述</Label>
              <Textarea
                placeholder="迭代目标/范围说明"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>取消</Button>
            <Button onClick={handleCreate} disabled={creating || !newName.trim()}>
              {creating ? '创建中…' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
