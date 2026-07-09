import { useState } from 'react'
import PageHeader from '@/components/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LayoutDashboard, Database, FileCheck, Search } from '@/lib/icons'
import OverviewTab from './components/OverviewTab'
import SourceListTab from './components/SourceListTab'
import ArtifactReviewTab from './components/ArtifactReviewTab'
import SearchTab from './components/SearchTab'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

/**
 * 知识中心 — RAG 知识图谱与 Agent 持续学习能力（M0 入口 / M1 只读列表 / M2 混合检索）。
 * 概览 / 检索 / 知识源 / AI 审核台 四个 Tab。
 */
export default function KnowledgePage() {
  useDocumentTitle('知识中心')
  const [tab, setTab] = useState('overview')

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
      </Tabs>
    </div>
  )
}
