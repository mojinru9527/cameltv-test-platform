/**
 * TriagePanel — AI 智能分诊面板，展示执行失败用例的 AI 分类结果。
 *
 * 用法：
 * <TriagePanel planId={planId} />
 *
 * 流程：
 * 1. 点击「开始分诊」→ 调用 POST /test-plans/{id}/triage
 * 2. 展示按分类（bug/flaky_env/case_defect/known_issue）分组的结果
 * 3. bug 类显示「一键提缺陷」按钮 → 生成草稿 → 创建缺陷
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { SkeletonText } from '@/components/ui/skeleton'
import EmptyState from '@/components/EmptyState'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

import {
  Bug,
  AlertTriangle,
  FlaskConical,
  Info,
  Sparkles,
  Loader2,
  Zap,
  ArrowRight,
  RotateCcw,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { triagePlanFailures, triageDraftDefect } from '@/api/testplan'
import { createDefect } from '@/api/defect'

// ── Types ────────────────────────────────────────────────

interface TriageClassified {
  execution_id: number
  case_id: number
  case_title: string
  case_type: string
  priority: string
  category: 'bug' | 'flaky_env' | 'case_defect' | 'known_issue'
  confidence: number
  explanation: string
  suggested_action: string
  notes: string
  result_data: Record<string, any>
  executed_at: string
}

interface TriageResult {
  plan_id: number
  total_failures: number
  classified: TriageClassified[]
  summary: Record<string, number>
  analysis_method: 'llm' | 'rule_only'
}

interface TriagePanelProps {
  planId: number
  /** Only show the button if there are failed executions to analyze (optional hint) */
  hasFailures?: boolean
}

// ── Category config ──────────────────────────────────────

const CATEGORY_CONFIG: Record<string, {
  label: string
  icon: React.ReactNode
  color: string
  bgClass: string
  borderClass: string
}> = {
  bug: {
    label: 'Bug',
    icon: <Bug className="size-4" />,
    color: 'text-destructive',
    bgClass: 'bg-destructive/5 border-destructive/20',
    borderClass: 'border-l-destructive',
  },
  flaky_env: {
    label: '环境抖动',
    icon: <AlertTriangle className="size-4" />,
    color: 'text-orange-500',
    bgClass: 'bg-orange-50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-800',
    borderClass: 'border-l-orange-400',
  },
  case_defect: {
    label: '用例缺陷',
    icon: <FlaskConical className="size-4" />,
    color: 'text-blue-500',
    bgClass: 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800',
    borderClass: 'border-l-blue-400',
  },
  known_issue: {
    label: '已知问题',
    icon: <Info className="size-4" />,
    color: 'text-muted-foreground',
    bgClass: 'bg-muted/30 border-border',
    borderClass: 'border-l-muted-foreground',
  },
}

// ── Component ─────────────────────────────────────────────

export default function TriagePanel({ planId, hasFailures }: TriagePanelProps) {
  const navigate = useNavigate()

  const [result, setResult] = useState<TriageResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Defect creation
  const [creatingFor, setCreatingFor] = useState<number | null>(null)
  const [defectConfirm, setDefectConfirm] = useState<{
    open: boolean
    draft: Record<string, any> | null
  }>({ open: false, draft: null })

  // ── Trigger triage ──

  const handleTriage = async () => {
    setLoading(true)
    setError(null)
    try {
      const data: TriageResult = await triagePlanFailures(planId)
      setResult(data)
      if (data.total_failures === 0) {
        toast.info('没有失败的用例需要分诊')
      } else {
        toast.success(`分诊完成 — ${data.analysis_method === 'llm' ? 'AI 深度分析' : '规则引擎'}，共 ${data.total_failures} 条`)
      }
    } catch (err: any) {
      const msg = err?.detail || err?.message || '分诊失败'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  // ── One-click defect ──

  const handleDraftDefect = async (item: TriageClassified) => {
    setCreatingFor(item.execution_id)
    try {
      const draft = await triageDraftDefect(planId, item.execution_id)
      setDefectConfirm({ open: true, draft })
    } catch (err: any) {
      const msg = err?.detail || err?.message || '生成缺陷草稿失败'
      toast.error(msg)
    } finally {
      setCreatingFor(null)
    }
  }

  const confirmCreateDefect = async () => {
    if (!defectConfirm.draft) return
    try {
      const created = await createDefect(defectConfirm.draft)
      toast.success('缺陷已创建')
      setDefectConfirm({ open: false, draft: null })
      // Navigate to defect detail
      const defectId = (created as any)?.id
      if (defectId) navigate(`/defect/${defectId}`)
    } catch (err: any) {
      const msg = err?.detail || err?.message || '创建缺陷失败'
      toast.error(msg)
    }
  }

  // ── Group by category ──

  const grouped = groupBy(result?.classified || [], (c) => c.category)
  const categoryOrder = ['bug', 'flaky_env', 'case_defect', 'known_issue']

  // ── Render ──

  const showTrigger = !result && !loading

  return (
    <div className="space-y-4">
      {/* Trigger / Retry */}
      {showTrigger && (
        <div className="flex items-center gap-3 py-2">
          <Button onClick={handleTriage} disabled={loading}>
            <Sparkles className="size-4" data-icon="inline-start" />
            开始 AI 分诊
          </Button>
          <span className="text-xs text-muted-foreground">
            分析执行失败的用例，AI 自动分类为 Bug / 环境抖动 / 用例缺陷 / 已知问题
          </span>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-3 py-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            AI 正在分析失败用例...
          </div>
          <SkeletonText lines={4} />
        </div>
      )}

      {/* Error + retry */}
      {error && !result && (
        <EmptyState
          title="分诊失败"
          description={error}
          action={{ label: '重试', onClick: handleTriage }}
        />
      )}

      {/* No failures */}
      {result && result.total_failures === 0 && (
        <EmptyState
          title="没有失败的用例"
          description="当前计划所有用例均已通过或待执行"
        />
      )}

      {/* Results */}
      {result && result.total_failures > 0 && (
        <div className="space-y-4">
          {/* Summary bar */}
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm font-medium">分诊结果：</span>
            {categoryOrder.map((cat) => {
              const count = result.summary[cat] || 0
              if (count === 0) return null
              const cfg = CATEGORY_CONFIG[cat]
              return (
                <Badge key={cat} variant="outline" className={cn('gap-1', cfg.color)}>
                  {cfg.icon}
                  {cfg.label} × {count}
                </Badge>
              )
            })}
            <Badge variant="secondary" className="text-[11px]">
              {result.analysis_method === 'llm' ? 'AI 深度分析' : '规则引擎'}
            </Badge>
            <Button variant="ghost" size="sm" onClick={handleTriage} disabled={loading} className="ml-auto">
              <RotateCcw className="size-3.5" data-icon="inline-start" />
              重新分诊
            </Button>
          </div>

          {/* Category groups */}
          {categoryOrder.map((cat) => {
            const items = grouped[cat]
            if (!items || items.length === 0) return null
            const cfg = CATEGORY_CONFIG[cat]
            return (
              <div key={cat} className="space-y-2">
                <h4 className={cn('text-sm font-semibold flex items-center gap-1.5', cfg.color)}>
                  {cfg.icon}
                  {cfg.label} ({items.length})
                </h4>
                <div className="space-y-2">
                  {items.map((item) => (
                    <Card
                      key={item.execution_id}
                      size="sm"
                      className={cn('border-l-4', cfg.borderClass, cfg.bgClass)}
                    >
                      <CardContent className="py-3 space-y-2">
                        {/* Header */}
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-sm font-medium truncate">
                                {item.case_title}
                              </span>
                              <Badge variant="outline" className="text-[10px]">
                                {item.priority}
                              </Badge>
                              <Badge variant="secondary" className="text-[10px]">
                                置信度 {(item.confidence * 100).toFixed(0)}%
                              </Badge>
                            </div>
                          </div>
                          {/* Actions */}
                          <div className="flex items-center gap-1 shrink-0">
                            {item.category === 'bug' && (
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={() => handleDraftDefect(item)}
                                disabled={creatingFor === item.execution_id}
                              >
                                {creatingFor === item.execution_id ? (
                                  <Loader2 className="size-3.5 animate-spin" data-icon="inline-start" />
                                ) : (
                                  <Zap className="size-3.5" data-icon="inline-start" />
                                )}
                                一键提缺陷
                              </Button>
                            )}
                          </div>
                        </div>

                        {/* Explanation */}
                        {item.explanation && (
                          <p className="text-xs text-muted-foreground">{item.explanation}</p>
                        )}

                        {/* Suggested action */}
                        {item.suggested_action && (
                          <div className="text-xs space-y-0.5">
                            <span className="font-medium text-muted-foreground">建议操作：</span>
                            <pre className="whitespace-pre-wrap text-muted-foreground text-[11px]">
                              {item.suggested_action}
                            </pre>
                          </div>
                        )}

                        {/* Footer: time + case type */}
                        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                          {item.executed_at && (
                            <span>执行时间：{new Date(item.executed_at).toLocaleString()}</span>
                          )}
                          {item.case_type && (
                            <Badge variant="outline" className="text-[10px]">
                              {item.case_type === 'api' ? '接口' : item.case_type === 'func' ? '功能' : item.case_type}
                            </Badge>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Defect confirm dialog */}
      <AlertDialog
        open={defectConfirm.open}
        onOpenChange={(open) => { if (!open) setDefectConfirm({ open: false, draft: null }) }}
      >
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>确认创建缺陷？</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2 mt-2">
                <p className="text-sm font-medium">{defectConfirm.draft?.title}</p>
                <pre className="whitespace-pre-wrap text-xs text-muted-foreground max-h-40 overflow-auto border rounded p-2">
                  {defectConfirm.draft?.description}
                </pre>
                <p className="text-xs text-muted-foreground">
                  严重度：{defectConfirm.draft?.severity}
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={confirmCreateDefect}>
              <ArrowRight className="size-3.5" data-icon="inline-start" />
              创建并查看
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

// ── Helper ────────────────────────────────────────────────

function groupBy<T>(items: T[], keyFn: (item: T) => string): Record<string, T[]> {
  const groups: Record<string, T[]> = {}
  for (const item of items) {
    const key = keyFn(item)
    if (!groups[key]) groups[key] = []
    groups[key].push(item)
  }
  return groups
}
