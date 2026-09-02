import { useMemo, useState } from 'react'
import { cn } from '@/lib/utils'
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
import { LayoutDashboard, Database, FileCheck, Search, GitBranch, Layers, Calendar, BookOpen, GitCompare, FolderOpen, Sparkles, Zap } from '@/lib/icons'
import type { LucideIcon } from '@/lib/icons'
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
import { useAuthStore } from '@/stores/auth'


/**
 * (batch-212 入口收敛) 知识中心 Tab 目录：普通用户视图只留 项目知识/平台研发/检索 3 Tab；
 * 其余为维护/专家 Tab（来源管理/AI 审核台/图谱/实体/迭代/Wiki 知识库/知识差异对比/Skills/概览），
 * 需知识维护权限才可见（02 白名单 §3「知识中心普通用户多余 Tab 收维护入口」）。
 */
type KnowledgeTabDef = { value: string; label: string; icon: LucideIcon }

const KNOWLEDGE_TAB_DEFS: KnowledgeTabDef[] = [
  { value: 'project', label: '项目知识', icon: FolderOpen },
  { value: 'platform', label: '平台研发', icon: Sparkles },
  { value: 'search', label: '检索', icon: Search },
  { value: 'overview', label: '概览', icon: LayoutDashboard },
  { value: 'sources', label: '知识源', icon: Database },
  { value: 'artifacts', label: 'AI 审核台', icon: FileCheck },
  { value: 'graph', label: '图谱', icon: GitBranch },
  { value: 'entities', label: '实体', icon: Layers },
  { value: 'iterations', label: '迭代', icon: Calendar },
  { value: 'wiki', label: 'Wiki 知识库', icon: BookOpen },
  { value: 'wikidiff', label: '知识差异对比', icon: GitCompare },
  { value: 'skills', label: 'Skills', icon: Zap },
]

const NORMAL_KNOWLEDGE_TABS = new Set(['project', 'platform', 'search'])

function visibleKnowledgeTabs(canMaintain: boolean): KnowledgeTabDef[] {
  if (canMaintain) return KNOWLEDGE_TAB_DEFS
  return KNOWLEDGE_TAB_DEFS.filter((def) => NORMAL_KNOWLEDGE_TABS.has(def.value))
}

/**
 * 知识中心 — PARA 视角（项目知识 / 平台研发） + RAG 技术视图。
 */
export default function KnowledgePage() {
  useDocumentTitle('知识中心')
  const [searchParams, setSearchParams] = useSearchParams()
  // (batch-212 入口收敛) 普通用户默认只读 3 Tab；维护 Tab 需知识维护权限（专家/管理员）。
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const canMaintainKnowledge =
    hasPerm('*') || hasPerm('knowledge:manage') || hasPerm('knowledge:approve') ||
    hasPerm('wiki:manage') || hasPerm('wiki:approve')
  const allowedTabs = useMemo(
    () => visibleKnowledgeTabs(canMaintainKnowledge),
    [canMaintainKnowledge],
  )
  const requestedTab = searchParams.get('tab') || (canMaintainKnowledge ? 'overview' : 'project')
  const tab = allowedTabs.some((def) => def.value === requestedTab)
    ? requestedTab
    : allowedTabs[0].value

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
          {allowedTabs.map((def) => (
          <TabsTrigger key={def.value} value={def.value}>
            <def.icon className="size-4 mr-1" />
            {def.label}
          </TabsTrigger>
        ))}
</TabsList>
        </div>

        <TabsContent value="project" className={cn('mt-4', tab !== 'project' && 'hidden')} forceMount={visitedTabs.has('project') ? true : undefined}>
          <ProjectTab />
        </TabsContent>
        <TabsContent value="platform" className={cn('mt-4', tab !== 'platform' && 'hidden')} forceMount={visitedTabs.has('platform') ? true : undefined}>
          <PlatformTab />
        </TabsContent>
        <TabsContent value="overview" className={cn('mt-4', tab !== 'overview' && 'hidden')} forceMount={visitedTabs.has('overview') ? true : undefined}>
          <OverviewTab />
        </TabsContent>
        <TabsContent value="search" className={cn('mt-4', tab !== 'search' && 'hidden')} forceMount={visitedTabs.has('search') ? true : undefined}>
          <SearchTab />
        </TabsContent>
        <TabsContent value="sources" className={cn('mt-4', tab !== 'sources' && 'hidden')} forceMount={visitedTabs.has('sources') ? true : undefined}>
          <SourceListTab />
        </TabsContent>
        <TabsContent value="artifacts" className={cn('mt-4', tab !== 'artifacts' && 'hidden')} forceMount={visitedTabs.has('artifacts') ? true : undefined}>
          <ArtifactReviewTab />
        </TabsContent>
        <TabsContent value="graph" className={cn('mt-4', tab !== 'graph' && 'hidden')} forceMount={visitedTabs.has('graph') ? true : undefined}>
          <GraphTab />
        </TabsContent>
        <TabsContent value="entities" className={cn('mt-4', tab !== 'entities' && 'hidden')} forceMount={visitedTabs.has('entities') ? true : undefined}>
          <EntityTab />
        </TabsContent>
        <TabsContent value="iterations" className={cn('mt-4', tab !== 'iterations' && 'hidden')} forceMount={visitedTabs.has('iterations') ? true : undefined}>
          <IterationTab />
        </TabsContent>
        <TabsContent value="wiki" className={cn('mt-4', tab !== 'wiki' && 'hidden')} forceMount={visitedTabs.has('wiki') ? true : undefined}>
          <WikiTab />
        </TabsContent>
        <TabsContent value="wikidiff" className={cn('mt-4', tab !== 'wikidiff' && 'hidden')} forceMount={visitedTabs.has('wikidiff') ? true : undefined}>
          <WikiDiffTab />
        </TabsContent>
        <TabsContent value="skills" className={cn('mt-4', tab !== 'skills' && 'hidden')} forceMount={visitedTabs.has('skills') ? true : undefined}>
          <SkillsTab />
        </TabsContent>
      </Tabs>

      {/* 灵感快速捕获浮动按钮 */}
      <CaptureDialog />
    </div>
  )
}
