import { useState } from 'react'
import { toast } from 'sonner'
import { Upload, Link2, FileText, Loader2 } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
// Label inline — no shadcn Label component available
import { previewOpenApiImport, confirmOpenApiImport } from '@/api/apitest'
import { useAuthStore } from '@/stores/auth'
import type { ApiImportPreview } from '@/types'

interface Props {
  open: boolean
  onClose: () => void
  onImported: () => void
}

export default function ImportDialog({ open, onClose, onImported }: Props) {
  const projectId = useAuthStore(s => s.currentProjectId)
  const [importTab, setImportTab] = useState('url')
  const [serviceName, setServiceName] = useState('')
  const [sourceRef, setSourceRef] = useState('')
  const [specContent, setSpecContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState<ApiImportPreview | null>(null)
  const [importing, setImporting] = useState(false)

  const doPreview = async () => {
    if (!serviceName.trim()) { toast.error('请输入服务名称'); return }
    if (!projectId) { toast.error('未选择项目'); return }
    setLoading(true)
    setPreview(null)
    try {
      const sourceType = importTab === 'url' ? 'openapi_url' : 'openapi_text'
      const result = await previewOpenApiImport(projectId, {
        service_name: serviceName,
        source_type: sourceType,
        source_ref: sourceRef,
        spec_content: specContent || undefined,
      })
      setPreview(result)
    } catch (e: any) {
      toast.error(e?.message || '预览失败')
    } finally { setLoading(false) }
  }

  const doImport = async () => {
    if (!preview || !projectId) return
    setImporting(true)
    try {
      const sourceType = importTab === 'url' ? 'openapi_url' : 'openapi_text'
      await confirmOpenApiImport(projectId, {
        service_name: serviceName,
        source_type: sourceType,
        source_ref: sourceRef,
        spec_content: specContent || undefined,
        generate_cases: true,
      })
      toast.success(`导入完成: ${preview.total_count} 个接口`)
      onImported()
      reset()
    } catch (e: any) {
      toast.error(e?.message || '导入失败')
    } finally { setImporting(false) }
  }

  const reset = () => {
    setServiceName(''); setSourceRef(''); setSpecContent('')
    setPreview(null); onClose()
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) reset() }}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>导入 OpenAPI / Swagger</DialogTitle>
          <DialogDescription>支持 OpenAPI 3.x 和 Swagger 2.0 格式</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1.5 block">服务名称 *</label>
            <Input placeholder="例如: account-service" value={serviceName} onChange={e => setServiceName(e.target.value)} />
          </div>

          <Tabs value={importTab} onValueChange={setImportTab}>
            <TabsList>
              <TabsTrigger value="url"><Link2 className="size-4 mr-1" />URL 导入</TabsTrigger>
              <TabsTrigger value="text"><FileText className="size-4 mr-1" />文本导入</TabsTrigger>
            </TabsList>
            <TabsContent value="url" className="mt-2">
              <Input placeholder="https://example.com/openapi.json" value={sourceRef} onChange={e => setSourceRef(e.target.value)} />
            </TabsContent>
            <TabsContent value="text" className="mt-2">
              <Textarea
                rows={10}
                placeholder='粘贴 OpenAPI JSON/YAML ...'
                value={specContent}
                onChange={e => setSpecContent(e.target.value)}
              />
            </TabsContent>
          </Tabs>

          <Button onClick={doPreview} disabled={loading || !serviceName.trim()} className="w-full">
            {loading ? <Loader2 className="animate-spin size-4 mr-2" /> : null}
            预览导入
          </Button>

          {preview && (
            <div className="border rounded-lg p-4 space-y-3 bg-muted/30">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="outline">版本: {preview.version || 'N/A'}</Badge>
                <Badge className="bg-blue-100 text-blue-700">总计: {preview.total_count}</Badge>
                <Badge className="bg-green-100 text-green-700">新增: {preview.new_count}</Badge>
                {preview.existing_count > 0 && <Badge className="bg-yellow-100 text-yellow-700">已存在: {preview.existing_count}</Badge>}
              </div>
              <div className="max-h-48 overflow-y-auto space-y-1">
                {preview.endpoints.slice(0, 20).map((ep, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs p-1.5 rounded bg-background">
                    <Badge className="text-[10px] px-1 py-0">{ep.method}</Badge>
                    <code className="flex-1 truncate">{ep.path}</code>
                    <span className="text-muted-foreground truncate max-w-[120px]">{ep.summary}</span>
                    {ep._exists && <Badge variant="outline" className="text-[10px]">已存在</Badge>}
                  </div>
                ))}
                {preview.endpoints.length > 20 && (
                  <p className="text-xs text-muted-foreground text-center">... 还有 {preview.endpoints.length - 20} 个接口</p>
                )}
              </div>
              <Button onClick={doImport} disabled={importing} className="w-full" variant="default">
                {importing ? <Loader2 className="animate-spin size-4 mr-2" /> : <Upload className="size-4 mr-2" />}
                确认导入并生成用例
              </Button>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={reset}>取消</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
