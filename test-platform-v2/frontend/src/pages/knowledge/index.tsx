import { useState } from 'react'
import { useSearchParams } from 'react-router'
import PageHeader from '@/components/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/ui'
import { Button } from '@/ui'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { LayoutDashboard, Database, FileCheck, Search, GitBranch, Layers, Calendar, BookOpen, GitCompare, FolderOpen, Sparkles, Zap, Lightbulb } from '@/lib/icons'
import OverviewTab from './components/OverviewTab'
import SourceListTab from './components/SourceListTab'
import ArtifactReviewTab from './components/ArtifactReviewTab'
import SearchTab from './components/SearchTab'
import GraphTab from './components/GraphTab'
import EntityTab from './components/EntityTab'
import IterationTab from './components/IterationTab'
import WikiTab from './components/WikiTab'
import WikiDiffTab from './components/WikiDiffTab'
import ProjectTab from './components/ProjectTab'
import PlatformTab from './components/PlatformTab'
import SkillsTab from './components/SkillsTab'
import CaptureDialog from './components/CaptureDialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

/**
 * 知识中心 — PARA 视角（项目知识 / 平台研发） + RAG 技术视图。
 */
export default function KnowledgePage() {
  useDocumentTitle('知识中心')
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'overview'

  // ── 常驻搜索栏状态 ──
  const [searchQuery, setSearchQuery] = useState('')
  const [searchMode, setSearchMode] = useState('hybrid')

  const [visitedTabs, setVisitedTabs] = useState<Set<string>>(new Set([tab]))

  const handleTabChange = (value: string) => {
    setVisitedTabs((prev) => new Set(prev).add(value))
    setSearchParams({ tab: value })
  }

  const handleSearch = () => {
    const q = searchQuery.trim()
    if (!q) return
    setSearchParams({ tab: 'search', q, mode: searchMode })
  }

  return (
    <div className="min-w-0 space-y-4">
      <PageHeader
        title="知识中心"
        description="项目知识（需求/接口/用例）+ 平台研发知识（踩坑记录/设计决策/最佳实践）统一沉淀、可检索、可复用。"
      />

      {/* ── 常驻搜索栏（所有 Tab 可见）── */}
      <div className="flex flex-col gap-2 px-1 py-1 sm:flex-row sm:items-center">
        <div className="relative min-w-0 flex-1">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            className="pl-8 h-9"
            placeholder="检索全部知识库（含审核通过/驳回/弃用的切片）"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSearch() }}
          />
        </div>
        <Select value={searchMode} onValueChange={setSearchMode}>
          <SelectTrigger
            className="h-9 w-full text-xs sm:w-[180px]"
            aria-label="知识检索方式"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="hybrid">混合（关键词+向量）</SelectItem>
            <SelectItem value="keyword">关键词</SelectItem>
            <SelectItem value="vector">向量语义</SelectItem>
          </SelectContent>
        </Select>
        <Button size="sm" className="h-9 w-full sm:w-auto" disabled={!searchQuery.trim()} onClick={handleSearch}>
          搜索
        </Button>
      </div>

      <Tabs value={tab} onValueChange={handleTabChange}>
        <div className="pb-1">
        <TabsList
          className="!h-auto w-full flex-wrap items-start justify-start gap-y-1"
          aria-label="知识中心功能页签"
        >
          <TabsTrigger value="overview">
            <LayoutDashboard className="size-4 mr-1" />
            概览
          </TabsTrigger>
          <TabsTrigger value="project">
            <FolderOpen className="size-4 mr-1" />
            项目知识
          </TabsTrigger>
          <TabsTrigger value="platform">
            <Sparkles className="size-4 mr-1" />
            平台研发
          </TabsTrigger>
          <TabsTrigger value="search">
            <Search className="size-4 mr-1" />
            检索
          </TabsTrigger>
          <TabsTrigger value="sources">
            <Database className="size-4 mr-1" />
            知识源
          </TabsTrigger>
          <TabsTrigger value="artifacts">
            <FileCheck className="size-4 mr-1" />
            AI 审核台
          </TabsTrigger>
          <TabsTrigger value="graph">
            <GitBranch className="size-4 mr-1" />
            图谱
          </TabsTrigger>
          <TabsTrigger value="entities">
            <Layers className="size-4 mr-1" />
            实体
          </TabsTrigger>
          <TabsTrigger value="iterations">
            <Calendar className="size-4 mr-1" />
            迭代
          </TabsTrigger>
          <TabsTrigger value="wiki">
            <BookOpen className="size-4 mr-1" />
            Wiki 知识库
          </TabsTrigger>
          <TabsTrigger value="wikidiff">
            <GitCompare className="size-4 mr-1" />
            知识差异对比
          </TabsTrigger>
          <TabsTrigger value="skills">
            <Zap className="size-4 mr-1" />
            Skills
          </TabsTrigger>
        </TabsList>
        </div>

        <TabsContent value="project" className="mt-4" forceMount={visitedTabs.has('project') ? true : undefined}>
          <ProjectTab />
        </TabsContent>
        <TabsContent value="platform" className="mt-4" forceMount={visitedTabs.has('platform') ? true : undefined}>
          <PlatformTab />
        </TabsContent>
        <TabsContent value="overview" className="mt-4" forceMount={visitedTabs.has('overview') ? true : undefined}>
          <OverviewTab />
        </TabsContent>
        <TabsContent value="search" className="mt-4" forceMount={visitedTabs.has('search') ? true : undefined}>
          <SearchTab />
        </TabsContent>
        <TabsContent value="sources" className="mt-4" forceMount={visitedTabs.has('sources') ? true : undefined}>
          <SourceListTab />
        </TabsContent>
        <TabsContent value="artifacts" className="mt-4" forceMount={visitedTabs.has('artifacts') ? true : undefined}>
          <ArtifactReviewTab />
        </TabsContent>
        <TabsContent value="graph" className="mt-4" forceMount={visitedTabs.has('graph') ? true : undefined}>
          <GraphTab />
        </TabsContent>
        <TabsContent value="entities" className="mt-4" forceMount={visitedTabs.has('entities') ? true : undefined}>
          <EntityTab />
        </TabsContent>
        <TabsContent value="iterations" className="mt-4" forceMount={visitedTabs.has('iterations') ? true : undefined}>
          <IterationTab />
        </TabsContent>
        <TabsContent value="wiki" className="mt-4" forceMount={visitedTabs.has('wiki') ? true : undefined}>
          <WikiTab />
        </TabsContent>
        <TabsContent value="wikidiff" className="mt-4" forceMount={visitedTabs.has('wikidiff') ? true : undefined}>
          <WikiDiffTab />
        </TabsContent>
        <TabsContent value="skills" className="mt-4" forceMount={visitedTabs.has('skills') ? true : undefined}>
          <SkillsTab />
        </TabsContent>
      </Tabs>

      {/* 灵感快速捕获浮动按钮 */}
      <CaptureDialog />
    </div>
  )
}
