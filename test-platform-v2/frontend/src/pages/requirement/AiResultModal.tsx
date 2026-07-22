import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { confirmExtraction, generateTestCases, importCases } from '@/api/requirement'
import type {
  AIGenerateResult, AIGeneratedCase, FeatureExtractionResult, RequirementAnalysis, TestModule,
} from '@/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Search, CheckCircle2, Info, Import, Loader2, FileText, Edit,
  Layers, ChevronDown, ChevronRight, AlertTriangle, RefreshCw,
  Monitor, Smartphone, Globe,
} from '@/lib/icons'

interface Props {
  open: boolean
  result: AIGenerateResult | null
  extractionResult: FeatureExtractionResult | null
  documentId: number | null
  mode?: 'generate' | 'view' | 'extract'
  onClose: () => void
  onImportSuccess: () => void
  onExtractionConfirmAndGenerate: (aiResult: AIGenerateResult) => void
  onExtractionReject: () => void
}

const PRIORITY_CLASSES: Record<string, string> = {
  P0: 'border-red-200 bg-red-50 text-red-700',
  P1: 'border-orange-200 bg-orange-50 text-orange-700',
  P2: 'border-blue-200 bg-blue-50 text-blue-700',
  P3: 'border-gray-200 bg-gray-50 text-gray-500',
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

// ── Client scope display helpers ──

const CLIENT_SCOPE_CONFIG: Record<string, { icon: typeof Monitor; label: string; className: string }> = {
  app: { icon: Smartphone, label: 'App', className: 'border-green-200 bg-green-50 text-green-700' },
  pc: { icon: Monitor, label: 'PC', className: 'border-blue-200 bg-blue-50 text-blue-700' },
  web: { icon: Globe, label: 'Web', className: 'border-purple-200 bg-purple-50 text-purple-700' },
}

function ClientScopeBadges({ clients }: { clients: string[] }) {
  if (!clients || clients.length === 0) return null
  return (
    <span className="inline-flex gap-0.5 ml-1 align-middle">
      {clients.map((c) => {
        const cfg = CLIENT_SCOPE_CONFIG[c]
        if (!cfg) return null
        const Icon = cfg.icon
        return (
          <Badge key={c} variant="outline" className={`text-[10px] leading-[16px] px-1 gap-0.5 ${cfg.className}`} title={cfg.label + '端'}>
            <Icon className="size-3" />
            {cfg.label}
          </Badge>
        )
      })}
    </span>
  )
}

/** VersionMarkerBadge — shows version origin for function points (batch-28). */
function VersionMarkerBadge({ fp, diffStatus, baseVersion }: {
  fp: { _inherited?: boolean; _from_version?: string }
  diffStatus?: string
  baseVersion?: string
}) {
  if (fp._inherited) {
    return (
      <Badge variant="outline" className="text-[10px] text-blue-600 border-blue-300">
        ➡️ 沿用自 {fp._from_version || baseVersion || '?'}
      </Badge>
    )
  }
  if (diffStatus === 'update') {
    return (
      <Badge variant="outline" className="text-[10px] text-orange-600 border-orange-300">
        ✏️ 本版本变更
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="text-[10px] text-green-600 border-green-300">
      🆕 首次提取
    </Badge>
  )
}

function renderSteps(steps: string) {
  try {
    const arr = JSON.parse(steps)
    if (!Array.isArray(arr) || arr.length === 0) return <span className="text-muted-foreground text-xs">-</span>
    return (
      <ol className="m-0 pl-[18px] max-w-[230px] break-words">
        {arr.map((s: any, i: number) => (
          <li key={i} className="text-xs leading-[18px] break-words">
            <span className="text-foreground">{s.desc}</span>
            {s.expected && <span className="text-green-600 ml-1">→ {s.expected}</span>}
          </li>
        ))}
      </ol>
    )
  } catch {
    return <span className="text-xs max-w-[230px] inline-block break-words">{steps}</span>
  }
}

function AnalysisPanel({ analysis }: { analysis: RequirementAnalysis }) {
  const { extracted_requirements, overall_assessment } = analysis
  const totalIssues = extracted_requirements.reduce((sum, er) => sum + (er.issues?.length || 0), 0)
  const highIssues = extracted_requirements.reduce(
    (sum, er) => sum + (er.issues || []).filter((i) => i.severity === 'high').length, 0,
  )
  const typeLabels: Record<string, string> = { functional: '功能', ui: '界面', data: '数据', integration: '集成' }

  return (
    <div className="max-h-[60vh] overflow-auto px-1">
      {overall_assessment && (
        <Alert className="mb-4">
          <Info className="size-4" />
          <AlertTitle>整体评估</AlertTitle>
          <AlertDescription>{overall_assessment}</AlertDescription>
        </Alert>
      )}

      {extracted_requirements.map((er) => {
        const issueCount = er.issues?.length || 0
        const hasHighIssue = er.issues?.some((i) => i.severity === 'high')
        const hasMediumIssue = er.issues?.some((i) => i.severity === 'medium')
        const issueBadgeClass = hasHighIssue
          ? 'border-red-200 bg-red-50 text-red-700'
          : hasMediumIssue
            ? 'border-orange-200 bg-orange-50 text-orange-700'
            : 'border-blue-200 bg-blue-50 text-blue-700'

        return (
          <Card key={er.id} size="sm" className="mb-3">
            <CardContent className="pt-3">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <Badge variant="outline" className="border-purple-200 bg-purple-50 text-purple-700">
                  {er.id}
                </Badge>
                <span className="font-medium text-sm">{er.title}</span>
                <Badge variant="secondary">{typeLabels[er.type] || er.type}</Badge>
                {issueCount > 0 && (
                  <Badge variant="outline" className={issueBadgeClass}>
                    {issueCount} 问题
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground mb-3">{er.description}</p>

              {(er.issues || []).map((iss, idx) => (
                <div
                  key={idx}
                  style={{ borderLeft: `3px solid ${SEVERITY_CONFIG[iss.severity]?.color || '#d9d9d9'}` }}
                  className="p-1.5 pl-3 mb-2 bg-muted/50 rounded"
                >
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={SEVERITY_BADGE_CLASSES[iss.severity] || 'border-gray-200 bg-gray-50 text-gray-500'}
                    >
                      {SEVERITY_CONFIG[iss.severity]?.label || iss.severity}
                    </Badge>
                    <span className="text-sm">{iss.description}</span>
                  </div>
                  {iss.suggestion && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      建议：{iss.suggestion}
                    </p>
                  )}
                </div>
              ))}

              {issueCount === 0 && (
                <span className="text-xs text-green-600">✓ 无明显问题</span>
              )}
            </CardContent>
          </Card>
        )
      })}

      {extracted_requirements.length === 0 && (
        <div className="text-center py-5 text-muted-foreground">未提取到需求功能点</div>
      )}
    </div>
  )
}

// ── Inline edit form for functional cases (no API fields) ──

function InlineEditRow({
  initial,
  onSave,
  onCancel,
}: {
  initial: AIGeneratedCase
  onSave: (updated: AIGeneratedCase) => void
  onCancel: () => void
}) {
  const [title, setTitle] = useState(initial.title || '')
  const [priority, setPriority] = useState(initial.priority || 'P2')
  const [module, setModule] = useState(initial.module || '')
  const [preconditions, setPreconditions] = useState(initial.preconditions || '')
  const [steps, setSteps] = useState(() => {
    try { return JSON.stringify(JSON.parse(initial.steps), null, 2) } catch { return initial.steps || '' }
  })
  const [expectedResult, setExpectedResult] = useState(initial.expected_result || '')
  const [remark, setRemark] = useState(initial.remark || '')

  const handleSave = () => {
    const t = title.trim()
    if (!t) { toast.warning('请输入用例标题'); return }
    let s = steps.trim()
    if (s) { try { JSON.parse(s) } catch { toast.warning('步骤需为有效 JSON 格式'); return } }
    onSave({
      ...initial,
      title: t,
      priority,
      module: module.trim(),
      preconditions: preconditions.trim(),
      steps: s,
      expected_result: expectedResult.trim(),
      remark: remark.trim(),
    })
  }

  return (
    <TableRow className="bg-amber-50/30 border-amber-200">
      <TableCell colSpan={9} className="p-0">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4">
          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs font-medium">用例标题 *</label>
            <Input placeholder="用例标题" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium">重要程度</label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger size="sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                {['P0', 'P1', 'P2', 'P3'].map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium">所属模块</label>
            <Input placeholder="模块名" value={module} onChange={(e) => setModule(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium">备注</label>
            <Input placeholder="备注信息" value={remark} onChange={(e) => setRemark(e.target.value)} />
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs font-medium">前置条件</label>
            <Textarea rows={2} placeholder="执行用例前需要满足的条件" value={preconditions} onChange={(e) => setPreconditions(e.target.value)} />
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs font-medium">测试步骤 (JSON)</label>
            <Textarea
              rows={4}
              placeholder='[{"desc":"操作描述","expected":"预期结果"}]'
              value={steps}
              onChange={(e) => setSteps(e.target.value)}
              className="font-mono text-xs"
            />
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs font-medium">预期结果</label>
            <Textarea rows={2} placeholder="整体预期结果描述" value={expectedResult} onChange={(e) => setExpectedResult(e.target.value)} />
          </div>
          <div className="sm:col-span-2 lg:col-span-3 flex items-center gap-2 pt-1">
            <Button size="sm" onClick={handleSave}>保存</Button>
            <Button size="sm" variant="outline" onClick={onCancel}>取消</Button>
          </div>
        </div>
      </TableCell>
    </TableRow>
  )
}

// ── Main component ──

export default function AiResultModal({
  open, result, extractionResult, documentId, mode = 'generate', onClose,
  onImportSuccess, onExtractionConfirmAndGenerate, onExtractionReject,
}: Props) {
  const [importing, setImporting] = useState(false)
  const [selectedFuncKeys, setSelectedFuncKeys] = useState<number[]>([])

  // Inline edit state
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editedCases, setEditedCases] = useState<Map<number, AIGeneratedCase>>(new Map())

  // ── Extraction review state ──
  const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set())
  const [selectedModules, setSelectedModules] = useState<Set<string>>(new Set())
  const [rejectMode, setRejectMode] = useState(false)
  const [rejectNotes, setRejectNotes] = useState('')
  const [generating, setGenerating] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [activeTab, setActiveTab] = useState('func')

  // Initialize extraction state when extractionResult changes
  useEffect(() => {
    if (extractionResult?.modules) {
      const ids = extractionResult.modules.map((m) => m.id)
      setSelectedModules(new Set(ids))
      setExpandedModules(new Set(ids.slice(0, 2)))
      setRejectMode(false)
      setRejectNotes('')
    }
  }, [extractionResult])

  const funcCases = result?.functional_cases || []
  const isViewMode = mode === 'view'
  const isExtractMode = mode === 'extract'
  const analysis = result?.requirement_analysis
  const hasAnalysis = analysis && analysis.extracted_requirements && analysis.extracted_requirements.length > 0
  const hasExtraction = extractionResult && extractionResult.modules && extractionResult.modules.length > 0

  const extractionModules = extractionResult?.modules || []
  const totalFps = extractionModules.reduce((sum, m) => sum + (m.function_points?.length || 0), 0)
  const extractionTotalIssues = extractionModules.reduce(
    (sum, m) =>
      sum + (m.function_points || []).reduce((s, fp) => s + (fp.issues?.length || 0), 0),
    0,
  )

  // Client scope summary
  const clientSummary = extractionResult?.client_summary || ''
  const versionInfo = extractionResult?.version_info || []

  // Default to first available tab
  useEffect(() => {
    if (hasExtraction && isExtractMode) setActiveTab('extraction')
    else if (hasAnalysis) setActiveTab('analysis')
    else if (funcCases.length > 0) setActiveTab('func')
  }, [hasExtraction, isExtractMode, hasAnalysis, funcCases.length])

  // Reset when result or extractionResult changes
  useEffect(() => {
    setEditedCases(new Map())
    setEditingIndex(null)
  }, [result])

  if (!result && !hasExtraction) return null

  const getDisplayCase = (c: AIGeneratedCase): AIGeneratedCase =>
    editedCases.get(c.index) || c

  const isCaseEdited = (c: AIGeneratedCase): boolean =>
    editedCases.has(c.index)

  const totalIssues = hasAnalysis
    ? analysis!.extracted_requirements.reduce((sum, er) => sum + (er.issues?.length || 0), 0)
    : 0
  const highIssueCount = hasAnalysis
    ? analysis!.extracted_requirements.reduce((sum, er) => sum + (er.issues || []).filter((i) => i.severity === 'high').length, 0)
    : 0

  const editedCount = editedCases.size

  const doImport = async (indices: number[]) => {
    if (indices.length === 0) {
      toast.warning('请至少选择一条用例')
      return
    }
    if (documentId == null) return
    setImporting(true)
    try {
      const res = await importCases(documentId, indices)
      toast.success(`成功导入 ${res.imported} 条功能用例` + (res.skipped > 0 ? `，${res.skipped} 条跳过` : ''))
      setSelectedFuncKeys([])
      setEditedCases(new Map())
      onImportSuccess()
    } catch {
      toast.error('导入失败，请重试')
    } finally {
      setImporting(false)
    }
  }

  const handleClose = () => {
    setSelectedFuncKeys([])
    setEditedCases(new Map())
    setEditingIndex(null)
    onClose()
  }

  const toggleFuncAll = () => {
    if (selectedFuncKeys.length === funcCases.length) {
      setSelectedFuncKeys([])
    } else {
      setSelectedFuncKeys(funcCases.map((c) => c.index))
    }
  }

  const toggleFuncOne = (index: number) => {
    setSelectedFuncKeys((prev) =>
      prev.includes(index) ? prev.filter((k) => k !== index) : [...prev, index],
    )
  }

  const handleStartEdit = (c: AIGeneratedCase) => {
    setEditingIndex(c.index)
  }

  const handleSaveEdit = (updated: AIGeneratedCase) => {
    setEditedCases((prev) => {
      const next = new Map(prev)
      next.set(updated.index, updated)
      return next
    })
    setEditingIndex(null)
    toast.success(`用例 #${updated.index} 已更新`)
  }

  // ── Extraction handlers ──

  const toggleModuleExpand = (id: string) => {
    setExpandedModules((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleModuleSelect = (id: string) => {
    setSelectedModules((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleExtractionConfirmAndGenerate = async () => {
    if (selectedModules.size === 0) {
      toast.error('请至少选择一个模块')
      return
    }
    if (documentId == null) return

    const confirmedModules: TestModule[] = extractionModules.filter((m) => selectedModules.has(m.id))

    setSubmitting(true)
    try {
      await confirmExtraction(documentId, {
        action: 'confirm',
        modules: confirmedModules,
      })
      toast.success('功能拆分已确认，正在生成用例...')

      setGenerating(true)
      try {
        const aiResult = await generateTestCases(documentId, { use_extraction: true })
        toast.success(`用例生成完成：${aiResult.functional_cases.length} 条功能用例`)
        onExtractionConfirmAndGenerate(aiResult)
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

  const handleExtractionReject = async () => {
    if (documentId == null) return
    setSubmitting(true)
    try {
      const rejectedModuleIds = extractionModules
        .filter((m) => !selectedModules.has(m.id))
        .map((m) => m.id)

      await confirmExtraction(documentId, {
        action: 'reject',
        rejected_modules: rejectedModuleIds,
        rejected_notes: rejectNotes,
      })
      toast.success('已标记需重新提取，可以重新进行功能拆分')
      onExtractionReject()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '操作失败'
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const hasContent = hasAnalysis || funcCases.length > 0 || hasExtraction

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleClose() }}>
      <DialogContent
        className="max-w-[95vw] lg:max-w-[1280px]"
        showCloseButton={false}
        onInteractOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 flex-wrap">
            {isExtractMode ? (
              <>
                <Layers className="size-5 text-primary" />
                功能拆分 — 共 {extractionModules.length} 个模块, {totalFps} 个功能点
                {clientSummary && (
                  <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700 text-xs">
                    {clientSummary}
                  </Badge>
                )}
              </>
            ) : (
              <>
                <Import className="size-5" />
                AI 生成功能测试用例
                <span className="text-xs text-muted-foreground font-normal">
                  共 <span className="text-blue-600 font-medium">{funcCases.length} 条功能用例</span>
                </span>
                {editedCount > 0 && (
                  <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">
                    已修改 {editedCount} 条
                  </Badge>
                )}
              </>
            )}
          </DialogTitle>
        </DialogHeader>

        {/* Extraction + changelog summary */}
        {(result?.extraction_summary || extractionResult?.extraction_summary) && (
          <Alert className="mb-2 border-purple-200 bg-purple-50">
            <Info className="size-4 text-purple-600" />
            <AlertTitle className="text-purple-800 text-sm">蓝湖提取状态</AlertTitle>
            <AlertDescription className="text-purple-700 text-xs">
              {result?.extraction_summary || extractionResult?.extraction_summary}
            </AlertDescription>
          </Alert>
        )}

        {/* Client scope summary banner */}
        {(clientSummary || versionInfo.length > 0) && (
          <Alert className="mb-2 border-blue-200 bg-blue-50">
            <Monitor className="size-4 text-blue-600" />
            <AlertTitle className="text-blue-800 text-sm">
              多端检测
              {clientSummary && <span> — {clientSummary}</span>}
            </AlertTitle>
            {versionInfo.length > 0 && (
              <AlertDescription className="text-blue-700 text-xs mt-1">
                {versionInfo.map((v, i) => (
                  <span key={i} className="mr-3">
                    {v.title || v.version}
                    {v.clients.length > 0 && <span> [{v.clients.join('/')}]</span>}
                  </span>
                ))}
              </AlertDescription>
            )}
          </Alert>
        )}

        {/* Extraction overall assessment */}
        {isExtractMode && extractionResult?.overall_assessment && (
          <Alert className="shrink-0 mb-2">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-sm">{extractionResult.overall_assessment}</AlertDescription>
          </Alert>
        )}

        {hasContent ? (
          <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); setEditingIndex(null) }}>
            <TabsList className="mb-3">
              {/* Extraction review tab */}
              {hasExtraction && (
                <TabsTrigger value="extraction" className="gap-1.5">
                  <Layers className="size-3.5 text-primary" />
                  测试点 ({extractionModules.length} 模块{totalFps > 0 ? ` · ${totalFps} 功能点` : ''})
                  {extractionTotalIssues > 0 && (
                    <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700 text-[10px] leading-[16px] ml-1">
                      {extractionTotalIssues} 问题
                    </Badge>
                  )}
                </TabsTrigger>
              )}
              {hasAnalysis && (
                <TabsTrigger value="analysis" className="gap-1.5">
                  <Search className="size-3.5 text-purple-600" />
                  需求分析 ({analysis!.extracted_requirements.length} 功能点{totalIssues > 0 ? ` · ${totalIssues} 问题` : ''})
                  {highIssueCount > 0 && (
                    <Badge variant="outline" className="border-red-200 bg-red-50 text-red-700 text-[10px] leading-[16px] ml-1">
                      {highIssueCount} 高
                    </Badge>
                  )}
                </TabsTrigger>
              )}
              {funcCases.length > 0 && (
                <TabsTrigger value="func" className="gap-1.5">
                  <CheckCircle2 className="size-3.5 text-blue-600" />
                  功能用例 ({funcCases.length})
                </TabsTrigger>
              )}
            </TabsList>

            {/* ── Tab: 测试点（功能拆分审核） ── */}
            {hasExtraction && (
              <TabsContent value="extraction" className="mt-0">
                <div className="flex-1 overflow-y-auto space-y-3 pr-1 max-h-[55vh]">
                  {extractionModules.map((mod) => {
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
                            onCheckedChange={() => toggleModuleSelect(mod.id)}
                          />
                          <button
                            className="flex-1 flex items-center gap-2 text-left hover:opacity-80"
                            onClick={() => toggleModuleExpand(mod.id)}
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

                        {/* Module description + function points */}
                        {isExpanded && (
                          <CardContent className="pb-3 pt-0">
                            {mod.description && (
                              <p className="text-sm text-muted-foreground mb-3">{mod.description}</p>
                            )}

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
                                    <Badge variant="secondary" className="text-xs">
                                      {TYPE_LABELS[fp.type] || fp.type}
                                    </Badge>
                                    <ClientScopeBadges clients={fp.client_scope} />
                                    <VersionMarkerBadge
                                      fp={fp as any}
                                      diffStatus={extractionResult?.diff_summary ? 'update' : undefined}
                                      baseVersion={extractionResult?.inherited_from_version}
                                    />
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
              </TabsContent>
            )}

            {/* ── Tab: 需求分析 ── */}
            {hasAnalysis && (
              <TabsContent value="analysis" className="mt-0">
                <AnalysisPanel analysis={analysis!} />
              </TabsContent>
            )}

            {/* ── Tab: 功能用例 ── */}
            {funcCases.length > 0 && (
              <TabsContent value="func" className="mt-0">
                <div className="max-h-[55vh] overflow-auto border rounded-lg">
                  <Table className="min-w-[1200px]">
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-10">
                          <Checkbox
                            checked={selectedFuncKeys.length === funcCases.length && funcCases.length > 0}
                            onCheckedChange={toggleFuncAll}
                          />
                        </TableHead>
                        <TableHead className="w-[210px]">用例标题</TableHead>
                        <TableHead className="w-[80px] text-center">重要程度</TableHead>
                        <TableHead className="w-[110px]">模块</TableHead>
                        <TableHead className="w-[70px] text-center">适用端</TableHead>
                        <TableHead className="w-[150px]">前提条件</TableHead>
                        <TableHead className="w-[240px]">操作步骤</TableHead>
                        <TableHead className="w-[210px]">预期结果</TableHead>
                        <TableHead className="w-[110px]">备注</TableHead>
                        <TableHead className="w-[60px] text-center">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {funcCases.map((c) => {
                        const display = getDisplayCase(c)
                        const edited = isCaseEdited(c)
                        const isEditing = editingIndex === c.index

                        if (isEditing) {
                          return (
                            <InlineEditRow
                              key={c.index}
                              initial={display}
                              onSave={handleSaveEdit}
                              onCancel={() => setEditingIndex(null)}
                            />
                          )
                        }

                        return (
                          <TableRow key={c.index} className={edited ? 'bg-amber-50/50' : undefined}>
                            <TableCell>
                              <Checkbox
                                checked={selectedFuncKeys.includes(c.index)}
                                onCheckedChange={() => toggleFuncOne(c.index)}
                              />
                            </TableCell>
                            <TableCell className="font-medium align-top whitespace-normal">
                              <div className="break-words max-w-[200px]">
                                {edited && <span className="text-amber-600 mr-1" title="已修改">*</span>}
                                {display.title}
                                {display.imported && (
                                  <Badge variant="outline" className="ml-1.5 border-green-200 bg-green-50 text-green-700 text-[10px] leading-[16px]">
                                    已导入
                                  </Badge>
                                )}
                              </div>
                            </TableCell>
                            <TableCell className="text-center">
                              <Badge variant="outline" className={PRIORITY_CLASSES[display.priority] || 'border-gray-200 bg-gray-50 text-gray-500'}>
                                {display.priority}
                              </Badge>
                            </TableCell>
                            <TableCell className="break-words max-w-[100px] text-xs align-top whitespace-normal">{display.module || '-'}</TableCell>
                            <TableCell className="text-center align-top">
                              <ClientScopeBadges clients={display.client_scope || []} />
                            </TableCell>
                            <TableCell className="break-words max-w-[140px] text-xs align-top whitespace-normal">{display.preconditions || '-'}</TableCell>
                            <TableCell className="whitespace-normal">{renderSteps(display.steps)}</TableCell>
                            <TableCell className="break-words max-w-[200px] text-xs align-top whitespace-normal">{display.expected_result || '-'}</TableCell>
                            <TableCell className="break-words max-w-[100px] text-xs text-muted-foreground align-top whitespace-normal">{display.remark || '-'}</TableCell>
                            <TableCell className="text-center">
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                title={edited ? '再次编辑' : '编辑用例'}
                                onClick={() => handleStartEdit(c)}
                              >
                                <Edit className="size-3.5" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <span className="text-xs text-muted-foreground">
                    已选 {selectedFuncKeys.length}/{funcCases.length} 条
                    {funcCases.filter((c) => c.imported).length > 0 && (
                      <span className="text-green-600 ml-2">
                        · 已导入 {funcCases.filter((c) => c.imported).length} 条
                      </span>
                    )}
                  </span>
                  <Button
                    size="sm"
                    onClick={() => doImport(selectedFuncKeys)}
                    disabled={importing || selectedFuncKeys.length === 0}
                  >
                    {importing ? <Loader2 className="size-3.5 animate-spin" /> : <Import className="size-3.5" />}
                    导入功能用例 ({selectedFuncKeys.length})
                  </Button>
                </div>
              </TabsContent>
            )}
          </Tabs>
        ) : (
          <div className="text-center py-10 text-muted-foreground">
            <FileText className="size-8 mx-auto mb-2 opacity-40" />
            AI 未生成任何用例，请检查需求文档内容
          </div>
        )}

        <DialogFooter className="shrink-0 flex-col gap-2 sm:flex-row sm:justify-between pt-2 border-t">
          {isExtractMode && rejectMode && (
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
            {isExtractMode ? (
              !rejectMode ? (
                <>
                  <Button variant="ghost" onClick={handleClose} disabled={submitting}>
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
                    onClick={handleExtractionConfirmAndGenerate}
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
                    onClick={handleExtractionReject}
                    disabled={submitting || !rejectNotes.trim()}
                  >
                    {submitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                    确认拒绝，重新提取
                  </Button>
                </>
              )
            ) : (
              <Button variant="outline" onClick={handleClose}>
                关闭
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
