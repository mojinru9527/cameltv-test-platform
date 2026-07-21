import { useSearchParams } from 'react-router-dom'
import PageHeader from '@/components/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LayoutDashboard, Database, FileCheck, Search, GitBranch, Layers, Calendar, BookOpen, GitCompare, FolderOpen, Sparkles } from '@/lib/icons'
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
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

/**
 * 知识中心 — PARA 视角（项目知识 / 平台研发） + RAG 技术视图。
 */
export default function KnowledgePage() {
  useDocumentTitle('知识中心')
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'project'

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value })
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="知识中心"
        description="项目知识（需求/接口/用例）+ 平台研发知识（踩坑记录/设计决策/最佳实践）统一沉淀、可检索、可复用。"
      />

      <Tabs value={tab} onValueChange={handleTabChange}>
        <TabsList className="overflow-x-auto flex-nowrap">
          <TabsTrigger value="project">
            <FolderOpen className="size-4 mr-1" />
            项目知识
          </TabsTrigger>
          <TabsTrigger value="platform">
            <Sparkles className="size-4 mr-1" />
            平台研发
          </TabsTrigger>
          <TabsTrigger value="overview">
            <LayoutDashboard className="size-4 mr-1" />
            概览
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
        </TabsList>

        <TabsContent value="project" className="mt-4">
          {tab === 'project' && <ProjectTab />}
        </TabsContent>
        <TabsContent value="platform" className="mt-4">
          {tab === 'platform' && <PlatformTab />}
        </TabsContent>
        <TabsContent value="overview" className="mt-4">
          {tab === 'overview' && <OverviewTab />}
        </TabsContent>
        <TabsContent value="search" className="mt-4">
          {tab === 'search' && <SearchTab />}
        </TabsContent>
        <TabsContent value="sources" className="mt-4">
          {tab === 'sources' && <SourceListTab />}
        </TabsContent>
        <TabsContent value="artifacts" className="mt-4">
          {tab === 'artifacts' && <ArtifactReviewTab />}
        </TabsContent>
        <TabsContent value="graph" className="mt-4">
          {tab === 'graph' && <GraphTab />}
        </TabsContent>
        <TabsContent value="entities" className="mt-4">
          {tab === 'entities' && <EntityTab />}
        </TabsContent>
        <TabsContent value="iterations" className="mt-4">
          {tab === 'iterations' && <IterationTab />}
        </TabsContent>
        <TabsContent value="wiki" className="mt-4">
          {tab === 'wiki' && <WikiTab />}
        </TabsContent>
        <TabsContent value="wikidiff" className="mt-4">
          {tab === 'wikidiff' && <WikiDiffTab />}
        </TabsContent>
      </Tabs>
    </div>
  )
}
