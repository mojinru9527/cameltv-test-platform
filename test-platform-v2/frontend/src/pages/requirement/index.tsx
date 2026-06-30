import { useCallback, useEffect, useMemo, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'
import { fetchDomains, fetchTestCases } from '@/api/testcase'
import {
  deleteRequirement, extractFeatures, fetchGeneratedCases, fetchRequirements,
  generateTestCases, getExtraction, uploadRequirement,
} from '@/api/requirement'
import type { AIGenerateResult, FeatureExtractionResult, RequirementDocument } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import Pagination from '@/components/Pagination'
import PageHeader from '@/components/PageHeader'
import StatCard from '@/components/StatCard'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  BookOpen, Trash2, Eye, FileSpreadsheet, FileText,
  Inbox, Layers, Link2, RotateCcw, Sparkles, Search, XCircle, Loader2, ExternalLink, Cloud,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import AiResultModal from './AiResultModal'

const TYPE_TAG: Record<string, { className: string; label: string; icon: React.ReactNode }> = {
  md: { className: 'border-blue-200 bg-blue-50 text-blue-700', label: 'Markdown', icon: <FileText className="size-3" /> },
  docx: { className: 'border-cyan-200 bg-cyan-50 text-cyan-700', label: 'Word', icon: <FileText className="size-3" /> },
  xlsx: { className: 'border-green-200 bg-green-50 text-green-700', label: 'Excel', icon: <FileSpreadsheet className="size-3" /> },
  lanhu: { className: 'border-purple-200 bg-purple-50 text-purple-700', label: '蓝湖', icon: <Link2 className="size-3" /> },
}

const STATUS_VARIANT: Record<string, { variant: 'secondary' | 'outline'; className?: string; label: string }> = {
  uploaded: { variant: 'secondary', label: '已上传' },
  parsed: { variant: 'secondary', label: '已解析' },
  generated: { variant: 'outline', className: 'border-blue-200 bg-blue-50 text-blue-700', label: '已生成' },
  imported: { variant: 'outline', className: 'border-green-200 bg-green-50 text-green-700', label: '已导入' },
}

export default function RequirementPage() {
  const [domains, setDomains] = useState<any[]>([])
  const [cases, setCases] = useState<any[]>([])
  const [docs, setDocs] = useState<RequirementDocument[]>([])
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generatingDocId, setGeneratingDocId] = useState<number | null>(null)
  const [aiResult, setAiResult] = useState<AIGenerateResult | null>(null)
  const [showAiModal, setShowAiModal] = useState(false)
  const [modalMode, setModalMode] = useState<'generate' | 'view' | 'extract'>('generate')
  const [activeDocId, setActiveDocId] = useState<number | null>(null)
  const [lanhuUrl, setLanhuUrl] = useState('')
  const [lanhuDesc, setLanhuDesc] = useState('')
  const [previewExpanded, setPreviewExpanded] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<RequirementDocument | null>(null)
  const [docPage, setDocPage] = useState(1)
  const [domainPage, setDomainPage] = useState(1)

  // ── Stage 1: Feature Extraction state ──
  const [extractionResult, setExtractionResult] = useState<FeatureExtractionResult | null>(null)
  const [extracting, setExtracting] = useState(false)
  const [extractingDocId, setExtractingDocId] = useState<number | null>(null)
  const [confirmedExtractionIds, setConfirmedExtractionIds] = useState<Set<number>>(new Set())

  const docPageSize = 10
  const domainPageSize = 8

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [domainData, caseData, docData]: any[] = await Promise.all([
        fetchDomains(),
        fetchTestCases({ page: 1, page_size: 200 }),
        fetchRequirements(),
      ])
      setDomains(domainData || [])
      setCases(caseData?.items || [])
      setDocs(docData || [])
    } catch {
      // keep
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  // Stats
  const totalModules = useMemo(
    () => domains.reduce((sum: number, item: any) => sum + (item.modules?.length || 0), 0),
    [domains],
  )
  const automatedCases = 0
  const coverage = 0

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
      setDocs((prev) => [doc, ...prev])
      setActiveDocId(doc.id)
      toast.success(`「${doc.title}」上传成功`)
    } catch {
      toast.error('上传失败')
    } finally {
      setUploading(false)
    }
  }

  const handleLanhuSubmit = async () => {
    const url = lanhuUrl.trim()
    if (!url) {
      toast.warning('请输入蓝湖链接')
      return
    }
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('lanhu_url', url)
      if (lanhuDesc.trim()) {
        formData.append('lanhu_description', lanhuDesc.trim())
      }
      const doc = await uploadRequirement(formData)
      setDocs((prev) => [doc, ...prev])
      setActiveDocId(doc.id)
      setLanhuUrl('')
      setLanhuDesc('')
      toast.success('蓝湖链接已提交')
    } catch {
      toast.error('提交失败')
    } finally {
      setUploading(false)
    }
  }

  // AI Generate
  const handleGenerate = async (docId: number) => {
    setGeneratingDocId(docId)
    setGenerating(true)
    try {
      const result = await generateTestCases(docId)
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
    try {
      const updated = await fetchRequirements()
      setDocs(updated || [])
    } catch { /* refresh failed – list will be stale but generation succeeded */ }
  }

  // ── Stage 1: Feature Extraction handlers ──

  const handleExtract = async (docId: number) => {
    setExtractingDocId(docId)
    setExtracting(true)
    try {
      // First try to get existing extraction (resume review)
      let result: FeatureExtractionResult | null = null
      try {
        result = await getExtraction(docId)
      } catch {
        // No existing extraction, will run fresh
      }

      if (!result || !result.modules || result.modules.length === 0) {
        result = await extractFeatures(docId)
      }

      setExtractionResult(result)
      setActiveDocId(docId)
      setModalMode('extract')
      setShowAiModal(true)

      // Refresh doc list to update status badges
      try {
        const updated = await fetchRequirements()
        setDocs(updated || [])
      } catch { /* ok */ }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '功能拆分失败'
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
    try {
      fetchRequirements().then((updated) => setDocs(updated || []))
    } catch { /* ok */ }
  }

  const handleExtractionReject = () => {
    // Called when user rejects extraction — close modal
    setShowAiModal(false)
    setExtractionResult(null)
    // Refresh doc list to show updated status
    try {
      fetchRequirements().then((updated) => setDocs(updated || []))
    } catch { /* ok */ }
  }

  const handleImportSuccess = async () => {
    if (activeDocId != null) {
      try {
        const result = await fetchGeneratedCases(activeDocId)
        setAiResult(result)
      } catch { /* keep existing result */ }
    }
    loadAll()
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

  const handleDelete = (doc: RequirementDocument) => {
    setDeleteTarget(doc)
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteRequirement(deleteTarget.id)
      toast.success('已删除')
      if (activeDocId === deleteTarget.id) setActiveDocId(null)
      setDeleteTarget(null)
      loadAll()
    } catch {
      toast.error('删除失败')
    }
  }

  // Filtered docs
  const filteredDocs = docs.filter((d) => {
    const text = `${d.title} ${d.source_ref} ${d.file_type}`.toLowerCase()
    return text.includes(keyword.toLowerCase())
  })

  const paginatedDocs = filteredDocs.slice((docPage - 1) * docPageSize, docPage * docPageSize)
  const totalDocPages = Math.ceil(filteredDocs.length / docPageSize)

  const paginatedDomains = domains.slice((domainPage - 1) * domainPageSize, domainPage * domainPageSize)
  const totalDomainPages = Math.ceil(domains.length / domainPageSize)

  // Content preview
  const activeDoc = docs.find((d) => d.id === activeDocId)

  return (
    <div className="space-y-4">
      {/* Header */}
      <PageHeader title="需求文档" icon={BookOpen} description="上传 PRD / Excel / 蓝湖链接，AI 自动生成测试用例。">
        <Button variant="outline" size="sm" onClick={loadAll} disabled={loading}>
          {loading ? <Loader2 className="size-4 animate-spin" /> : <RotateCcw className="size-4" />}
          刷新
        </Button>
      </PageHeader>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          icon={BookOpen}
          label="需求文档"
          value={docs.length}
          variant="glass"
        />
        <StatCard
          icon={Layers}
          label="覆盖业务域"
          value={domains.length}
          trend={`/ ${totalModules} 模块`}
          variant="glass"
        />
        <Card size="sm">
          <CardContent>
            <div className="text-xs text-muted-foreground mb-1">接口自动化占比</div>
            <div className="flex items-center gap-2">
              <Progress value={coverage} className="flex-1 h-2" />
              <span className="text-sm font-medium tabular-nums">{coverage}%</span>
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
      <Card size="sm">
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
                <input {...getInputProps()} />
                <Inbox className="size-10 mx-auto text-muted-foreground mb-3" />
                <p className="text-sm">点击或拖拽文件到此区域上传</p>
                <p className="text-xs text-muted-foreground mt-1">
                  支持 .md（Markdown）、.docx（Word）、.xlsx（Excel）格式
                </p>
              </div>
            </TabsContent>
            <TabsContent value="lanhu" className="pt-4 space-y-3">
              <div className="flex w-full">
                <div className="relative flex-1">
                  <Link2 className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-[#7b61ff] pointer-events-none" />
                  <Input
                    className="pl-8 rounded-r-none border-r-0 focus-visible:z-10"
                    placeholder="输入蓝湖设计稿链接..."
                    value={lanhuUrl}
                    onChange={(e) => setLanhuUrl(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleLanhuSubmit()}
                  />
                  {lanhuUrl && (
                    <button
                      type="button"
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      onClick={() => setLanhuUrl('')}
                    >
                      <XCircle className="size-4" />
                    </button>
                  )}
                </div>
                <Button className="rounded-l-none" onClick={handleLanhuSubmit} disabled={uploading}>
                  {uploading ? <Loader2 className="size-4 animate-spin" /> : null}
                  提交
                </Button>
              </div>
              <Textarea
                placeholder="补充说明（可选）：描述设计稿中的页面功能、交互逻辑、关键组件等，帮助 AI 更精准地生成用例"
                value={lanhuDesc}
                onChange={(e) => setLanhuDesc(e.target.value)}
                rows={3}
              />
              {lanhuDesc && (
                <button
                  type="button"
                  className="text-xs text-muted-foreground hover:text-foreground"
                  onClick={() => setLanhuDesc('')}
                >
                  清除说明
                </button>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Content Preview */}
      {activeDoc && (
        <Card size="sm">
          <CardHeader className="border-b pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Search className="size-4" />
                内容预览：{activeDoc.title}
                {activeDoc.file_type && TYPE_TAG[activeDoc.file_type] && (
                  <Badge variant="outline" className={cn('gap-1', TYPE_TAG[activeDoc.file_type].className)}>
                    {TYPE_TAG[activeDoc.file_type].icon}
                    {TYPE_TAG[activeDoc.file_type].label}
                  </Badge>
                )}
              </CardTitle>
              <Button variant="link" size="sm" onClick={() => { setActiveDocId(null); setPreviewExpanded(false) }}>
                收起
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            <div className={cn(
              'whitespace-pre-wrap text-xs bg-muted/50 rounded-md p-3 overflow-auto',
              !previewExpanded && 'max-h-[200px]',
            )}>
              {activeDoc.content}
            </div>
            {activeDoc.content && activeDoc.content.length > 400 && (
              <Button
                variant="link"
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

      {/* Document Table */}
      <Card size="sm">
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
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  onClick={() => { setKeyword(''); setDocPage(1) }}
                >
                  <XCircle className="size-3.5" />
                </button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {filteredDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Inbox className="size-8 mb-2 opacity-40" />
              <p className="text-sm">暂无需求文档，请上传</p>
            </div>
          ) : (
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
                  {paginatedDocs.map((r) => {
                    const isActive = r.id === activeDocId
                    return (
                      <TableRow
                        key={r.id}
                        className={cn('cursor-pointer', isActive && 'bg-accent')}
                        onClick={() => setActiveDocId(r.id)}
                        data-state={isActive ? 'selected' : undefined}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="font-medium truncate max-w-[140px]">{r.title}</span>
                            {r.file_type && TYPE_TAG[r.file_type] && (
                              <Badge variant="outline" className={cn('gap-1 shrink-0', TYPE_TAG[r.file_type].className)}>
                                {TYPE_TAG[r.file_type].icon}
                                {TYPE_TAG[r.file_type].label}
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {r.file_type === 'lanhu' ? (
                            <a
                              href={r.source_ref}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <ExternalLink className="size-3" />
                              <span className="truncate max-w-[150px] inline-block">
                                {r.source_ref.length > 50 ? r.source_ref.slice(0, 50) + '...' : r.source_ref}
                              </span>
                            </a>
                          ) : (
                            <code className="text-xs bg-muted px-1 py-0.5 rounded">{r.source_ref}</code>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          <div className="flex items-center gap-1 flex-wrap justify-center">
                          {r.extraction_status === 'pending_review' && (
                            <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700 text-xs">待审核</Badge>
                          )}
                          {r.extraction_status === 'confirmed' && (
                            <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700 text-xs">已拆分</Badge>
                          )}
                          {(() => {
                            const t = STATUS_VARIANT[r.status]
                            if (!t) return <Badge variant="secondary">{r.status}</Badge>
                            if (r.status === 'imported' || r.status === 'generated') {
                              const hasFunc = r.imported_func_count > 0
                              if (hasFunc) {
                                return (
                                  <Badge variant="outline" className="border-green-200 bg-green-50 text-green-700">
                                    功能用例已导入
                                  </Badge>
                                )
                              }
                            }
                            return (
                              <Badge variant={t.variant} className={t.className}>
                                {t.label}
                              </Badge>
                            )
                          })()}
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          {r.imported_func_count > 0 ? (
                            <span className="text-sm font-semibold text-green-600 tabular-nums">
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
                            {(r.status === 'uploaded' || r.status === 'parsed') && (
                              <>
                                {/* Stage 1: Feature Extraction buttons */}
                                {r.extraction_status === 'confirmed' ? (
                                  <Button
                                    size="sm"
                                    variant="default"
                                    disabled={generating && generatingDocId === r.id}
                                    onClick={() => handleGenerate(r.id)}
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
                                    variant="default"
                                    disabled={extracting && extractingDocId === r.id}
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
                                    variant="default"
                                    disabled={extracting && extractingDocId === r.id}
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
                                  variant="outline"
                                  disabled={generating && generatingDocId === r.id}
                                  onClick={() => handleGenerate(r.id)}
                                >
                                  {generating && generatingDocId === r.id ? (
                                    <Loader2 className="size-3.5 animate-spin" />
                                  ) : (
                                    <Sparkles className="size-3.5" />
                                  )}
                                  {r.extraction_status === 'confirmed' ? '重新拆分' : 'AI 生成'}
                                </Button>
                              </>
                            )}
                            {r.status === 'generated' && (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  disabled={generating && generatingDocId === r.id}
                                  onClick={() => handleGenerate(r.id)}
                                >
                                  {generating && generatingDocId === r.id ? (
                                    <Loader2 className="size-3.5 animate-spin" />
                                  ) : (
                                    <Sparkles className="size-3.5" />
                                  )}
                                  重新生成
                                </Button>
                                {r.imported_count > 0 && (
                                  <Badge variant="outline" className="border-green-200 bg-green-50 text-green-700">
                                    已导入 {r.imported_count} 条
                                  </Badge>
                                )}
                              </>
                            )}
                            {r.status === 'imported' && (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleGenerate(r.id)}
                                >
                                  <Sparkles className="size-3.5" />
                                  重新生成
                                </Button>
                                <Badge variant="outline" className="border-green-200 bg-green-50 text-green-700">
                                  已导入 {r.imported_count} 条
                                </Badge>
                              </>
                            )}
                            {(r.status === 'generated' || r.status === 'imported') && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleViewCases(r.id)}
                              >
                                <Eye className="size-3.5" />
                                查看用例
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="destructive"
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
                total={filteredDocs.length}
                onChange={(p) => setDocPage(p)}
              />
            </>
          )}
        </CardContent>
      </Card>

      {/* Domain Coverage Table */}
      <Card size="sm">
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
                        <Badge key={m.module} variant="secondary">
                          {m.module} ({m.count})
                        </Badge>
                      ))}
                      {(item.modules || []).length > 8 && (
                        <Badge variant="secondary">+{(item.modules || []).length - 8}</Badge>
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
    </div>
  )
}
