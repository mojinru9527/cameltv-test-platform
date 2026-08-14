import { Button, PageShell } from '@/ui'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth'
import { fetchDomains } from '@/api/testcase'
import {
  confirmExtraction, deleteRequirement, extractFeatures, extractFeaturesAsync, fetchGeneratedCases,
  fetchRequirement, fetchRequirementCoverage, fetchRequirements,
  generateTestCases, generateTestCasesAsync, runAsyncAiTask, getOrCreateExtraction, uploadRequirement,
} from '@/api/requirement'
import type {
  AIGenerateResult,
  FeatureExtractionResult,
  RequirementDocument,
  RequirementDocumentBrief,
  RequirementCoverage,
} from '@/types'
import { Input } from '@/ui'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Settings, RotateCcw, Loader2, Smartphone, Monitor } from '@/lib/icons'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import AiResultModal from './AiResultModal'
import EvidenceTaskPanel from './components/EvidenceTaskPanel'
import ProductionDiffPanel from './components/ProductionDiffPanel'
import InteractionGapPanel from './components/InteractionGapPanel'
import VersionCompare from './components/VersionCompare'
import PrototypePreview from './components/PrototypePreview'
import LanhuEvidenceDialog from '@/pages/knowledge/components/LanhuEvidenceDialog'
import LanhuEvidenceJobDrawer from '@/pages/knowledge/components/LanhuEvidenceJobDrawer'
import RequirementStatsRow from './components/RequirementStatsRow'
import RequirementUploadCard from './components/RequirementUploadCard'
import RequirementContentPreview from './components/RequirementContentPreview'
import RequirementDocTable from './components/RequirementDocTable'
import RequirementDomainCoverageTable from './components/RequirementDomainCoverageTable'

interface RequirementData {
  domains: any[]
}

export default function RequirementPage() {
  const hasPerm = useAuthStore((state) => state.hasPerm)
  const canWriteDocs = hasPerm('requirement:upload') || hasPerm('requirement:generate') || hasPerm('requirement:import')
  useDocumentTitle('需求文档')
  const [keyword, setKeyword] = useState('')
  const [uploading, setUploading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generatingDocId, setGeneratingDocId] = useState<number | null>(null)
  const [aiResult, setAiResult] = useState<AIGenerateResult | null>(null)
  const [showAiModal, setShowAiModal] = useState(false)
  const [modalMode, setModalMode] = useState<'generate' | 'view' | 'extract'>('generate')
  const [activeDocId, setActiveDocId] = useState<number | null>(null)
  const [lanhuUrl, setLanhuUrl] = useState('')
  const [evOpen, setEvOpen] = useState(false)
  const [evJobId, setEvJobId] = useState<number | null>(null)
  const [previewExpanded, setPreviewExpanded] = useState(false)
  const navigate = useNavigate()
  const [deleteTarget, setDeleteTarget] = useState<RequirementDocumentBrief | null>(null)
  const [docPage, setDocPage] = useState(1)
  const [domainPage, setDomainPage] = useState(1)
  const [debouncedKeyword, setDebouncedKeyword] = useState('')
  const [evidenceRefreshKey, setEvidenceRefreshKey] = useState(0)

  // ── Stage 1: Feature Extraction state ──
  const [extractionResult, setExtractionResult] = useState<FeatureExtractionResult | null>(null)
  const [extracting, setExtracting] = useState(false)
  const [extractingDocId, setExtractingDocId] = useState<number | null>(null)
  const [, setConfirmedExtractionIds] = useState<Set<number>>(new Set())
  // ── batch-28: version compare + screenshot preview states ──
  const [versionDiffData, setVersionDiffData] = useState<any>(null)
  const [showVersionCompare, setShowVersionCompare] = useState(false)
  const [screenshotPages, setScreenshotPages] = useState<any[]>([])
  const [showScreenshotPreview, setShowScreenshotPreview] = useState(false)
  const [screenshotVersion, setScreenshotVersion] = useState('')

  // ── Lanhu settings (batch-34) ──
  const [lanhuSettingsOpen, setLanhuSettingsOpen] = useState(false)
  const [lanhuUserProjectId, setLanhuUserProjectId] = useState(
    () => localStorage.getItem('lanhu_user_project_id') || ''
  )
  const [lanhuUserVersionId, setLanhuUserVersionId] = useState(
    () => localStorage.getItem('lanhu_user_version_id') || ''
  )
  const [lanhuAdminProjectId, setLanhuAdminProjectId] = useState(
    () => localStorage.getItem('lanhu_admin_project_id') || ''
  )
  const [lanhuAdminVersionId, setLanhuAdminVersionId] = useState(
    () => localStorage.getItem('lanhu_admin_version_id') || ''
  )

  const saveLanhuSettings = () => {
    localStorage.setItem('lanhu_user_project_id', lanhuUserProjectId)
    localStorage.setItem('lanhu_user_version_id', lanhuUserVersionId)
    localStorage.setItem('lanhu_admin_project_id', lanhuAdminProjectId)
    localStorage.setItem('lanhu_admin_version_id', lanhuAdminVersionId)
    toast.success('蓝湖配置已保存')
    setLanhuSettingsOpen(false)
  }

  const docPageSize = 20
  const domainPageSize = 20

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedKeyword(keyword.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [keyword])

  // Domain metadata is independent from the server-paginated document list.
  const {
    data: metadata,
    isLoading: isMetadataLoading,
    isRefetching: isMetadataRefetching,
    refetch: refetchMetadata,
  } = useApi<RequirementData>(
    async () => {
      const domainData = await fetchDomains()
      return { domains: domainData || [] }
    },
    []
  )

  const {
    data: documentPage,
    isLoading,
    isRefetching,
    isError,
    error,
    refetch: refetchDocuments,
  } = useApi(
    (signal) => fetchRequirements({
      page: docPage,
      page_size: docPageSize,
      ...(debouncedKeyword ? { keyword: debouncedKeyword } : {}),
    }, signal),
    [docPage, debouncedKeyword],
  )

  const {
    data: activeDoc,
    isLoading: isDetailLoading,
    isRefetching: isDetailRefetching,
    isError: isDetailError,
    error: detailError,
    refetch: refetchDetail,
  } = useApi<RequirementDocument | null>(
    (signal) => activeDocId == null
      ? Promise.resolve(null)
      : fetchRequirement(activeDocId, signal),
    { deps: [activeDocId], showErrorToast: false },
  )

  const {
    data: activeCoverage,
    isLoading: isCoverageLoading,
    isRefetching: isCoverageRefetching,
  } = useApi<RequirementCoverage | null>(
    (signal) => activeDocId == null
      ? Promise.resolve(null)
      : fetchRequirementCoverage(activeDocId, signal),
    { deps: [activeDocId], showErrorToast: false },
  )

  const refetch = () => {
    refetchMetadata()
    refetchDocuments()
    if (activeDocId != null) {
      refetchDetail()
    }
  }

  const domains = useMemo(() => metadata?.domains || [], [metadata?.domains])
  const docs = documentPage?.items || []
  const totalDocuments = documentPage?.total || 0

  // Stats
  const totalModules = useMemo(
    () => domains.reduce((sum: number, item: any) => sum + (item.modules?.length || 0), 0),
    [domains],
  )
  const coverage = activeCoverage?.coverage_rate ?? 0

  // Dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) handleFileUpload(acceptedFiles[0])
    },
    accept: {
      'text/markdown': ['.md'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx', '.xls'],
    },
    multiple: false,
    disabled: uploading,
  })

  // Upload handlers
  const handleFileUpload = async (file: File) => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const doc = await uploadRequirement(formData)
      setActiveDocId(doc.id)
      toast.success(`「${doc.title}」上传成功`)
      refetch()
    } catch {
      toast.error('上传失败')
    } finally {
      setUploading(false)
    }
  }

  const handleLanhuSubmit = () => {
    const url = lanhuUrl.trim()
    if (!url) {
      toast.warning('请输入蓝湖链接')
      return
    }
    setEvOpen(true)
  }

  // AI Generate
  const handleGenerate = async (docId: number, useExtraction = false) => {
    setGeneratingDocId(docId)
    setGenerating(true)
    try {
      const task = await generateTestCasesAsync(docId, { use_extraction: useExtraction })
      const result = await runAsyncAiTask(task.id)
      setAiResult(result)
      setActiveDocId(docId)
      setModalMode('generate')
      setShowAiModal(true)
    } catch {
      toast.error('AI 生成失败，请稍后重试')
    } finally {
      setGenerating(false)
      setGeneratingDocId(null)
    }
    // Refresh doc list (outside try/catch so a refresh failure doesn't mask generation success)
    refetch()
  }

  // ── Stage 1: Feature Extraction handlers ──

  const handleExtract = async (docId: number) => {
    setExtractingDocId(docId)
    setExtracting(true)
    try {
      // A code=0/null response is the only valid signal to create a new
      // extraction. Permission, server and network errors must not overwrite
      // an existing review session.
      const result = await getOrCreateExtraction(docId)

      setExtractionResult(result)
      setActiveDocId(docId)
      setModalMode('extract')
      setShowAiModal(true)

      // Refresh doc list to update status badges
      refetch()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '功能拆分失败'
      toast.error(msg)
    } finally {
      setExtracting(false)
      setExtractingDocId(null)
    }
  }

  const handleReExtract = async (docId: number) => {
    setExtractingDocId(docId)
    setExtracting(true)
    try {
      await confirmExtraction(docId, {
        action: 'reject',
        rejected_notes: '用户主动重新拆分',
      })
      const task = await extractFeaturesAsync(docId)
      const result = await runAsyncAiTask(task.id)
      setExtractionResult(result)
      setActiveDocId(docId)
      setModalMode('extract')
      setShowAiModal(true)
      refetch()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '重新拆分失败'
      toast.error(msg)
    } finally {
      setExtracting(false)
      setExtractingDocId(null)
    }
  }

  const handleExtractionConfirmAndGenerate = (aiResult: AIGenerateResult) => {
    // Called when user confirms extraction + auto-generates cases
    // Transition from extraction mode to generate mode in same modal
    setAiResult(aiResult)
    setModalMode('generate')
    // Mark this doc as having confirmed extraction
    if (activeDocId != null) {
      setConfirmedExtractionIds((prev) => new Set(prev).add(activeDocId))
    }
    // Refresh doc list
    refetch()
  }

  const handleExtractionReject = () => {
    // Called when user rejects extraction — close modal
    setShowAiModal(false)
    setExtractionResult(null)
    // Refresh doc list to show updated status
    refetch()
  }

  const handleImportSuccess = async () => {
    if (activeDocId != null) {
      try {
        const result = await fetchGeneratedCases(activeDocId)
        setAiResult(result)
      } catch { /* keep existing result */ }
    }
    refetch()
  }

  /** Navigate to feature extraction for the doc imported from this evidence job */
  const handleViewExtraction = async (job: any) => {
    // Find the requirement document linked to this job (via import_result_json)
    try {
      const importResult = job.import_result_json ? JSON.parse(job.import_result_json) : null
      const docId = importResult?.requirement_doc_id
      if (docId) {
        setActiveDocId(docId)
        handleExtract(docId)
      } else {
        toast.info('该任务未导入需求文档，请先在任务详情中导入')
      }
    } catch {
      toast.info('该任务未导入需求文档')
    }
  }

  /** Open screenshot preview for an evidence job (batch-28) */
  const handleViewScreenshots = async (job: any) => {
    try {
      const { fetchLanhuEvidenceAssets, fetchLanhuEvidencePages } = await import('@/api/lanhuEvidence')
      const [assets, pageData] = await Promise.all([
        fetchLanhuEvidenceAssets(job.id),
        fetchLanhuEvidencePages(job.id),
      ])
      const pagesById = new Map((pageData.items || []).map((page) => [page.id, page]))
      const screenshots = (assets || [])
        .filter((a: any) => a.asset_type === 'screenshot')
        .map((a: any, i: number) => ({
          page_name: pagesById.get(a.page_id)?.page_name
            || a.relative_path?.replace(/^.*[\\/]/, '')
            || `截图 ${i + 1}`,
          page_index: i,
          ocr_text: pagesById.get(a.page_id)?.merged_text
            || pagesById.get(a.page_id)?.ocr_text
            || pagesById.get(a.page_id)?.dom_text
            || '',
          interactions: pagesById.get(a.page_id)?.quality_json || '',
          asset_id: a.id,
        }))
      if (screenshots.length > 0) {
        setScreenshotPages(screenshots)
        setScreenshotVersion(job.source_url ? (job.source_url.match(/\/updates\/([\d.]+)/) || [])[1] || '' : '')
        setShowScreenshotPreview(true)
      } else {
        toast.info('该任务暂无截图资产')
      }
    } catch {
      toast.error('获取截图失败')
    }
  }

  const handleViewCases = async (docId: number) => {
    try {
      const result = await fetchGeneratedCases(docId)
      setAiResult(result)
      setActiveDocId(docId)
      setModalMode('generate')
      setShowAiModal(true)
    } catch {
      toast.error('获取用例失败')
    }
  }

  const handleDelete = (doc: RequirementDocumentBrief) => {
    setDeleteTarget(doc)
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteRequirement(deleteTarget.id)
      toast.success('已删除')
      if (activeDocId === deleteTarget.id) setActiveDocId(null)
      setDeleteTarget(null)
      refetch()
    } catch {
      toast.error('删除失败')
    }
  }

  const totalDocPages = Math.max(1, Math.ceil(totalDocuments / docPageSize))

  const paginatedDomains = domains.slice((domainPage - 1) * domainPageSize, domainPage * domainPageSize)
  const totalDomainPages = Math.ceil(domains.length / domainPageSize)

  const activeDocBrief = docs.find((d) => d.id === activeDocId)

  return (
    <PageShell
      title="需求文档"
      description="上传 PRD、Excel 或蓝湖链接，使用 AI 提取需求并生成测试用例。"
      actions={(
        <>
          <Button variant="secondary" size="sm" onClick={() => setLanhuSettingsOpen(true)} title="蓝湖项目配置" disabled={!canWriteDocs}>
            <Settings className="size-4" />
            蓝湖设置
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={refetch}
            disabled={isLoading || isRefetching || isMetadataLoading || isMetadataRefetching}
          >
            {isLoading || isRefetching || isMetadataLoading || isMetadataRefetching
              ? <Loader2 className="size-4 animate-spin" />
              : <RotateCcw className="size-4" />}
            刷新
          </Button>
        </>
      )}
      glass
    >
      <div className="space-y-4">
      {/* Main layout: task panel (left) + content (right) */}
      <div className="flex flex-col gap-4 items-stretch xl:flex-row xl:items-start">
        <EvidenceTaskPanel
          onViewExtraction={handleViewExtraction}
          onViewScreenshots={handleViewScreenshots}
          onNewTask={() => setEvOpen(true)}
          refreshKey={evidenceRefreshKey}
        />

        <div className="flex-1 min-w-0 space-y-4">

      {/* Stats Row */}
      <RequirementStatsRow
        totalDocuments={totalDocuments}
        domainCount={domains.length}
        totalModules={totalModules}
        coverage={coverage}
        isCoverageLoading={isCoverageLoading}
        isCoverageRefetching={isCoverageRefetching}
        activeDocId={activeDocId}
        importedCaseCount={docs.reduce((s, d) => s + d.imported_count, 0)}
      />

      {/* Upload Area */}
      <RequirementUploadCard
        canWriteDocs={canWriteDocs}
        getRootProps={getRootProps}
        getInputProps={getInputProps}
        isDragActive={isDragActive}
        uploading={uploading}
        lanhuUrl={lanhuUrl}
        onLanhuUrlChange={setLanhuUrl}
        onLanhuSubmit={handleLanhuSubmit}
      />

      {/* Content Preview */}
      {activeDocId != null && (
        <RequirementContentPreview
          title={activeDocBrief?.title || activeDoc?.title || `#${activeDocId}`}
          fileType={activeDocBrief?.file_type || activeDoc?.file_type}
          isLoading={isDetailLoading}
          isRefetching={isDetailRefetching}
          isError={isDetailError}
          errorMessage={detailError?.message}
          content={activeDoc?.content}
          previewExpanded={previewExpanded}
          onTogglePreview={() => setPreviewExpanded(!previewExpanded)}
          onClose={() => { setActiveDocId(null); setPreviewExpanded(false) }}
          onRetry={refetchDetail}
        />
      )}

      <ProductionDiffPanel />

      <InteractionGapPanel />

      {/* Document Table */}
      <RequirementDocTable
        docs={docs}
        keyword={keyword}
        activeDocId={activeDocId}
        canWriteDocs={canWriteDocs}
        generating={generating}
        generatingDocId={generatingDocId}
        extracting={extracting}
        extractingDocId={extractingDocId}
        isLoading={isLoading}
        isError={isError}
        error={error}
        refetch={refetch}
        debouncedKeyword={debouncedKeyword}
        page={docPage}
        totalPages={totalDocPages}
        total={totalDocuments}
        onKeywordChange={(value) => { setKeyword(value); setDocPage(1) }}
        onClearKeyword={() => { setKeyword(''); setDocPage(1) }}
        onPreviewDoc={(id) => { setActiveDocId(id); setPreviewExpanded(false) }}
        onGenerate={handleGenerate}
        onExtract={handleExtract}
        onReExtract={handleReExtract}
        onViewCases={handleViewCases}
        onDelete={handleDelete}
        onNavigate={navigate}
        onOpenVersionCompare={(diffData) => { setVersionDiffData(diffData); setShowVersionCompare(true) }}
        onPageChange={setDocPage}
      />

      {/* Domain Coverage Table */}
      <RequirementDomainCoverageTable
        paginatedDomains={paginatedDomains}
        page={domainPage}
        totalPages={totalDomainPages}
        total={domains.length}
        onPageChange={setDomainPage}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(o) => { if (!o) setDeleteTarget(null) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除需求文档「{deleteTarget?.title}」吗？删除后不可恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmDelete}>删除</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

        </div>{/* end flex-1 main content */}
      </div>{/* end flex row */}

      {/* Lanhu Evidence — dialogs rendered at root so they work regardless of active tab */}
      <LanhuEvidenceDialog
        open={evOpen}
        onOpenChange={setEvOpen}
        initialUrl={lanhuUrl}
        initialImportRequirement
        onCreated={(job) => {
          setEvJobId(job.id)
          setEvidenceRefreshKey((value) => value + 1)
        }}
      />
      <LanhuEvidenceJobDrawer
        open={evJobId != null}
        onOpenChange={(v) => { if (!v) setEvJobId(null) }}
        jobId={evJobId}
      />

      {/* Unified AI Modal — handles extraction review + case viewing */}
      <AiResultModal
        open={showAiModal}
        result={aiResult}
        extractionResult={extractionResult}
        documentId={activeDocId}
        mode={modalMode}
        onClose={() => {
          setShowAiModal(false)
          setExtractionResult(null)
        }}
        onImportSuccess={handleImportSuccess}
        onExtractionConfirmAndGenerate={handleExtractionConfirmAndGenerate}
        onExtractionReject={handleExtractionReject}
      />

      {/* ── batch-28: Version comparison modal ── */}
      <VersionCompare
        open={showVersionCompare}
        onClose={() => setShowVersionCompare(false)}
        diffData={versionDiffData}
      />

      {/* ── batch-28: Screenshot preview modal ── */}
      <PrototypePreview
        open={showScreenshotPreview}
        onClose={() => setShowScreenshotPreview(false)}
        pages={screenshotPages}
        version={screenshotVersion}
      />

      {/* ── Lanhu Settings Dialog (batch-34) ── */}
      <Dialog open={lanhuSettingsOpen} onOpenChange={setLanhuSettingsOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="size-5" />
              蓝湖项目配置
            </DialogTitle>
            <DialogDescription>
              配置蓝湖用户端和运营后台的项目 ID，用于自动解析设计稿链接。这些设置保存在本地浏览器中。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-3">
              <h4 className="flex items-center gap-1.5 text-sm font-medium text-status-info"><Smartphone className="size-4" aria-hidden="true" />用户端 (CamelTv)</h4>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <Label>Project ID</Label>
                  <Input
                    placeholder="蓝湖用户端项目 ID"
                    value={lanhuUserProjectId}
                    onChange={(e) => setLanhuUserProjectId(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label>Version ID (可选)</Label>
                  <Input
                    placeholder="默认版本 ID"
                    value={lanhuUserVersionId}
                    onChange={(e) => setLanhuUserVersionId(e.target.value)}
                  />
                </div>
              </div>
            </div>
            <div className="space-y-3">
              <h4 className="flex items-center gap-1.5 text-sm font-medium text-status-accent"><Monitor className="size-4" />运营后台 (Admin)</h4>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <Label>Project ID</Label>
                  <Input
                    placeholder="蓝湖运营后台项目 ID"
                    value={lanhuAdminProjectId}
                    onChange={(e) => setLanhuAdminProjectId(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label>Version ID (可选)</Label>
                  <Input
                    placeholder="默认版本 ID"
                    value={lanhuAdminVersionId}
                    onChange={(e) => setLanhuAdminVersionId(e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setLanhuSettingsOpen(false)}>取消</Button>
            <Button onClick={saveLanhuSettings}>保存配置</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
    </PageShell>
  )
}
