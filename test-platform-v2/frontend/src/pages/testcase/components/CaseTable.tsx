import { Fragment, useState } from 'react'
import { useNavigate } from 'react-router'
import { Badge, Button } from '@/ui'
import type { BadgeTone } from '@/ui'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { AsyncState } from '@/components/state'
import { CheckCircle2, ChevronDown, ChevronRight, Edit, History, Send, Trash2, XCircle, MessageSquare } from '@/lib/icons'
import { formatNumberedText, formatStepActions, formatStepExpectations } from '../caseListFormatters'

const PRIORITY_TONES: Record<string, BadgeTone> = { P0: 'danger', P1: 'warning', P2: 'info', P3: 'neutral' }
const REVIEW_LABELS: Record<string, string> = { draft: '草稿', submitted: '已提交', approved: '已通过', rejected: '已驳回' }
const REVIEW_TONES: Record<string, BadgeTone> = { draft: 'neutral', submitted: 'info', approved: 'success', rejected: 'danger' }
const CASE_NATURE_LABELS: Record<string, string> = { positive: '正向', negative: '负向', boundary: '边界' }
const CASE_NATURE_TONES: Record<string, BadgeTone> = { positive: 'success', negative: 'danger', boundary: 'warning' }

interface CaseTableProps {
  isLoading: boolean
  isError: boolean
  error: Error | null
  data: { total: number; items: any[]; page: number; page_size: number } | null | undefined
  sortedItems: any[]
  refetch: () => void
  activeFilters: {
    keyword: string
    selSurface: string
    selDomain: string
    selModule: string
    caseNature: string
    priority: string
  }
  onClearFilters: () => void
  canCreate: boolean
  canBatchSelect: boolean
  selected: Set<number>
  onToggleSelectAll: () => void
  onToggleSelect: (id: number) => void
  canSubmitReview: boolean
  canApproveReview: boolean
  canUpdate: boolean
  canDelete: boolean
  deleteTarget: number | null
  setDeleteTarget: (v: number | null) => void
  onDelete: (id: number) => void
  onEdit: (row?: any) => void
  onOpenVersionHistory: (row: any) => void
  onOpenReviewDialog: (row: any, action: string) => void
}

export default function CaseTable({
  isLoading,
  isError,
  error,
  data,
  sortedItems,
  refetch,
  activeFilters,
  onClearFilters,
  canCreate,
  canBatchSelect,
  selected,
  onToggleSelectAll,
  onToggleSelect,
  canSubmitReview,
  canApproveReview,
  canUpdate,
  canDelete,
  deleteTarget,
  setDeleteTarget,
  onDelete,
  onEdit,
  onOpenVersionHistory,
  onOpenReviewDialog,
}: CaseTableProps) {
  const navigate = useNavigate()
  const { keyword, selSurface, selDomain, selModule, caseNature, priority } = activeFilters

  // Batch 183（FIX-173-P3-10）：行内展开查看步骤/预期配对（折叠三列高密度全文）
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())
  const toggleExpanded = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div
      className="flex-1 min-h-0 overflow-auto rounded-md border"
      role="region"
      aria-label="测试用例数据表"
      tabIndex={0}
      data-density={sortedItems.length >= 50 ? 'high' : 'standard'}
    >
      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={data?.items}
        onRetry={refetch}
        emptyTitle="暂无测试用例"
        emptyDescription="点击「新建用例」开始创建"
        emptyAction={keyword || selSurface || selDomain || selModule || caseNature || priority
          ? {
              label: '清除筛选',
              onClick: onClearFilters,
            }
          : canCreate
            ? { label: '新建用例', onClick: () => onEdit() }
            : undefined}
        skeletonType="table"
        loadingRows={4}
      >
        {() => (
          <div className="min-w-0 overflow-x-auto">
            <Table className="ui-table min-w-[900px] [&_td]:py-2.5">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]">
                    {canBatchSelect && <Checkbox
                      checked={selected.size === sortedItems.length && sortedItems.length > 0}
                      onCheckedChange={onToggleSelectAll}
                      aria-label="选择当前页全部用例"
                    />}
                  </TableHead>
                  <TableHead className="w-[100px]">模块名称</TableHead>
                  <TableHead className="w-[160px]">用例标题</TableHead>
                  <TableHead className="w-[70px]">用例等级</TableHead>
                  <TableHead className="w-[64px]">场景</TableHead>
                  <TableHead className="w-[60px]">评审</TableHead>
                  <TableHead className="sticky right-0 z-20 w-[132px] bg-card shadow-[-10px_0_18px_-16px_hsl(var(--foreground))]">
                    操作
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedItems.map((r: any) => (
                  <Fragment key={r.id}>
                  <TableRow
                    className={sortedItems.length >= 50 ? '[content-visibility:auto] [contain-intrinsic-size:auto_44px]' : undefined}
                  >
                    <TableCell>
                      {canBatchSelect && <Checkbox
                        checked={selected.has(r.id)}
                        onCheckedChange={() => onToggleSelect(r.id)}
                        aria-label={`选择用例：${r.title || r.id}`}
                      />}
                    </TableCell>
                    <TableCell className="max-w-[100px] truncate">
                      <span
                        className="line-clamp-1"
                        title={[r.taxonomy_domain, r.taxonomy_module].filter(Boolean).join(' / ')}
                      >
                        {r.taxonomy_domain || r.module || '......'}
                      </span>
                    </TableCell>
                    <TableCell className="max-w-[160px] truncate">
                      <div className="flex items-center gap-1">
                        <Button
                          size="icon-xs"
                          variant="ghost"
                          onClick={() => toggleExpanded(r.id)}
                          aria-label={`${expandedIds.has(r.id) ? '收起' : '展开'}用例内容：${r.title || r.id}`}
                        >
                          {expandedIds.has(r.id)
                            ? <ChevronDown className="size-3" aria-hidden="true" />
                            : <ChevronRight className="size-3" aria-hidden="true" />}
                        </Button>
                        <button
                          type="button"
                          onClick={() => onEdit(r)}
                          className="line-clamp-1 text-left hover:text-primary hover:underline"
                          title={`查看/编辑用例：${r.title || r.id}`}
                        >
                          {r.title || '......'}
                        </button>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge tone={PRIORITY_TONES[r.priority] || 'neutral'}>
                        {r.priority}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge tone={CASE_NATURE_TONES[r.positive_negative] || 'neutral'}>
                        {CASE_NATURE_LABELS[r.positive_negative] || '未标注'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge tone={REVIEW_TONES[r.review_status] || 'neutral'} className="text-xs">
                        {REVIEW_LABELS[r.review_status] || r.review_status || '草稿'}
                      </Badge>
                    </TableCell>
                    <TableCell className="sticky right-0 z-10 bg-card shadow-[-10px_0_18px_-16px_hsl(var(--foreground))]">
                      <div className="flex items-center gap-1">
                        <Button
                          size="icon-xs"
                          variant="ghost"
                          onClick={() => navigate(`/dsh-tasks?scene=functional&hint=${encodeURIComponent(r.title || '')}`)}
                          aria-label={`用 DSH 补充用例：${r.title || r.id}`}
                          title="用 DSH 场景向导补充用例"
                        >
                          <MessageSquare className="size-3" aria-hidden="true" />
                        </Button>
                        <Button
                          size="icon-xs"
                          variant="ghost"
                          onClick={() => onOpenVersionHistory(r)}
                          aria-label={`查看版本历史：${r.title || r.id}`}
                        >
                          <History className="size-3" aria-hidden="true" />
                        </Button>
                        {/* Review actions (batch-34) */}
                        {canSubmitReview && r.review_status === 'draft' && (
                          <Button
                            size="icon-xs"
                            variant="ghost"
                            onClick={() => onOpenReviewDialog(r, 'submit')}
                            aria-label={`提交评审：${r.title || r.id}`}
                          >
                            <Send className="size-3 text-status-info" aria-hidden="true" />
                          </Button>
                        )}
                        {canApproveReview && r.review_status === 'submitted' && (
                          <>
                            <Button
                              size="icon-xs"
                              variant="ghost"
                              onClick={() => onOpenReviewDialog(r, 'approve')}
                              aria-label={`通过评审：${r.title || r.id}`}
                            >
                              <CheckCircle2 className="size-3 text-status-success" aria-hidden="true" />
                            </Button>
                            <Button
                              size="icon-xs"
                              variant="ghost"
                              onClick={() => onOpenReviewDialog(r, 'reject')}
                              aria-label={`驳回评审：${r.title || r.id}`}
                            >
                              <XCircle className="size-3 text-status-danger" aria-hidden="true" />
                            </Button>
                          </>
                        )}
                        {canUpdate && <Button
                          size="icon-xs"
                          variant="ghost"
                          onClick={() => onEdit(r)}
                          aria-label={`编辑用例：${r.title || r.id}`}
                        >
                          <Edit className="size-3" aria-hidden="true" />
                        </Button>}
                        {canDelete && <AlertDialog open={deleteTarget === r.id} onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}>
                          <AlertDialogTrigger asChild>
                            <Button
                              size="icon-xs"
                              variant="ghost"
                              className="text-destructive hover:bg-destructive/10"
                              onClick={() => setDeleteTarget(r.id)}
                              aria-label={`删除用例：${r.title || r.id}`}
                            >
                              <Trash2 className="size-3" aria-hidden="true" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent size="sm">
                            <AlertDialogHeader>
                              <AlertDialogTitle>确定删除？</AlertDialogTitle>
                              <AlertDialogDescription>此操作不可撤销。</AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>取消</AlertDialogCancel>
                              <AlertDialogAction variant="destructive" onClick={() => onDelete(r.id)}>删除</AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>}
                      </div>
                    </TableCell>
                  </TableRow>
                  {expandedIds.has(r.id) && (
                    <TableRow className="bg-muted/30">
                      <TableCell colSpan={7} className="px-6 py-3 text-sm">
                        <div className="space-y-2">
                          {formatNumberedText(r.preconditions).length > 0 && (
                            <div className="text-xs text-muted-foreground">
                              <span className="font-medium">前置条件：</span>
                              {formatNumberedText(r.preconditions).join(' ')}
                            </div>
                          )}
                          <div className="grid gap-1.5">
                            {(() => {
                              const actions = formatStepActions(r.steps)
                              const expectations = formatStepExpectations(r.steps, r.expected_result)
                              if (!actions.length) return null
                              const rows = actions.map((action, index) => ({
                                action,
                                expected: expectations[index] || '—',
                              }))
                              return rows.map((row, index) => (
                                <div key={index} className="grid grid-cols-1 gap-0.5 md:grid-cols-2 md:gap-4">
                                  <div className="text-xs">
                                    <span className="text-muted-foreground">步骤 {index + 1}：</span>
                                    <span className="whitespace-pre-wrap break-words">{row.action.replace(/^\d+、/, '')}</span>
                                  </div>
                                  <div className="text-xs">
                                    <span className="text-muted-foreground">预期 {index + 1}：</span>
                                    <span className="whitespace-pre-wrap break-words text-status-success">{row.expected.replace(/^\d+、/, '')}</span>
                                  </div>
                                </div>
                              ))
                            })()}
                          </div>
                          {!formatStepActions(r.steps).length && formatNumberedText(r.expected_result).length > 0 && (
                            <div className="text-xs text-muted-foreground">
                              <span className="font-medium">预期结果：</span>
                              {formatNumberedText(r.expected_result).join(' ')}
                            </div>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </AsyncState>
    </div>
  )
}
