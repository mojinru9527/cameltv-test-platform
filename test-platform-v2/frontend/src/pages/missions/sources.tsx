import { useState } from 'react'
import { useParams } from 'react-router'
import { toast } from 'sonner'
import {
  Badge,
  Button,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
  Textarea,
} from '@/ui'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  attachMissionSource,
  fetchMissionSources,
  fetchSourceFragments,
  parseMissionSource,
  PARSE_STATUS_LABELS,
  SOURCE_TYPE_LABELS,
  type SourceArtifact,
  type SourceFragment,
} from '@/api/sources'
import { Plus, FileText, RefreshCw } from '@/lib/icons'

export default function MissionSourcesPage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('资料')

  const [sources, setSources] = useState<SourceArtifact[]>([])
  const [loading, setLoading] = useState(true)
  const [attachOpen, setAttachOpen] = useState(false)
  const [fragOpen, setFragOpen] = useState(false)
  const [activeSource, setActiveSource] = useState<SourceArtifact | null>(null)
  const [fragments, setFragments] = useState<SourceFragment[]>([])
  const [parsingId, setParsingId] = useState<number | null>(null)

  // attach form state
  const [attachType, setAttachType] = useState('MANUAL_NOTE')
  const [attachName, setAttachName] = useState('')
  const [attachContent, setAttachContent] = useState('')
  const [attachUri, setAttachUri] = useState('')
  const [attachDocId, setAttachDocId] = useState('')

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    fetchMissionSources(missionId)
      .then(setSources)
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId, loading])

  const openFragments = async (source: SourceArtifact) => {
    setActiveSource(source)
    setFragOpen(true)
    try {
      const rows = await fetchSourceFragments(missionId, source.id)
      setFragments(rows)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载片段失败')
      setFragments([])
    }
  }

  const doParse = async (source: SourceArtifact) => {
    setParsingId(source.id)
    try {
      await parseMissionSource(missionId, source.id)
      toast.success('解析完成')
      setLoading(true)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '解析失败')
    } finally {
      setParsingId(null)
    }
  }

  const doAttach = async () => {
    try {
      const payload = {
        source_type: attachType as 'REQUIREMENT' | 'OPENAPI' | 'MANUAL_NOTE',
        name: attachName || null,
        content: attachType === 'MANUAL_NOTE' ? attachContent : null,
        uri: attachType === 'OPENAPI' ? attachUri : null,
        requirement_doc_id: attachType === 'REQUIREMENT' && attachDocId ? Number(attachDocId) : null,
      }
      await attachMissionSource(missionId, payload)
      toast.success('已添加 Source')
      setAttachOpen(false)
      setAttachName('')
      setAttachContent('')
      setAttachUri('')
      setAttachDocId('')
      setLoading(true)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '添加失败')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">导入 / 关联测试所需原始资料</p>
        <Button onClick={() => setAttachOpen(true)}>
          <Plus className="size-4" /> 添加 Source
        </Button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>解析状态</TableHead>
                <TableHead>片段</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sources.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-10 text-center text-muted-foreground">
                    <FileText className="mx-auto mb-2 size-8 opacity-50" />
                    尚未添加 Source。点击「添加 Source」导入 PRD / OpenAPI / 补充说明。
                  </TableCell>
                </TableRow>
              ) : (
                sources.map((s) => {
                  const ps = PARSE_STATUS_LABELS[s.parse_status]
                  return (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium">{s.name}</TableCell>
                      <TableCell>{SOURCE_TYPE_LABELS[s.source_type] ?? s.source_type}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={ps?.color}>
                          {ps?.label ?? s.parse_status}
                        </Badge>
                      </TableCell>
                      <TableCell>{s.fragment_count}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          {s.parse_status !== 'PARSED' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={parsingId === s.id}
                              onClick={() => doParse(s)}
                            >
                              <RefreshCw className="size-3.5" /> 解析
                            </Button>
                          )}
                          <Button variant="ghost" size="sm" onClick={() => openFragments(s)}>
                            片段
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={attachOpen} onOpenChange={setAttachOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加 Source</DialogTitle>
            <DialogDescription>导入或关联测试原始资料</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>来源类型</Label>
              <Select value={attachType} onValueChange={setAttachType}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MANUAL_NOTE">人工补充说明</SelectItem>
                  <SelectItem value="REQUIREMENT">需求文档</SelectItem>
                  <SelectItem value="OPENAPI">OpenAPI</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>名称</Label>
              <Input value={attachName} onChange={(e) => setAttachName(e.target.value)} />
            </div>
            {attachType === 'MANUAL_NOTE' && (
              <div className="space-y-1.5">
                <Label>内容</Label>
                <Textarea
                  rows={4}
                  value={attachContent}
                  onChange={(e) => setAttachContent(e.target.value)}
                />
              </div>
            )}
            {attachType === 'OPENAPI' && (
              <div className="space-y-1.5">
                <Label>OpenAPI URL / 引用</Label>
                <Input
                  value={attachUri}
                  placeholder="https://…/openapi.json"
                  onChange={(e) => setAttachUri(e.target.value)}
                />
              </div>
            )}
            {attachType === 'REQUIREMENT' && (
              <div className="space-y-1.5">
                <Label>需求文档 ID</Label>
                <Input
                  value={attachDocId}
                  placeholder="需求文档 ID"
                  onChange={(e) => setAttachDocId(e.target.value)}
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAttachOpen(false)}>
              取消
            </Button>
            <Button onClick={doAttach}>添加</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={fragOpen} onOpenChange={setFragOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Source 片段</DialogTitle>
            <DialogDescription>{activeSource?.name}</DialogDescription>
          </DialogHeader>
          <div className="max-h-[50vh] space-y-2 overflow-y-auto">
            {fragments.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                暂无片段，请先解析该 Source。
              </p>
            ) : (
              fragments.map((f) => (
                <div key={f.id} className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">
                    {f.fragment_key} · {f.title}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm">{f.text}</p>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
