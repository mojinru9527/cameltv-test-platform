import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import {
  confirmApiMatches,
  generateApiFromEndpoints,
  confirmExtraction,
  fetchApiMatchSelection,
  generateTestCases,
  importCases,
  matchApiEndpoints,
  reviewCase,
} from '@/api/requirement'
import { fetchApiServices } from '@/api/apitest'
import type {
  AIGenerateResult, AIGeneratedCase, FeatureExtractionResult, RequirementAnalysis,
  TestModule, ApiMatchItem, ApiService,
} from '@/types'
import { Badge, Button } from '@/ui'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Search, CheckCircle2, Info, Import, Loader2, FileText,
  Layers, AlertTriangle, RefreshCw,
  Monitor, Server, Zap, BarChart3,
} from '@/lib/icons'
import AiAnalysisPanel from './components/AiAnalysisPanel'
import AiExtractionPanel from './components/AiExtractionPanel'
import AiFuncCasesPanel from './components/AiFuncCasesPanel'
import AiApiCasesPanel from './components/AiApiCasesPanel'
import AiRegressionPanel from './components/AiRegressionPanel'
import AiCoveragePanel from './components/AiCoveragePanel'

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

export default function AiResultModal({
  open, result, extractionResult, documentId, mode = 'generate', onClose,
  onImportSuccess, onExtractionConfirmAndGenerate, onExtractionReject,
}: Props) {
  const [importing, setImporting] = useState(false)
  const [createPlan, setCreatePlan] = useState(false)
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

  // ── API matching & regression state (batch-34) ──
  const [apiMatches, setApiMatches] = useState<ApiMatchItem[]>([])
  const [loadingMatches, setLoadingMatches] = useState(false)
  const [selectedApiKeys, setSelectedApiKeys] = useState<number[]>([])
  const [apiServices, setApiServices] = useState<ApiService[]>([])
  const [selectedServiceId, setSelectedServiceId] = useState<number | null>(null)
  const [confirmedEndpointIds, setConfirmedEndpointIds] = useState<Set<number>>(new Set())
  const [savingMatches, setSavingMatches] = useState(false)
  const [generatingApiFromEndpoints, setGeneratingApiFromEndpoints] = useState(false)

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
  const apiCases = useMemo(() => result?.api_cases || [], [result?.api_cases])

  // ── Fetch API matches when modal opens with result ──
  useEffect(() => {
    if (open && documentId && apiCases.length > 0) {
      const controller = new AbortController()
      setLoadingMatches(true)
      const integrationReqs = apiCases.map((c: any) => ({
        id: c.id || c.title || '',
        title: c.title || '',
        description: c.expected_result || c.api_endpoint || '',
      }))
      Promise.all([
        fetchApiServices(),
        fetchApiMatchSelection(documentId, controller.signal),
      ])
        .then(async ([services, selection]) => {
          if (controller.signal.aborted) return
          setApiServices(services || [])
          setSelectedServiceId(selection.service_id)
          setConfirmedEndpointIds(new Set(selection.endpoint_ids || []))
          const matches = await matchApiEndpoints(
            documentId,
            integrationReqs,
            selection.service_id ?? undefined,
            controller.signal,
          )
          if (!controller.signal.aborted) setApiMatches(matches || [])
        })
        .catch(() => {
          if (!controller.signal.aborted) setApiMatches([])
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoadingMatches(false)
        })
      return () => controller.abort()
    } else {
      setApiMatches([])
      setApiServices([])
      setSelectedServiceId(null)
      setConfirmedEndpointIds(new Set())
    }
  }, [open, documentId, apiCases])
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
    setSelectedApiKeys([])
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
    if (editingIndex !== null) {
      toast.warning('请先保存或取消正在编辑的用例')
      return
    }
    if (documentId == null) return
    setImporting(true)
    try {
      const finalEdits = indices
        .map((index) => editedCases.get(index))
        .filter((item): item is AIGeneratedCase => item != null)
      const res = await importCases(documentId, indices, finalEdits, createPlan, createPlan)
      let msg = `成功导入 ${res.imported} 条功能用例` + (res.skipped > 0 ? `，${res.skipped} 条跳过` : '')
      if (res.plan_id) {
        msg += ` → 已创建计划「${res.plan_name}」`
      }
      toast.success(msg)
      setSelectedFuncKeys([])
      setEditedCases(new Map())
      setCreatePlan(false)
      onImportSuccess()
    } catch {
      toast.error('导入失败，请重试')
    } finally {
      setImporting(false)
    }
  }

  const handleClose = () => {
    setSelectedFuncKeys([])
    setSelectedApiKeys([])
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

  const toggleApiAll = () => {
    if (selectedApiKeys.length === apiCases.length) {
      setSelectedApiKeys([])
    } else {
      setSelectedApiKeys(apiCases.map((c) => c.index))
    }
  }

  const handleStartEdit = (c: AIGeneratedCase) => {
    setEditingIndex(c.index)
  }

  const handleSaveEdit = async (updated: AIGeneratedCase): Promise<boolean> => {
    if (documentId == null) return false
    try {
      await reviewCase(documentId, updated.index, 'edit', updated)
      setEditedCases((prev) => {
        const next = new Map(prev)
        next.set(updated.index, updated)
        return next
      })
      setEditingIndex(null)
      toast.success(`用例 #${updated.index} 已保存`)
      return true
    } catch {
      toast.error('保存编辑失败，未导入任何旧数据')
      return false
    }
  }

  const handleServiceChange = async (value: string) => {
    if (documentId == null) return
    const serviceId = Number(value)
    setSelectedServiceId(serviceId)
    setConfirmedEndpointIds(new Set())
    setLoadingMatches(true)
    try {
      const integrationReqs = apiCases.map((c: any) => ({
        id: c.id || c.title || '',
        title: c.title || '',
        description: c.expected_result || c.api_endpoint || '',
      }))
      const matches = await matchApiEndpoints(documentId, integrationReqs, serviceId)
      setApiMatches(matches || [])
    } catch {
      setApiMatches([])
      toast.error('API 端点匹配失败')
    } finally {
      setLoadingMatches(false)
    }
  }

  const toggleMatchedEndpoint = (endpointId: number) => {
    setConfirmedEndpointIds((previous) => {
      const next = new Set(previous)
      if (next.has(endpointId)) next.delete(endpointId)
      else next.add(endpointId)
      return next
    })
  }


  const handleGenerateApiFromEndpoints = async () => {
    if (documentId == null) return
    setGeneratingApiFromEndpoints(true)
    try {
      const result = await generateApiFromEndpoints(documentId, selectedServiceId ?? undefined)
      toast.success(`已按已导入接口生成 ${result.generated} 条接口用例（匹配 ${result.matched} 个端点）`)
    } catch {
      toast.error('生成真实接口用例失败，请先在接口测试导入 OpenAPI/Swagger')
    } finally {
      setGeneratingApiFromEndpoints(false)
    }
  }

  const handleConfirmMatches = async () => {
    if (documentId == null || selectedServiceId == null) {
      toast.warning('请先选择 API 服务')
      return
    }
    setSavingMatches(true)
    try {
      const selection = await confirmApiMatches(documentId, {
        service_id: selectedServiceId,
        endpoint_ids: Array.from(confirmedEndpointIds),
      })
      setConfirmedEndpointIds(new Set(selection.endpoint_ids || []))
      toast.success('API 匹配已确认并保存')
    } catch {
      toast.error('保存 API 匹配失败')
    } finally {
      setSavingMatches(false)
    }
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
  const coverageReport = result?.coverage_report ?? null
  const hasCoverage = !!coverageReport

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
                  <Badge tone="neutral" className="border-status-info-border bg-status-info-muted text-status-info text-xs">
                    {clientSummary}
                  </Badge>
                )}
              </>
            ) : (
              <>
                <Import className="size-5" />
                AI 生成功能测试用例
                <span className="text-xs text-muted-foreground font-normal">
                  共 <span className="text-status-info font-medium">{funcCases.length} 条功能用例</span>
                </span>
                {editedCount > 0 && (
                  <Badge tone="neutral" className="border-status-warning-border bg-status-warning-muted text-status-warning">
                    已修改 {editedCount} 条
                  </Badge>
                )}
              </>
            )}
          </DialogTitle>
        </DialogHeader>

        {/* Extraction + changelog summary */}
        {(result?.extraction_summary || extractionResult?.extraction_summary) && (
          <Alert className="mb-2 border-status-accent-border bg-status-accent-muted">
            <Info className="size-4 text-status-accent" />
            <AlertTitle className="text-status-accent text-sm">蓝湖提取状态</AlertTitle>
            <AlertDescription className="text-status-accent text-xs">
              {result?.extraction_summary || extractionResult?.extraction_summary}
            </AlertDescription>
          </Alert>
        )}

        {/* Client scope summary banner */}
        {(clientSummary || versionInfo.length > 0) && (
          <Alert className="mb-2 border-status-info-border bg-status-info-muted">
            <Monitor className="size-4 text-status-info" />
            <AlertTitle className="text-status-info text-sm">
              多端检测
              {clientSummary && <span> — {clientSummary}</span>}
            </AlertTitle>
            {versionInfo.length > 0 && (
              <AlertDescription className="text-status-info text-xs mt-1">
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
                    <Badge tone="neutral" className="border-status-warning-border bg-status-warning-muted text-status-warning text-xs leading-[16px] ml-1">
                      {extractionTotalIssues} 问题
                    </Badge>
                  )}
                </TabsTrigger>
              )}
              {hasAnalysis && (
                <TabsTrigger value="analysis" className="gap-1.5">
                  <Search className="size-3.5 text-status-accent" />
                  需求分析 ({analysis!.extracted_requirements.length} 功能点{totalIssues > 0 ? ` · ${totalIssues} 问题` : ''})
                  {highIssueCount > 0 && (
                    <Badge tone="neutral" className="border-status-danger-border bg-status-danger-muted text-status-danger text-xs leading-[16px] ml-1">
                      {highIssueCount} 高
                    </Badge>
                  )}
                </TabsTrigger>
              )}
              {funcCases.length > 0 && (
                <TabsTrigger value="func" className="gap-1.5">
                  <CheckCircle2 className="size-3.5 text-status-info" />
                  功能用例 ({funcCases.length})
                </TabsTrigger>
              )}
              {apiCases.length > 0 && (
                <TabsTrigger value="api" className="gap-1.5">
                  <Server className="size-3.5 text-status-success" />
                  接口用例 ({apiCases.length})
                  {apiMatches.length > 0 && (
                    <Badge tone="neutral" className="border-status-success-border bg-status-success-muted text-status-success text-xs leading-[16px] ml-1">
                      +{apiMatches.length} 匹配
                    </Badge>
                  )}
                </TabsTrigger>
              )}
              {hasExtraction && extractionModules.some((m) => m.function_points?.some((fp) => fp.type === 'integration')) && (
                <TabsTrigger value="regression" className="gap-1.5">
                  <Zap className="size-3.5 text-status-warning" />
                  UI回归建议
                </TabsTrigger>
              )}
              {hasCoverage && (
                <TabsTrigger value="coverage" className="gap-1.5">
                  <BarChart3 className="size-3.5 text-status-info" />
                  覆盖矩阵
                  {coverageReport && coverageReport.gap_count > 0 && (
                    <Badge tone="neutral" className="border-status-warning-border bg-status-warning-muted text-status-warning text-xs leading-[16px] ml-1">
                      {coverageReport.gap_count} 缺口
                    </Badge>
                  )}
                </TabsTrigger>
              )}
            </TabsList>

            {/* ── Tab: 测试点（功能拆分审核） ── */}
            {hasExtraction && (
              <TabsContent value="extraction" className="mt-0">
                <AiExtractionPanel
                  extractionModules={extractionModules}
                  expandedModules={expandedModules}
                  selectedModules={selectedModules}
                  extractionResult={extractionResult}
                  onToggleExpand={toggleModuleExpand}
                  onToggleSelect={toggleModuleSelect}
                />
              </TabsContent>
            )}

            {/* ── Tab: 需求分析 ── */}
            {hasAnalysis && (
              <TabsContent value="analysis" className="mt-0">
                <AiAnalysisPanel analysis={analysis!} />
              </TabsContent>
            )}

            {/* ── Tab: 功能用例 ── */}
            {funcCases.length > 0 && (
              <TabsContent value="func" className="mt-0">
                <AiFuncCasesPanel
                  funcCases={funcCases}
                  selectedKeys={selectedFuncKeys}
                  editingIndex={editingIndex}
                  importing={importing}
                  createPlan={createPlan}
                  getDisplayCase={getDisplayCase}
                  isCaseEdited={isCaseEdited}
                  onToggleAll={toggleFuncAll}
                  onToggleOne={toggleFuncOne}
                  onStartEdit={handleStartEdit}
                  onSaveEdit={handleSaveEdit}
                  onCancelEdit={() => setEditingIndex(null)}
                  onCreatePlanChange={(v) => setCreatePlan(v)}
                  onImport={doImport}
                />
              </TabsContent>
            )}
            {/* ── Tab: 接口用例 ── */}
            {apiCases.length > 0 && (
              <TabsContent value="api" className="mt-0">
                <AiApiCasesPanel
                  apiCases={apiCases}
                  selectedKeys={selectedApiKeys}
                  apiServices={apiServices}
                  apiMatches={apiMatches}
                  confirmedEndpointIds={confirmedEndpointIds}
                  selectedServiceId={selectedServiceId}
                  loadingMatches={loadingMatches}
                  savingMatches={savingMatches}
                  generatingApiFromEndpoints={generatingApiFromEndpoints}
                  importing={importing}
                  getDisplayCase={getDisplayCase}
                  onToggleAll={toggleApiAll}
                  onToggleOne={(index) => {
                    setSelectedApiKeys((prev) =>
                      prev.includes(index) ? prev.filter((k) => k !== index) : [...prev, index]
                    )
                  }}
                  onServiceChange={handleServiceChange}
                  onToggleEndpoint={toggleMatchedEndpoint}
                  onConfirmMatches={handleConfirmMatches}
                  onGenerateApiFromEndpoints={handleGenerateApiFromEndpoints}
                  onImport={doImport}
                />
              </TabsContent>
            )}

            {/* ── Tab: UI回归建议 ── */}
            {hasExtraction && extractionModules.some((m) => m.function_points?.some((fp) => fp.type === 'integration')) && (
              <TabsContent value="regression" className="mt-0">
                <AiRegressionPanel extractionModules={extractionModules} />
              </TabsContent>
            )}
            {hasCoverage && coverageReport && (
              <TabsContent value="coverage" className="mt-0">
                <AiCoveragePanel report={coverageReport} />
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
                    variant="secondary"
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
                    variant="danger"
                    onClick={handleExtractionReject}
                    disabled={submitting || !rejectNotes.trim()}
                  >
                    {submitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                    确认拒绝，重新提取
                  </Button>
                </>
              )
            ) : (
              <Button variant="secondary" onClick={handleClose}>
                关闭
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
