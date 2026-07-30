import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router'
import { fetchModuleTree } from '@/api/requirementModules'
import type { ModuleTreeResponse, ModuleTreeNode } from '@/types'
import { Button } from '@/ui'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowLeft, RefreshCw, Package } from '@/lib/icons'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { cn } from '@/lib/utils'
import VersionList from './components/VersionList'
import PlatformCard from './components/PlatformCard'
import AdminModuleCard from './components/AdminModuleCard'
import PageInteractionPanel from './components/PageInteractionPanel'

export default function VersionPanoramaPage() {
  const { id } = useParams<{ id: string }>()
  const bundleId = Number(id)
  const navigate = useNavigate()
  useDocumentTitle('版本全景')

  const [selectedBundleId, setSelectedBundleId] = useState<number>(bundleId)
  const [tree, setTree] = useState<ModuleTreeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPage, setSelectedPage] = useState<ModuleTreeNode | null>(null)
  const [interactionPanelOpen, setInteractionPanelOpen] = useState(false)
  const loadControllerRef = useRef<AbortController | null>(null)

  // Sync selected bundle with URL param
  useEffect(() => {
    if (bundleId && !isNaN(bundleId)) {
      setSelectedBundleId(bundleId)
    }
  }, [bundleId])

  const loadTree = useCallback(async () => {
    if (!selectedBundleId) return
    loadControllerRef.current?.abort()
    const controller = new AbortController()
    loadControllerRef.current = controller
    setLoading(true)
    setError(null)
    try {
      const data = await fetchModuleTree(selectedBundleId, controller.signal)
      if (controller.signal.aborted) return
      setTree(data)
    } catch (err) {
      if (controller.signal.aborted) return
      setError(err instanceof Error ? err.message : '加载模块树失败')
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [selectedBundleId])

  useEffect(() => {
    loadTree()
    return () => loadControllerRef.current?.abort()
  }, [loadTree])

  // Navigate when selecting a different bundle
  const handleBundleSelect = (newBundleId: number) => {
    setSelectedBundleId(newBundleId)
    navigate(`/release-bundles/${newBundleId}/panorama`, { replace: true })
  }

  // Page click → open interaction panel
  const handlePageClick = (page: ModuleTreeNode) => {
    setSelectedPage(page)
    setInteractionPanelOpen(true)
  }

  // Group modules by platform
  const platformModules = useCallback(() => {
    if (!tree?.roots) return {}
    const groups: Record<string, ModuleTreeNode[]> = {}
    for (const node of tree.roots) {
      const platform = node.platform || 'UNKNOWN'
      if (!groups[platform]) groups[platform] = []
      groups[platform].push(node)
    }
    return groups
  }, [tree])

  const platforms = platformModules()
  const platformNames = Object.keys(platforms).filter((p) => p !== 'ADMIN')
  const adminModules = platforms['ADMIN'] ?? []

  // Collect all modules for AdminModuleCard lookup
  const allModules = tree?.roots ?? []

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex shrink-0 flex-wrap items-center gap-3 border-b bg-card px-3 py-3 sm:gap-4 sm:px-6 sm:py-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/release-bundles')}
          aria-label="返回发布包列表"
        >
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
        </Button>
        <div className="flex-1">
          <h1 className="text-lg font-bold">
            {tree?.bundle_name ?? '版本全景'}
          </h1>
          {tree && (
            <p className="text-sm text-muted-foreground">
              用户端 {tree.client_version}
              {tree.admin_version ? ` / 运营后台 ${tree.admin_version}` : ''}
            </p>
          )}
        </div>
        {tree && (
          <div className="flex w-full items-center gap-3 text-sm text-muted-foreground sm:w-auto">
            <span>
              <Package className="h-4 w-4 inline mr-1" />
              {tree.total_modules} 模块
            </span>
            <span>
              {tree.total_pages} 页面
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">
        {/* Left Sidebar: Version List */}
        <aside className="h-48 w-full shrink-0 overflow-hidden border-b bg-muted/20 lg:h-auto lg:w-64 lg:border-r lg:border-b-0">
          <VersionList
            projectId={0}
            selectedBundleId={selectedBundleId}
            onSelect={handleBundleSelect}
          />
        </aside>

        {/* Main Area */}
        <main className="flex-1 overflow-auto">
          {loading ? (
            <div className="p-6">
              {/* Loading skeleton */}
              <div className="flex gap-4 mb-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex-1 space-y-2">
                    <Skeleton className="h-8 w-32" />
                    <Skeleton className="h-40 w-full" />
                  </div>
                ))}
              </div>
              <Skeleton className="h-32 w-full" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-20">
              <p className="text-destructive mb-3">{error}</p>
              <Button variant="secondary" onClick={loadTree}>
                <RefreshCw className="h-4 w-4 mr-1" /> 重试
              </Button>
            </div>
          ) : !tree || platformNames.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <Package className="h-12 w-12 mb-3 opacity-30" />
              <p className="text-lg font-medium">暂无版本数据</p>
              <p className="text-sm mt-1">
                请先在 ReleaseBundle 详情中导入模块树
              </p>
            </div>
          ) : (
            <div className="space-y-6 p-3 sm:p-6">
              {/* Three-column platform cards */}
              <div
                className={cn(
                  'grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3',
                )}
              >
                {platformNames.map((platform) => (
                  <PlatformCard
                    key={platform}
                    platform={platform}
                    modules={platforms[platform] ?? []}
                    onPageClick={handlePageClick}
                  />
                ))}
              </div>

              {/* Admin Modules */}
              {adminModules.length > 0 && (
                <div
                  className={cn(
                    'grid grid-cols-1 gap-4 md:grid-cols-2',
                  )}
                >
                  <PlatformCard
                    platform="ADMIN"
                    modules={adminModules}
                    onPageClick={handlePageClick}
                  />
                </div>
              )}

              {/* Admin Module Links */}
              <AdminModuleCard bundleId={selectedBundleId} modules={allModules} />
            </div>
          )}
        </main>
      </div>

      {/* Page Interaction Panel (Sheet) */}
      <PageInteractionPanel
        open={interactionPanelOpen}
        onOpenChange={setInteractionPanelOpen}
        page={selectedPage}
        bundleId={selectedBundleId}
      />
    </div>
  )
}
