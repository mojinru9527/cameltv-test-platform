import { useRef, useState } from 'react'
import { toast } from 'sonner'
import {
  ArrowLeftRight,
  ArrowRight,
  Download,
  File,
  Link2,
  Loader2,
  Plus,
  RefreshCw,
  Send,
  Trash2,
} from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import useApi from '@/hooks/useApi'
import {
  fetchTransitions,
  transitionDefect,
  fetchComments,
  addComment,
  fetchAttachments,
  uploadAttachment,
  getAttachmentUrl,
  deleteAttachment,
} from '@/api/defect'
import { pushDefect, pullDefect } from '@/api/integration'
import type { DefectItem, DefectTransition, DefectComment, DefectAttachment } from '@/types'
import {
  SEVERITY_MAP,
  STATUS_MAP,
  STATUS_TRANSITIONS,
  formatFileSize,
  severityBadgeClass,
  statusBadgeClass,
} from './constants'
import DefectTransitionDialog from './DefectTransitionDialog'

interface DefectDetailSheetProps {
  detail: DefectItem
  open: boolean
  onClose: () => void
  onTransitioned: (updated: DefectItem) => void
  onMutated: () => void
  canSync: boolean
}

export default function DefectDetailSheet({
  detail,
  open,
  onClose,
  onTransitioned,
  onMutated,
  canSync,
}: DefectDetailSheetProps) {
  // ── Transitions ──
  const [transitionOpen, setTransitionOpen] = useState(false)
  const [transitionTarget, setTransitionTarget] = useState<string>('')

  const { data: transitions, refetch: refetchTransitions } = useApi<DefectTransition[]>(
    () => {
      if (!detail?.id) return Promise.resolve([])
      return fetchTransitions(detail.id)
    },
    [detail?.id],
  )

  // ── Comments ──
  const [commentText, setCommentText] = useState('')
  const [commentSubmitting, setCommentSubmitting] = useState(false)

  const { data: comments, refetch: refetchComments } = useApi<DefectComment[]>(
    () => {
      if (!detail?.id) return Promise.resolve([])
      return fetchComments(detail.id)
    },
    [detail?.id],
  )

  // ── Attachments ──
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const { data: attachments, refetch: refetchAttachments } = useApi<DefectAttachment[]>(
    () => {
      if (!detail?.id) return Promise.resolve([])
      return fetchAttachments(detail.id)
    },
    [detail?.id],
  )

  // ── Transition handlers ──
  const openTransition = (toStatus: string) => {
    setTransitionTarget(toStatus)
    setTransitionOpen(true)
  }

  const handleTransitionConfirm = async (comment: string) => {
    if (!detail?.id || !transitionTarget) return
    try {
      const updated = await transitionDefect(detail.id, {
        to_status: transitionTarget,
        comment: comment || undefined,
      })
      toast.success(`状态已更新为 ${STATUS_MAP[transitionTarget]?.label || transitionTarget}`)
      onTransitioned(updated)
      setTransitionOpen(false)
      refetchTransitions()
    } catch {
      // error toast handled by interceptor
    }
  }

  // ── Comment handlers ──
  const handleAddComment = async () => {
    if (!detail?.id || !commentText.trim()) return
    setCommentSubmitting(true)
    try {
      await addComment(detail.id, commentText.trim())
      setCommentText('')
      toast.success('评论已添加')
      refetchComments()
    } catch {
      // error toast handled by interceptor
    } finally {
      setCommentSubmitting(false)
    }
  }

  // ── Attachment handlers ──
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !detail?.id) return
    setUploading(true)
    try {
      await uploadAttachment(detail.id, file)
      toast.success('文件已上传')
      refetchAttachments()
    } catch {
      // error toast handled by interceptor
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDeleteAttachment = async (attachmentId: number) => {
    if (!detail?.id) return
    try {
      await deleteAttachment(detail.id, attachmentId)
      toast.success('附件已删除')
      refetchAttachments()
    } catch {
      // error toast handled by interceptor
    }
  }

  return (
    <>
      <Sheet open={open} onOpenChange={(open) => { if (!open) onClose() }}>
        <SheetContent className="sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle>缺陷详情</SheetTitle>
          </SheetHeader>
          <Tabs defaultValue="info" className="flex flex-col flex-1 mt-4 overflow-hidden">
            <TabsList className="w-full">
              <TabsTrigger value="info" className="flex-1">详情</TabsTrigger>
              <TabsTrigger value="comments" className="flex-1">评论</TabsTrigger>
              <TabsTrigger value="attachments" className="flex-1">附件</TabsTrigger>
              <TabsTrigger value="history" className="flex-1">历史</TabsTrigger>
            </TabsList>

            {/* ── Tab 1: 详情 ── */}
            <TabsContent value="info" className="flex-1 overflow-y-auto mt-4">
              {/* Status badge + transition buttons */}
              <div className="flex items-center gap-2 mb-4 flex-wrap">
                <span className="text-sm text-muted-foreground">状态:</span>
                <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[detail.status]?.color)}>
                  {STATUS_MAP[detail.status]?.label || detail.status}
                </Badge>
                {STATUS_TRANSITIONS[detail.status]?.length > 0 && (
                  <div className="flex items-center gap-1.5 ml-2">
                    <ArrowLeftRight className="size-3.5 text-muted-foreground" />
                    {STATUS_TRANSITIONS[detail.status].map((toStatus) => (
                      <Button
                        key={toStatus}
                        size="xs"
                        variant="outline"
                        onClick={() => openTransition(toStatus)}
                      >
                        <ArrowRight className="size-3 mr-1" />
                        {STATUS_MAP[toStatus]?.label || toStatus}
                      </Button>
                    ))}
                  </div>
                )}
              </div>

              <dl className="grid grid-cols-2 border rounded-lg">
                {[
                  ['编号', detail.defect_id],
                  ['标题', detail.title],
                  ['严重程度', <Badge key="sev" variant="outline" className={severityBadgeClass(SEVERITY_MAP[detail.severity]?.color)}>{SEVERITY_MAP[detail.severity]?.label}</Badge>],
                  ['处理人', detail.assignee_name || '-'],
                  ['创建人', detail.creator_name || '-'],
                  ['关联用例', detail.case_title || (detail.case_id ? `#${detail.case_id}` : '-')],
                  ['外部ID', detail.external_id || '-'],
                  ['创建时间', detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '-'],
                  ['更新时间', detail.updated_at ? new Date(detail.updated_at).toLocaleString('zh-CN') : '-'],
                  ['解决时间', detail.resolved_at ? new Date(detail.resolved_at).toLocaleString('zh-CN') : '-'],
                ].map(([label, value]) => (
                  <div key={label as string} className="flex flex-col border-b border-r p-2 even:border-r-0 [&:nth-last-child(-n+2)]:border-b-0">
                    <dt className="text-xs text-muted-foreground">{label}</dt>
                    <dd className="text-sm mt-0.5">{value}</dd>
                  </div>
                ))}
              </dl>

              {detail.external_url && (
                <p className="flex items-center gap-1 mt-4">
                  <Link2 className="size-4" />
                  <a href={detail.external_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                    查看外部链接
                  </a>
                </p>
              )}

              {/* Sync buttons */}
              {canSync && (
                <div className="flex items-center gap-2 mt-4 pt-3 border-t">
                  <span className="text-xs text-muted-foreground">同步:</span>
                  <Button
                    variant="outline" size="sm"
                    onClick={async () => {
                      const iid = prompt('请输入集成配置 ID (可在集成配置页查看):')
                      if (!iid) return
                      try {
                        await pushDefect(detail.id, Number(iid))
                        toast.success('推送成功')
                        onMutated()
                      } catch (e: any) { toast.error(e?.message || '推送失败') }
                    }}
                  >
                    <RefreshCw className="size-3 mr-1" />推送
                  </Button>
                  {detail.external_id && (
                    <Button
                      variant="outline" size="sm"
                      onClick={async () => {
                        const iid = prompt('请输入集成配置 ID:')
                        if (!iid) return
                        try {
                          await pullDefect(detail.id, Number(iid))
                          toast.success('拉取成功')
                          onMutated()
                        } catch (e: any) { toast.error(e?.message || '拉取失败') }
                      }}
                    >
                      <RefreshCw className="size-3 mr-1" />拉取
                    </Button>
                  )}
                </div>
              )}

              {detail.description && (
                <Card size="sm" className="mt-4">
                  <div className="text-sm font-medium px-[var(--card-spacing)] pt-[var(--card-spacing)]">详细描述</div>
                  <CardContent>
                    <pre className="whitespace-pre-wrap m-0 text-sm">{detail.description}</pre>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* ── Tab 2: 评论 ── */}
            <TabsContent value="comments" className="flex flex-col flex-1 overflow-hidden mt-4">
              <div className="flex-1 overflow-y-auto space-y-3">
                {comments && comments.length > 0 ? (
                  comments.map((c) => (
                    <div key={c.id} className="border rounded-lg p-3">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-medium">{c.author_name || '匿名'}</span>
                        <span className="text-xs text-muted-foreground">
                          {c.created_at ? new Date(c.created_at).toLocaleString('zh-CN') : '-'}
                        </span>
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{c.content}</p>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-muted-foreground text-sm py-8">暂无评论</div>
                )}
              </div>
              <Separator className="my-3" />
              <div className="flex gap-2">
                <Textarea
                  id="detail-comment"
                  rows={2}
                  placeholder="输入评论..."
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                      e.preventDefault()
                      handleAddComment()
                    }
                  }}
                  className="flex-1"
                />
                <Button
                  size="sm"
                  onClick={handleAddComment}
                  disabled={commentSubmitting || !commentText.trim()}
                  className="self-end"
                >
                  {commentSubmitting ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                </Button>
              </div>
            </TabsContent>

            {/* ── Tab 3: 附件 ── */}
            <TabsContent value="attachments" className="flex flex-col flex-1 overflow-hidden mt-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-muted-foreground">
                  {attachments ? `${attachments.length} 个文件` : '加载中...'}
                </span>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  onChange={handleFileSelect}
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  {uploading ? (
                    <Loader2 className="size-4 animate-spin mr-1" />
                  ) : (
                    <Plus className="size-4 mr-1" />
                  )}
                  上传文件
                </Button>
              </div>
              <div className="flex-1 overflow-y-auto space-y-2">
                {attachments && attachments.length > 0 ? (
                  attachments.map((att) => (
                    <div key={att.id} className="flex items-center gap-3 border rounded-lg p-3">
                      <File className="size-5 text-muted-foreground shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{att.filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatFileSize(att.file_size)}
                          {att.uploader_name ? ` · ${att.uploader_name}` : ''}
                          {att.created_at ? ` · ${new Date(att.created_at).toLocaleString('zh-CN')}` : ''}
                        </p>
                      </div>
                      <a
                        href={getAttachmentUrl(detail.id, att.id)}
                        download={att.filename}
                        className="shrink-0"
                      >
                        <Button size="xs" variant="ghost" type="button">
                          <Download className="size-4" />
                        </Button>
                      </a>
                      <Button
                        size="xs"
                        variant="ghost"
                        className="text-destructive hover:text-destructive shrink-0"
                        onClick={() => handleDeleteAttachment(att.id)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-muted-foreground text-sm py-8">暂无附件</div>
                )}
              </div>
            </TabsContent>

            {/* ── Tab 4: 历史 ── */}
            <TabsContent value="history" className="flex-1 overflow-y-auto mt-4">
              {transitions && transitions.length > 0 ? (
                <div className="relative pl-6 border-l-2 border-muted space-y-4">
                  {transitions.map((t) => (
                    <div key={t.id} className="relative">
                      <div className="absolute -left-[25px] top-1 size-2.5 rounded-full border-2 border-muted-foreground/30 bg-background" />
                      <div className="flex items-center gap-1.5 text-sm">
                        <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[t.from_status]?.color)}>
                          {STATUS_MAP[t.from_status]?.label || t.from_status}
                        </Badge>
                        <ArrowRight className="size-3 text-muted-foreground" />
                        <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[t.to_status]?.color)}>
                          {STATUS_MAP[t.to_status]?.label || t.to_status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
                        {t.operator_name && <span>{t.operator_name}</span>}
                        <span>{t.created_at ? new Date(t.created_at).toLocaleString('zh-CN') : '-'}</span>
                      </div>
                      {t.comment && (
                        <p className="text-sm text-muted-foreground mt-1 bg-muted/50 rounded px-2 py-1">{t.comment}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground text-sm py-8">暂无流转记录</div>
              )}
            </TabsContent>
          </Tabs>
        </SheetContent>
      </Sheet>

      {/* Transition Dialog (rendered inside DetailSheet since it depends on detail state) */}
      <DefectTransitionDialog
        open={transitionOpen}
        currentStatus={detail.status}
        targetStatus={transitionTarget}
        onClose={() => setTransitionOpen(false)}
        onConfirm={handleTransitionConfirm}
      />
    </>
  )
}
