import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { confirmExtraction, generateTestCases } from '@/api/requirement'
import type { FeatureExtractionResult, TestModule, AIGenerateResult } from '@/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Layers, ChevronDown, ChevronRight, CheckCircle2, AlertTriangle, Loader2, RefreshCw } from '@/lib/icons'

interface Props {
  open: boolean
  result: FeatureExtractionResult | null
  documentId: number | null
  onClose: () => void
  onConfirmAndGenerate: (aiResult: AIGenerateResult) => void
  onReject: () => void
}

const SEVERITY_CONFIG: Record<string, { color: string; label: string }> = {
  high: { color: '#ff4d4f', label: '高' },
  medium: { color: '#fa8c16', label: '中' },
  low: { color: '#1890ff', label: '低' },
}

const SEVERITY_BADGE_CLASSES: Record<string, string> = {
  high: 'border-red-200 bg-red-50 text-red-700',
  medium: 'border-orange-200 bg-orange-50 text-orange-700',
  low: 'border-blue-200 bg-blue-50 text-blue-700',
}

const TYPE_LABELS: Record<string, string> = {
  functional: '功能',
  ui: '界面',
  data: '数据',
  integration: '集成',
}

export default function ExtractionModal({
  open,
  result,
  documentId,
  onClose,
  onConfirmAndGenerate,
  onReject,
}: Props) {
  const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set())
  const [selectedModules, setSelectedModules] = useState<Set<string>>(new Set())
  const [rejectMode, setRejectMode] = useState(false)
  const [rejectNotes, setRejectNotes] = useState('')
  const [generating, setGenerating] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // Initialize state when result changes
  useEffect(() => {
    if (result?.modules) {
      const ids = result.modules.map((m) => m.id)
      setSelectedModules(new Set(ids))
      setExpandedModules(new Set(ids.slice(0, 2))) // expand first 2 by default
      setRejectMode(false)
      setRejectNotes('')
    }
  }, [result])

  if (!result || !documentId) return null

  const modules = result.modules || []
  const totalFps = modules.reduce((sum, m) => sum + (m.function_points?.length || 0), 0)
  const totalIssues = modules.reduce(
    (sum, m) =>
      sum +
      (m.function_points || []).reduce((s, fp) => s + (fp.issues?.length || 0), 0),
    0
  )

  const toggleModule = (id: string) => {
    setExpandedModules((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelect = (id: string) => {
    setSelectedModules((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleConfirmAndGenerate = async () => {
    if (selectedModules.size === 0) {
      toast.error('请至少选择一个模块')
      return
    }

    // Filter to only selected modules
    const confirmedModules: TestModule[] = modules.filter((m) => selectedModules.has(m.id))

    setSubmitting(true)
    try {
      // Step 1: Confirm extraction
      await confirmExtraction(documentId, {
        action: 'confirm',
        modules: confirmedModules,
      })
      toast.success('功能拆分已确认，正在生成用例...')

      // Step 2: Generate test cases with extraction
      setGenerating(true)
      try {
        const aiResult = await generateTestCases(documentId, { use_extraction: true })
        toast.success(`用例生成完成：${aiResult.functional_cases.length} 条功能用例`)
        onConfirmAndGenerate(aiResult)
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : '生成失败'
        toast.error(`用例生成失败: ${msg}`)
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '确认失败'
      toast.error(msg)
    } finally {
      setSubmitting(false)
      setGenerating(false)
    }
  }

  const handleReject = async () => {
    setSubmitting(true)
    try {
      const rejectedModuleIds = modules
        .filter((m) => !selectedModules.has(m.id))
        .map((m) => m.id)

      await confirmExtraction(documentId, {
        action: 'reject',
        rejected_modules: rejectedModuleIds,
        rejected_notes: rejectNotes,
      })
      toast.success('已标记需重新提取，可以重新进行功能拆分')
      onReject()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '操作失败'
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader className="shrink-0">
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Layers className="h-5 w-5 text-primary" />
            功能拆分 — 共 {modules.length} 个模块, {totalFps} 个功能点
          </DialogTitle>
        </DialogHeader>

        {/* Overall assessment */}
        {result.overall_assessment && (
          <Alert className="shrink-0">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-sm">{result.overall_assessment}</AlertDescription>
          </Alert>
        )}

        {result.extraction_summary && (
          <Alert variant="default" className="shrink-0 border-purple-200 bg-purple-50">
            <AlertDescription className="text-xs text-purple-700">
              {result.extraction_summary}
            </AlertDescription>
          </Alert>
        )}

        {/* Module list */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-1">
          {modules.map((mod) => {
            const isExpanded = expandedModules.has(mod.id)
            const isSelected = selectedModules.has(mod.id)
            const fpCount = mod.function_points?.length || 0
            const issueCount =
              mod.function_points?.reduce((s, fp) => s + (fp.issues?.length || 0), 0) || 0

            return (
              <Card
                key={mod.id}
                className={`border transition-colors ${
                  isSelected ? 'border-primary/40' : 'border-muted opacity-60'
                }`}
              >
                {/* Module header */}
                <div className="flex items-center gap-3 px-4 py-3">
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => toggleSelect(mod.id)}
                  />
                  <button
                    className="flex-1 flex items-center gap-2 text-left hover:opacity-80"
                    onClick={() => toggleModule(mod.id)}
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                    )}
                    <Badge variant="outline" className="font-mono text-xs">
                      {mod.id}
                    </Badge>
                    <span className="font-medium text-sm">{mod.name}</span>
                    <Badge variant="secondary" className="text-xs">
                      {fpCount} 个功能点
                    </Badge>
                    {issueCount > 0 && (
                      <Badge
                        variant="outline"
                        className="text-xs border-amber-200 bg-amber-50 text-amber-700"
                      >
                        {issueCount} 个问题
                      </Badge>
                    )}
                  </button>
                </div>

                {/* Module description */}
                {isExpanded && (
                  <CardContent className="pb-3 pt-0">
                    {mod.description && (
                      <p className="text-sm text-muted-foreground mb-3">{mod.description}</p>
                    )}

                    {/* Function points table */}
                    <div className="space-y-2">
                      {mod.function_points?.map((fp) => (
                        <div
                          key={fp.id}
                          className="border rounded-lg p-3 bg-muted/30"
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="outline" className="font-mono text-xs">
                              {fp.id}
                            </Badge>
                            <span className="text-sm font-medium">{fp.title}</span>
                            <Badge
                              variant="secondary"
                              className="text-xs"
                            >
                              {TYPE_LABELS[fp.type] || fp.type}
                            </Badge>
                          </div>
                          {fp.description && (
                            <p className="text-xs text-muted-foreground mb-2">
                              {fp.description}
                            </p>
                          )}

                          {/* Issues */}
                          {fp.issues && fp.issues.length > 0 && (
                            <div className="space-y-1.5 mt-2">
                              {fp.issues.map((issue, i) => {
                                const sev = SEVERITY_CONFIG[issue.severity] || SEVERITY_CONFIG.low
                                return (
                                  <div
                                    key={i}
                                    className="text-xs border-l-2 pl-2 py-1"
                                    style={{ borderLeftColor: sev.color }}
                                  >
                                    <Badge
                                      variant="outline"
                                      className={`text-xs mr-1 ${
                                        SEVERITY_BADGE_CLASSES[issue.severity] || ''
                                      }`}
                                    >
                                      {sev.label}
                                    </Badge>
                                    <span className="text-foreground">{issue.description}</span>
                                    {issue.suggestion && (
                                      <span className="text-muted-foreground ml-1">
                                        — 建议: {issue.suggestion}
                                      </span>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                )}
              </Card>
            )
          })}
        </div>

        {/* Footer */}
        <DialogFooter className="shrink-0 flex-col gap-2 sm:flex-row sm:justify-between pt-2 border-t">
          {/* Rejection notes */}
          {rejectMode && (
            <div className="flex-1 mr-2">
              <Textarea
                placeholder="请说明哪些部分需要重新提取，以及原因..."
                value={rejectNotes}
                onChange={(e) => setRejectNotes(e.target.value)}
                rows={2}
                className="text-sm"
              />
            </div>
          )}

          <div className="flex gap-2">
            {!rejectMode ? (
              <>
                <Button variant="ghost" onClick={onClose} disabled={submitting}>
                  关闭
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setRejectMode(true)}
                  disabled={submitting}
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  重新提取
                </Button>
                <Button
                  onClick={handleConfirmAndGenerate}
                  disabled={submitting || selectedModules.size === 0}
                >
                  {generating ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 mr-1" />
                  )}
                  {generating ? '正在生成用例...' : '确认并生成用例'}
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="ghost"
                  onClick={() => setRejectMode(false)}
                  disabled={submitting}
                >
                  取消
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleReject}
                  disabled={submitting || !rejectNotes.trim()}
                >
                  {submitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                  确认拒绝，重新提取
                </Button>
              </>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
