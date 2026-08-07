import { Badge, Button, PageShell, type BadgeTone } from '@/ui'
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/ui'
import Pagination from '@/components/Pagination'
import StatCard from '@/components/StatCard'
import { Progress } from '@/ui'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  BookOpen, Trash2, Eye, FileSpreadsheet, FileText,
  Inbox, Layers, Link2, RotateCcw, Sparkles, Search, XCircle, Loader2, ExternalLink, Cloud, GitCompare, Settings, Smartphone, Monitor,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { AsyncState } from '@/components/state'
import AiResultModal from './AiResultModal'
import EvidenceTaskPanel from './components/EvidenceTaskPanel'
import ProductionDiffPanel from './components/ProductionDiffPanel'
import InteractionGapPanel from './components/InteractionGapPanel'
import VersionCompare from './components/VersionCompare'
import PrototypePreview from './components/PrototypePreview'
import LanhuEvidenceDialog from '@/pages/knowledge/components/LanhuEvidenceDialog'
import LanhuEvidenceJobDrawer from '@/pages/knowledge/components/LanhuEvidenceJobDrawer'

const TYPE_TAG: Record<string, { className: string; label: string; icon: React.ReactNode }> = {
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

interface RequirementData {
  domains: any[]
}

export default function RequirementPage() {
  const hasPerm = useAuthStore((state) => state.hasPerm)
  const canWriteDocs = hasPerm('requirement:upload') || hasPerm('requirement:generate') || hasPerm('requirement:import')
  useDocumentTitle('需求管理')
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

  const docPageSize = 10
  const domainPageSize = 8

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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          icon={BookOpen}
          label="需求文档"
          value={totalDocuments}
          variant="glass"
        />
        <StatCard
          icon={Layers}
          label="覆盖业务域"
          value={domains.length}
          trend={`/ ${totalModules} 模块`}
          variant="glass"
        />
        <Card size="sm" className="ui-surface">
          <CardContent>
            <div className="text-xs text-muted-foreground mb-1">
              {activeDocId == null ? '需求覆盖率（选择文档查看）' : '当前需求覆盖率'}
            </div>
            <div className="flex items-center gap-2">
              <Progress
                value={coverage}
                className="flex-1 h-2"
                aria-label="当前需求覆盖率"
              />
              <span className="text-sm font-medium tabular-nums">
                {(isCoverageLoading || isCoverageRefetching) && activeDocId != null ? '…' : `${coverage}%`}
              </span>
            </div>
          </CardContent>
        </Card>
        <StatCard
          icon={Sparkles}
          label="AI 导入用例"
          value={docs.reduce((s, d) => s + d.imported_count, 0)}
          variant="glass"
        />
      </div>

      {/* Upload Area */}
      <Card size="sm" className={'ui-surface' + (canWriteDocs ? '' : ' opacity-60 pointer-events-none')}>
        <CardHeader className="border-b pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Cloud className="size-4" />
            上传需求
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <Tabs defaultValue="file">
            <TabsList>
              <TabsTrigger value="file">文件上传</TabsTrigger>
              <TabsTrigger value="lanhu">蓝湖链接</TabsTrigger>
            </TabsList>
            <TabsContent value="file" className="pt-4">
              <div
                {...getRootProps()}
                className={cn(
                  'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
                  isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50',
                  uploading && 'opacity-50 cursor-not-allowed',
                )}
              >
                <input {...getInputProps({ 'aria-label': '上传需求文档' })} />
                <Inbox className="size-10 mx-auto text-muted-foreground mb-3" />
                <p className="text-sm">点击或拖拽文件到此区域上传</p>
                <p className="text-xs text-muted-foreground mt-1">
                  支持 .md（Markdown）、.docx（Word）、.xlsx（Excel）格式
                </p>
              </div>
            </TabsContent>
            <TabsContent value="lanhu" className="pt-4 space-y-3">
              <div className="flex w-full flex-col gap-2 sm:flex-row sm:gap-0">
                <div className="relative flex-1">
                  <Link2 className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-primary pointer-events-none" />
                  <Input
                    className="pl-8 sm:rounded-r-none sm:border-r-0 focus-visible:z-10"
                    placeholder="输入蓝湖设计稿链接..."
                    value={lanhuUrl}
                    onChange={(e) => setLanhuUrl(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleLanhuSubmit()}
                  />
                  {lanhuUrl && (
                    <button
                      type="button"
                      className="absolute right-1 top-1/2 min-h-11 min-w-11 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      onClick={() => setLanhuUrl('')}
                      aria-label="清空蓝湖链接"
                    >
                      <XCircle className="size-4" />
                    </button>
                  )}
                </div>
                <Button className="sm:rounded-l-none" onClick={handleLanhuSubmit} disabled={uploading}>
                  {uploading ? <Loader2 className="size-4 animate-spin" /> : null}
                  证据采集
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  全页面滚动截图 + OCR，生成可追溯证据包（Word/JSON），再入需求 / RAG / Wiki
                </span>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Content Preview */}
      {activeDocId != null && (
        <Card size="sm" className="ui-surface">
          <CardHeader className="border-b pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Search className="size-4" />
                内容预览：{activeDocBrief?.title || activeDoc?.title || `#${activeDocId}`}
                {(activeDocBrief?.file_type || activeDoc?.file_type) && TYPE_TAG[activeDocBrief?.file_type || activeDoc?.file_type || ''] && (
                  <Badge
                    tone="neutral"
                    className={cn('gap-1', TYPE_TAG[activeDocBrief?.file_type || activeDoc?.file_type || ''].className)}
                  >
                    {TYPE_TAG[activeDocBrief?.file_type || activeDoc?.file_type || ''].icon}
                    {TYPE_TAG[activeDocBrief?.file_type || activeDoc?.file_type || ''].label}
                  </Badge>
                )}
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => { setActiveDocId(null); setPreviewExpanded(false) }}>
                收起
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            {isDetailLoading || isDetailRefetching ? (
              <div className="flex min-h-[100px] items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="mr-2 size-4 animate-spin" />
                正在加载完整内容…
              </div>
            ) : isDetailError ? (
              <div className="flex min-h-[100px] flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
                <span>{detailError?.message || '文档详情加载失败'}</span>
                <Button variant="secondary" size="sm" onClick={refetchDetail}>重试加载</Button>
              </div>
            ) : (
              <div className={cn(
                'whitespace-pre-wrap text-xs bg-muted/50 rounded-md p-3 overflow-auto',
                !previewExpanded && 'max-h-[200px]',
              )}>
                {activeDoc?.content || '文档内容为空'}
              </div>
            )}
            {activeDoc?.content && activeDoc.content.length > 400 && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-1"
                onClick={() => setPreviewExpanded(!previewExpanded)}
              >
                {previewExpanded ? '收起' : '展开全部'}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      <ProductionDiffPanel />

      <InteractionGapPanel />

      {/* Document Table */}
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
                onChange={(e) => { setKeyword(e.target.value); setDocPage(1) }}
              />
              {keyword && (
                <button
                  type="button"
                  className="absolute right-0 top-1/2 min-h-9 min-w-9 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  onClick={() => { setKeyword(''); setDocPage(1) }}
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
                              onClick={() => {
                                setActiveDocId(r.id)
                                setPreviewExpanded(false)
                              }}
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
                                onClick={() => navigate(`/knowledge?tab=wikidiff&q=${encodeURIComponent(r.title || '')}`)}
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
                                    disabled={!canWriteDocs || (generating && generatingDocId === r.id)}
                                    onClick={() => handleGenerate(r.id, true)}
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
                                    disabled={!canWriteDocs || (extracting && extractingDocId === r.id)}
                                    onClick={() => handleExtract(r.id)}
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
                                    disabled={!canWriteDocs || (extracting && extractingDocId === r.id)}
                                    onClick={() => handleExtract(r.id)}
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
                                  disabled={!canWriteDocs || (
                                    r.extraction_status === 'confirmed'
                                      ? extracting && extractingDocId === r.id
                                      : generating && generatingDocId === r.id
                                  )}
                                  onClick={() => {
                                    if (r.extraction_status === 'confirmed') {
                                      handleReExtract(r.id)
                                    } else {
                                      handleGenerate(r.id, false)
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
                                          onClick={() => {
                                            setVersionDiffData(diffData)
                                            setShowVersionCompare(true)
                                          }}
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
                                  onClick={() => handleGenerate(r.id, false)}
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
                                  onClick={() => handleGenerate(r.id, false)}
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
                                  onClick={() => handleViewCases(r.id)}
                                >
                                  <Eye className="size-3.5" />
                                  查看用例
                                </Button>
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  onClick={() => navigate(`/requirement/${r.id}/review`)}
                                >
                                  <Layers className="size-3.5" />
                                  审查用例
                                </Button>
                              </>
                            )}
                            <Button
                              size="sm"
                              variant="danger"
                              disabled={!canWriteDocs}
                              onClick={() => handleDelete(r)}
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
                page={docPage}
                totalPages={totalDocPages}
                total={totalDocuments}
                onChange={(p) => setDocPage(p)}
              />
            </>
            )}
          </AsyncState>
        </CardContent>
      </Card>

      {/* Domain Coverage Table */}
      <Card size="sm" className="ui-surface">
        <CardHeader className="border-b pb-3">
          <CardTitle className="text-sm">需求域与用例覆盖</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[180px]">业务域</TableHead>
                <TableHead className="w-[90px]">用例数</TableHead>
                <TableHead>模块</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedDomains.map((item: any) => (
                <TableRow key={item.domain}>
                  <TableCell className="font-medium">{item.domain}</TableCell>
                  <TableCell>{item.count}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 flex-wrap">
                      {(item.modules || []).slice(0, 8).map((m: any) => (
                        <Badge key={m.module} tone="neutral">
                          {m.module} ({m.count})
                        </Badge>
                      ))}
                      {(item.modules || []).length > 8 && (
                        <Badge tone="neutral">+{(item.modules || []).length - 8}</Badge>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination
            page={domainPage}
            totalPages={totalDomainPages}
            total={domains.length}
            onChange={(p) => setDomainPage(p)}
          />
        </CardContent>
      </Card>

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
