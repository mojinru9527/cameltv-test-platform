import { Badge, Button, type BadgeTone } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/ui'
import Pagination from '@/components/Pagination'
import { AsyncState } from '@/components/state'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  Trash2, Eye, FileSpreadsheet, FileText,
  Layers, Link2, Search, XCircle, Loader2, ExternalLink, GitCompare, Sparkles, Inbox,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import type { RequirementDocumentBrief } from '@/types'

export const TYPE_TAG: Record<string, { className: string; label: string; icon: React.ReactNode }> = {
  md: { className: 'border-status-info-border bg-status-info-muted text-status-info', label: 'Markdown', icon: <FileText className="size-3" /> },
  docx: { className: 'border-status-info-border bg-status-info-muted text-status-info', label: 'Word', icon: <FileText className="size-3" /> },
  xlsx: { className: 'border-status-success-border bg-status-success-muted text-status-success', label: 'Excel', icon: <FileSpreadsheet className="size-3" /> },
  lanhu: { className: 'border-status-accent-border bg-status-accent-muted text-status-accent', label: '蓝湖', icon: <Link2 className="size-3" /> },
}

// ── Source ref display helpers ──
function formatSourceRef(sourceRef: string, fileType: string): { label: string; isLink: boolean } {
  if (!sourceRef) return { label: '-', isLink: false }
  if (fileType === 'lanhu') {
    // Extract version from lanhu URL: .../updates/{version} or query param
    const versionMatch = sourceRef.match(/\/updates\/([\d.]+)/) || sourceRef.match(/[?&]v(?:ersion)?=([\d.]+)/)
    if (versionMatch) {
      return { label: `蓝湖 v${versionMatch[1]}`, isLink: true }
    }
    return { label: '蓝湖链接', isLink: true }
  }
  // Non-lanhu: extract domain
  try {
    const url = new URL(sourceRef)
    return { label: url.hostname, isLink: true }
  } catch {
    return { label: sourceRef.length > 30 ? sourceRef.slice(0, 30) + '...' : sourceRef, isLink: false }
  }
}

const STATUS_VARIANT: Record<string, { tone: BadgeTone; className?: string; label: string }> = {
  uploaded: { tone: 'neutral', label: '已上传' },
  parsed: { tone: 'neutral', label: '已解析' },
  generated: { tone: 'info', className: 'border-status-info-border bg-status-info-muted text-status-info', label: '已生成' },
  imported: { tone: 'success', className: 'border-status-success-border bg-status-success-muted text-status-success', label: '已导入' },
}

interface Props {
  docs: RequirementDocumentBrief[]
  keyword: string
  activeDocId: number | null
  canWriteDocs: boolean
  generating: boolean
  generatingDocId: number | null
  extracting: boolean
  extractingDocId: number | null
  isLoading: boolean
  isError: boolean
  error: Error | null
  refetch: () => void
  debouncedKeyword: string
  page: number
  totalPages: number
  total: number
  aiConfigured: boolean
  onKeywordChange: (value: string) => void
  onClearKeyword: () => void
  onPreviewDoc: (id: number) => void
  onGenerate: (docId: number, useExtraction: boolean) => void
  onExtract: (docId: number) => void
  onReExtract: (docId: number) => void
  onViewCases: (docId: number) => void
  onDelete: (doc: RequirementDocumentBrief) => void
  onNavigate: (path: string) => void
  onOpenVersionCompare: (diffData: any) => void
  onPageChange: (page: number) => void
}

export default function RequirementDocTable({
  docs,
  keyword,
  activeDocId,
  canWriteDocs,
  generating,
  generatingDocId,
  extracting,
  extractingDocId,
  isLoading,
  isError,
  error,
  refetch,
  debouncedKeyword,
  page,
  totalPages,
  total,
  aiConfigured,
  onKeywordChange,
  onClearKeyword,
  onPreviewDoc,
  onGenerate,
  onExtract,
  onReExtract,
  onViewCases,
  onDelete,
  onNavigate,
  onOpenVersionCompare,
  onPageChange,
}: Props) {
  return (
    <Card size="sm" className="ui-surface">
      <CardHeader className="border-b pb-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Search className="size-4" />
            需求文档记录
          </CardTitle>
          <div className="relative w-[180px]">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground pointer-events-none" />
            <Input
              className="pl-7 h-7 text-xs"
              placeholder="搜索文档"
              value={keyword}
              onChange={(e) => onKeywordChange(e.target.value)}
            />
            {keyword && (
              <button
                type="button"
                className="absolute right-0 top-1/2 min-h-9 min-w-9 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                onClick={onClearKeyword}
                aria-label="清空文档搜索"
              >
                <XCircle className="size-3.5" />
              </button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <AsyncState
          isLoading={isLoading}
          isError={isError}
          error={error}
          data={docs.length > 0 ? docs : ([] as any[])}
          onRetry={refetch}
          emptyTitle="暂无需求文档"
          emptyDescription={debouncedKeyword ? '没有找到匹配的需求文档' : '请上传需求文档开始使用'}
          emptyIcon={Inbox}
          skeletonType="table"
          loadingRows={3}
        >
          {() => (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[180px]">标题</TableHead>
                  <TableHead className="w-[200px]">来源</TableHead>
                  <TableHead className="w-[80px] text-center">状态</TableHead>
                  <TableHead className="w-[70px] text-center">导入</TableHead>
                  <TableHead className="w-[100px]">操作人</TableHead>
                  <TableHead className="w-[110px]">时间</TableHead>
                  <TableHead className="w-[260px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {docs.map((r) => {
                  const isActive = r.id === activeDocId
                  return (
                    <TableRow
                      key={r.id}
                      className={cn(isActive && 'bg-accent')}
                      data-state={isActive ? 'selected' : undefined}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            className="max-w-[140px] truncate rounded-sm text-left font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            onClick={() => onPreviewDoc(r.id)}
                            aria-pressed={isActive}
                            aria-label={`预览需求文档：${r.title}`}
                          >
                            {r.title}
                          </button>
                          {r.file_type && TYPE_TAG[r.file_type] && (
                            <Badge tone="neutral" className={cn('gap-1 shrink-0', TYPE_TAG[r.file_type].className)}>
                              {TYPE_TAG[r.file_type].icon}
                              {TYPE_TAG[r.file_type].label}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="max-w-[200px]">
                        {(() => {
                          const { label, isLink } = formatSourceRef(r.source_ref, r.file_type)
                          if (isLink && r.file_type === 'lanhu') {
                            return (
                              <a
                                href={r.source_ref}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-status-info hover:underline inline-flex items-center gap-1 truncate"
                                title={r.source_ref}
                                onClick={(e) => e.stopPropagation()}
                              >
                                <ExternalLink className="size-3 shrink-0" />
                                <span className="truncate">{label}</span>
                              </a>
                            )
                          }
                          if (isLink) {
                            return (
                              <a
                                href={r.source_ref}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-muted-foreground hover:underline truncate block"
                                title={r.source_ref}
                                onClick={(e) => e.stopPropagation()}
                              >
                                {label}
                              </a>
                            )
                          }
                          return <span className="text-xs text-muted-foreground truncate block" title={r.source_ref}>{label}</span>
                        })()}
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center gap-1 flex-wrap justify-center">
                        {r.extraction_status === 'pending_review' && (
                          <Badge tone="neutral" className="border-status-warning-border bg-status-warning-muted text-status-warning text-xs">待审核</Badge>
                        )}
                        {r.extraction_status === 'confirmed' && (
                          <Badge tone="neutral" className="border-status-info-border bg-status-info-muted text-status-info text-xs">已拆分</Badge>
                        )}
                        {(() => {
                          const t = STATUS_VARIANT[r.status]
                          if (!t) return <Badge tone="neutral">{r.status}</Badge>
                          if (r.status === 'imported' || r.status === 'generated') {
                            const hasFunc = r.imported_func_count > 0
                            if (hasFunc) {
                              return (
                                <Badge tone="neutral" className="border-status-success-border bg-status-success-muted text-status-success">
                                  功能用例已导入
                                </Badge>
                              )
                            }
                          }
                          return (
                            <Badge tone={t.tone} className={t.className}>
                              {t.label}
                            </Badge>
                          )
                        })()}
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        {r.imported_func_count > 0 ? (
                          <span className="text-sm font-semibold text-status-success tabular-nums">
                            {r.imported_func_count}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">{r.creator_name || '-'}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {r.created_at ? new Date(r.created_at).toLocaleDateString('zh-CN') : '-'}
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-1 flex-wrap">
                          {r.file_type === 'lanhu' && (
                            <Button
                              size="sm"
                              variant="ghost"
                              title="在知识中心对该需求发起 RAG vs Wiki 差异对比"
                              onClick={() => onNavigate(`/knowledge?tab=wikidiff&q=${encodeURIComponent(r.title || '')}`)}
                            >
                              <GitCompare className="size-3.5" />
                              发起对比
                            </Button>
                          )}
                          {(r.status === 'uploaded' || r.status === 'parsed') && (
                            <>
                              {/* Stage 1: Feature Extraction buttons */}
                              {r.extraction_status === 'confirmed' ? (
                                <Button
                                  size="sm"
                                  variant="primary"
                                  disabled={!canWriteDocs || !aiConfigured || (generating && generatingDocId === r.id)}
                                  title={!aiConfigured ? '当前项目未配置 AI 提供方' : undefined}
                                  onClick={() => onGenerate(r.id, true)}
                                >
                                  {generating && generatingDocId === r.id ? (
                                    <Loader2 className="size-3.5 animate-spin" />
                                  ) : (
                                    <Sparkles className="size-3.5" />
                                  )}
                                  生成用例(基于拆分)
                                </Button>
                              ) : r.extraction_status === 'pending_review' ? (
                                <Button
                                  size="sm"
                                  variant="primary"
                                  disabled={!canWriteDocs || !aiConfigured || (extracting && extractingDocId === r.id)}
                                  title={!aiConfigured ? '当前项目未配置 AI 提供方' : undefined}
                                  onClick={() => onExtract(r.id)}
                                >
                                  {extracting && extractingDocId === r.id ? (
                                    <Loader2 className="size-3.5 animate-spin" />
                                  ) : (
                                    <Layers className="size-3.5" />
                                  )}
                                  继续审核
                                </Button>
                              ) : (
                                <Button
                                  size="sm"
                                  variant="primary"
                                  disabled={!canWriteDocs || !aiConfigured || (extracting && extractingDocId === r.id)}
                                  title={!aiConfigured ? '当前项目未配置 AI 提供方' : undefined}
                                  onClick={() => onExtract(r.id)}
                                >
                                  {extracting && extractingDocId === r.id ? (
                                    <Loader2 className="size-3.5 animate-spin" />
                                  ) : (
                                    <Layers className="size-3.5" />
                                  )}
                                  功能拆分
                                </Button>
                              )}

                              {/* Stage 2: Direct AI Generation (backward compat) */}
                              <Button
                                size="sm"
                                variant="secondary"
                                disabled={!canWriteDocs || !aiConfigured || (
                                  r.extraction_status === 'confirmed'
                                    ? extracting && extractingDocId === r.id
                                    : generating && generatingDocId === r.id
                                )}
                                title={!aiConfigured ? '当前项目未配置 AI 提供方' : undefined}
                                onClick={() => {
                                  if (r.extraction_status === 'confirmed') {
                                    onReExtract(r.id)
                                  } else {
                                    onGenerate(r.id, false)
                                  }
                                }}
                              >
                                {(generating && generatingDocId === r.id)
                                  || (extracting && extractingDocId === r.id) ? (
                                  <Loader2 className="size-3.5 animate-spin" />
                                ) : r.extraction_status === 'confirmed' ? (
                                  <Layers className="size-3.5" />
                                ) : (
                                  <Sparkles className="size-3.5" />
                                )}
                                {r.extraction_status === 'confirmed' ? '重新拆分' : 'AI 生成'}
                              </Button>

                              {/* Version compare (batch-28): shown when diff_json exists */}
                              {r.diff_json && (() => {
                                try {
                                  const diffData = typeof r.diff_json === 'string' ? JSON.parse(r.diff_json) : r.diff_json
                                  if (diffData?.pages) {
                                    return (
                                      <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => onOpenVersionCompare(diffData)}
                                      >
                                        <GitCompare className="size-3.5" />
                                        版本对比
                                      </Button>
                                    )
                                  }
                                } catch { /* invalid JSON, hide button */ }
                                return null
                              })()}
                            </>
                          )}
                          {r.status === 'generated' && (
                            <>
                              <Button
                                size="sm"
                                variant="secondary"
                                disabled={!canWriteDocs || (generating && generatingDocId === r.id)}
                                onClick={() => onGenerate(r.id, false)}
                              >
                                {generating && generatingDocId === r.id ? (
                                  <Loader2 className="size-3.5 animate-spin" />
                                ) : (
                                  <Sparkles className="size-3.5" />
                                )}
                                重新生成
                              </Button>
                              {r.imported_count > 0 && (
                                <Badge tone="neutral" className="border-status-success-border bg-status-success-muted text-status-success">
                                  已导入 {r.imported_count} 条
                                </Badge>
                              )}
                            </>
                          )}
                          {r.status === 'imported' && (
                            <>
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => onGenerate(r.id, false)}
                              >
                                <Sparkles className="size-3.5" />
                                重新生成
                              </Button>
                              <Badge tone="neutral" className="border-status-success-border bg-status-success-muted text-status-success">
                                已导入 {r.imported_count} 条
                              </Badge>
                            </>
                          )}
                          {(r.status === 'generated' || r.status === 'imported') && (
                            <>
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => onViewCases(r.id)}
                              >
                                <Eye className="size-3.5" />
                                查看用例
                              </Button>
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => onNavigate(`/requirement/${r.id}/review`)}
                              >
                                <Layers className="size-3.5" />
                                审查用例
                              </Button>
                            </>
                          )}
                          <Button
                            size="sm"
                            variant="secondary"
                            title="用 DSH 场景向导生成功能用例"
                            onClick={() => onNavigate(`/dsh-tasks?scene=functional&hint=${encodeURIComponent(r.title || '')}`)}
                          >
                            <Sparkles className="size-3.5" />
                            用 DSH 生成
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            disabled={!canWriteDocs}
                            onClick={() => onDelete(r)}
                          >
                            <Trash2 className="size-3.5" />
                            删除
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
            {/* Pagination */}
            <Pagination
              page={page}
              totalPages={totalPages}
              total={total}
              onChange={onPageChange}
            />
          </>
          )}
        </AsyncState>
      </CardContent>
    </Card>
  )
}
