import { useState } from 'react'
import PageHeader from '@/components/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LayoutDashboard, Database, FileCheck, Search, GitBranch, Layers, Calendar, BookOpen, GitCompare } from '@/lib/icons'
import OverviewTab from './components/OverviewTab'
import SourceListTab from './components/SourceListTab'
import ArtifactReviewTab from './components/ArtifactReviewTab'
import SearchTab from './components/SearchTab'
import GraphTab from './components/GraphTab'
import EntityTab from './components/EntityTab'
import IterationTab from './components/IterationTab'
import WikiTab from './components/WikiTab'
import WikiDiffTab from './components/WikiDiffTab'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

/**
 * 知识中心 — RAG 知识图谱与 Agent 持续学习能力（M0 入口 / M1 只读列表 / M2 混合检索 / M3 图谱可视化 / M6 迭代知识包）。
 * 概览 / 检索 / 知识源 / AI 审核台 / 图谱 / 实体 / 迭代 / Wiki 知识库 / 知识差异对比 九个 Tab。
 */
export default function KnowledgePage() {
  useDocumentTitle('知识中心')
  const initialTab = new URLSearchParams(window.location.search).get('tab') || 'overview'
  const [tab, setTab] = useState(initialTab)

  return (
    <div className="space-y-4">
      <PageHeader
        title="知识中心"
        description="需求 / 接口 / 用例 / 缺陷 / 执行结果统一沉淀为可检索、可追溯、可复用的知识。"
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
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
