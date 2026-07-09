import { useState, useCallback } from 'react'
import { Upload, Trash2, Eye, Plus, RefreshCw, FileText, FileJson } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Pagination from '@/components/Pagination'
import PageHeader from '@/components/PageHeader'
import { AsyncState } from '@/components/state/AsyncState'
import { useApi } from '@/hooks/useApi'

import {
  fetchDatasets, fetchDataset, createDataset, updateDataset, deleteDataset,
  uploadDatasetFile, previewDatasetRaw,
} from '@/api/dataset'
import type { DatasetListItem } from '@/types'

export default function DatasetPage() {
  const [page, setPage] = useState(1)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [detailId, setDetailId] = useState<number | null>(null)

  // Form state
  const [formName, setFormName] = useState('')
  const [formDesc, setFormDesc] = useState('')
  const [formType, setFormType] = useState<'csv' | 'json'>('csv')
  const [formContent, setFormContent] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<{ columns: string[]; rows: Record<string, string>[]; total_rows: number } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const { data: listData, isLoading, isError, error, refetch } = useApi(
    () => fetchDatasets({ page, page_size: 20 }),
    [page]
  )

  const { data: detailData, isLoading: detailLoading, refetch: refetchDetail } = useApi(
    () => detailId ? fetchDataset(detailId) : Promise.resolve(null),
    [detailId]
  )

  // ── Preview raw content ──
  const handlePreview = useCallback(async (content: string, type: string) => {
    if (!content.trim()) { setPreview(null); return }
    setPreviewLoading(true)
    try {
      const p = await previewDatasetRaw(content, type)
      setPreview(p)
    } catch {
      setPreview(null)
    } finally {
      setPreviewLoading(false)
    }
  }, [])

  // ── File upload ──
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setUploadFile(f)
    // Detect type from extension
    const ext = f.name.split('.').pop()?.toLowerCase()
    if (ext === 'json') setFormType('json')
    else setFormType('csv')
    // Read file content for preview
    const reader = new FileReader()
    reader.onload = (ev) => {
      const text = ev.target?.result as string
      setFormContent(text)
      handlePreview(text, ext === 'json' ? 'json' : 'csv')
    }
    reader.readAsText(f)
  }, [handlePreview])

  // ── Open create dialog ──
  const openCreate = () => {
    setEditingId(null)
    setFormName('')
    setFormDesc('')
    setFormType('csv')
    setFormContent('')
    setUploadFile(null)
    setPreview(null)
    setDialogOpen(true)
  }

  // ── Open edit dialog ──
  const openEdit = async (id: number) => {
    try {
      const d = await fetchDataset(id)
      setEditingId(id)
      setFormName(d.name)
      setFormDesc(d.description)
      setFormType(d.source_type as 'csv' | 'json')
      setFormContent(d.raw_content)
      setUploadFile(null)
      setDialogOpen(true)
      handlePreview(d.raw_content, d.source_type)
    } catch {
      toast.error('加载数据集失败')
    }
  }

  // ── Submit ──
  const handleSubmit = async () => {
    if (!formName.trim()) { toast.error('请输入数据集名称'); return }
    if (!formContent.trim()) { toast.error('请输入或上传数据内容'); return }

    try {
      if (uploadFile && !editingId) {
        await uploadDatasetFile(uploadFile, formName, formDesc)
      } else if (editingId) {
        await updateDataset(editingId, { name: formName, description: formDesc, raw_content: formContent })
      } else {
        await createDataset({ name: formName, description: formDesc, source_type: formType, raw_content: formContent })
      }
      toast.success(editingId ? '数据集已更新' : '数据集已创建')
      setDialogOpen(false)
      refetch()
    } catch (e: any) {
      toast.error(e?.response?.data?.message || e?.message || '操作失败')
    }
  }

  // ── Delete ──
  const handleDelete = async (id: number) => {
    if (!confirm('确定删除此数据集？')) return
    try {
      await deleteDataset(id)
      toast.success('已删除')
      refetch()
    } catch {
      toast.error('删除失败')
    }
  }

  // ── View detail ──
  const handleViewDetail = (id: number) => {
    setDetailId(id)
  }

  const items = listData?.items || []
  const total = listData?.total || 0

  return (
    <div className="space-y-4">
      <PageHeader
        title="测试数据集"
        description="管理 CSV/JSON 测试数据，支持参数化注入到 API 用例执行中"
        icon={FileText}
      >
        <Button onClick={openCreate} size="sm">
          <Plus className="size-4 mr-1" />
          新建数据集
        </Button>
      </PageHeader>

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={items}
        emptyTitle="暂无数据集"
        emptyDescription="点击「新建数据集」上传 CSV 或 JSON 文件"
        onRetry={refetch}
      >
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead className="w-16">类型</TableHead>
                  <TableHead className="w-20">行数</TableHead>
                  <TableHead className="w-40">列名</TableHead>
                  <TableHead className="w-40">更新时间</TableHead>
                  <TableHead className="w-32 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item: DatasetListItem) => {
                  let columns: string[] = []
                  try { columns = JSON.parse(item.columns_meta) } catch { /* ignore */ }
                  return (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.name}</TableCell>
                      <TableCell>
                        <Badge variant={item.source_type === 'json' ? 'secondary' : 'outline'}>
                          {item.source_type.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell>{item.row_count}</TableCell>
                      <TableCell className="text-muted-foreground text-xs truncate max-w-[160px]">
                        {columns.join(', ') || '-'}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-xs">
                        {item.updated_at?.slice(0, 10) || '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" onClick={() => handleViewDetail(item.id)} title="查看详情">
                            <Eye className="size-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => openEdit(item.id)} title="编辑">
                            <FileText className="size-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleDelete(item.id)} title="删除">
                            <Trash2 className="size-4 text-red-500" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
        {total > 20 && (
          <div className="flex justify-center pt-2">
            <Pagination page={page} totalPages={Math.ceil(total / 20)} total={total} onChange={setPage} />
          </div>
        )}
      </AsyncState>

      {/* ── Create/Edit Dialog ── */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? '编辑数据集' : '新建数据集'}</DialogTitle>
            <DialogDescription>
              上传 CSV 或 JSON 文件，或手动粘贴数据内容
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Name */}
            <div>
              <Label htmlFor="ds-name">名称 *</Label>
              <Input
                id="ds-name"
                value={formName}
                onChange={e => setFormName(e.target.value)}
                placeholder="例如：登录测试数据"
              />
            </div>

            {/* Description */}
            <div>
              <Label htmlFor="ds-desc">描述</Label>
              <Input
                id="ds-desc"
                value={formDesc}
                onChange={e => setFormDesc(e.target.value)}
                placeholder="数据集用途说明"
              />
            </div>

            {/* Type + File upload */}
            {!editingId && (
              <div className="flex gap-3 items-end">
                <div className="w-32">
                  <Label>数据格式</Label>
                  <Select value={formType} onValueChange={v => { setFormType(v as any); handlePreview(formContent, v) }}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="csv">CSV</SelectItem>
                      <SelectItem value="json">JSON</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1">
                  <Label>文件上传</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="file"
                      accept=".csv,.json"
                      onChange={handleFileChange}
                      className="cursor-pointer"
                    />
                    {uploadFile && <span className="text-xs text-muted-foreground whitespace-nowrap">{uploadFile.name}</span>}
                  </div>
                </div>
              </div>
            )}

            {/* Content textarea */}
            <div>
              <Label htmlFor="ds-content">数据内容 *</Label>
              <Textarea
                id="ds-content"
                value={formContent}
                onChange={e => { setFormContent(e.target.value); handlePreview(e.target.value, formType) }}
                placeholder={formType === 'csv'
                  ? 'name,email,password\n测试用户1,user1@test.com,pass123\n测试用户2,user2@test.com,pass456'
                  : '[{"name":"测试用户1","email":"user1@test.com"},{"name":"测试用户2","email":"user2@test.com"}]'
                }
                className="min-h-[160px] font-mono text-xs"
                rows={8}
              />
            </div>

            {/* Preview */}
            <div>
              <Label className="flex items-center gap-2">
                数据预览
                {previewLoading && <RefreshCw className="size-3 animate-spin" />}
                {preview && <span className="text-xs text-muted-foreground">({preview.total_rows} 行, {preview.columns.length} 列)</span>}
              </Label>
              {preview && preview.columns.length > 0 ? (
                <div className="border rounded-md max-h-[200px] overflow-auto mt-1">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12 text-center">#</TableHead>
                        {preview.columns.map(c => <TableHead key={c} className="text-xs">{c}</TableHead>)}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {preview.rows.map((row, i) => (
                        <TableRow key={i}>
                          <TableCell className="text-center text-xs text-muted-foreground">{i + 1}</TableCell>
                          {preview.columns.map(c => (
                            <TableCell key={c} className="text-xs font-mono max-w-[200px] truncate">
                              {row[c] ?? '-'}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-xs text-muted-foreground mt-1">
                  {formContent.trim() ? '无法解析数据，请检查格式' : '输入数据后自动预览'}
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={handleSubmit}>{editingId ? '保存' : '创建'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Detail Dialog ── */}
      <Dialog open={!!detailId} onOpenChange={() => setDetailId(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <AsyncState isLoading={detailLoading} isError={false} error={null} data={detailData}>
            {detailData && (
              <>
                <DialogHeader>
                  <DialogTitle>{detailData.name}</DialogTitle>
                  <DialogDescription>
                    {detailData.source_type.toUpperCase()} · {detailData.row_count} 行 · 创建于 {detailData.created_at?.slice(0, 10)}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                  {detailData.description && (
                    <p className="text-sm text-muted-foreground">{detailData.description}</p>
                  )}
                  {/* Full data preview */}
                  {(() => {
                    let cols: string[] = []
                    try { cols = JSON.parse(detailData.columns_meta) } catch { /* */ }
                    let rows: Record<string, string>[] = []
                    if (detailData.source_type === 'csv') {
                      const lines = detailData.raw_content.trim().split('\n')
                      if (lines.length > 1) {
                        const headers = lines[0].split(',')
                        rows = lines.slice(1).map(line => {
                          const vals = line.split(',')
                          const obj: Record<string, string> = {}
                          headers.forEach((h, i) => { obj[h.trim()] = vals[i]?.trim() ?? '' })
                          return obj
                        })
                      }
                    } else if (detailData.source_type === 'json') {
                      try { rows = JSON.parse(detailData.raw_content) } catch { /* */ }
                    }
                    return (
                      <div className="border rounded-md max-h-[400px] overflow-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-12 text-center">#</TableHead>
                              {cols.map(c => <TableHead key={c} className="text-xs">{c}</TableHead>)}
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {rows.slice(0, 100).map((row, i) => (
                              <TableRow key={i}>
                                <TableCell className="text-center text-xs text-muted-foreground">{i + 1}</TableCell>
                                {cols.map(c => (
                                  <TableCell key={c} className="text-xs font-mono max-w-[200px] truncate">
                                    {row[c] ?? '-'}
                                  </TableCell>
                                ))}
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                        {rows.length > 100 && (
                          <div className="text-center text-xs text-muted-foreground py-2">
                            仅显示前 100 行，共 {rows.length} 行
                          </div>
                        )}
                      </div>
                    )
                  })()}
                </div>
              </>
            )}
          </AsyncState>
        </DialogContent>
      </Dialog>
    </div>
  )
}
