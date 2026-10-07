import { useMemo, useState } from 'react'
import { cn } from '@/lib/utils'
import { useSearchParams } from 'react-router'
import PageHeader from '@/components/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/ui'
import { Input } from '@/ui'
import { Button } from '@/ui'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/ui'
import { LayoutDashboard, Database, Search, Calendar, BookOpen, FolderOpen, Layers, Target } from '@/lib/icons'
import type { LucideIcon } from '@/lib/icons'
import OverviewTab from './components/OverviewTab'
import SourceListTab from './components/SourceListTab'
import SearchTab from './components/SearchTab'
import WikiTab from './components/WikiTab'
import ProjectTab from './components/ProjectTab'
import VersionKnowledgeTab from './components/VersionKnowledgeTab'
import ImpactTab from './components/ImpactTab'
import CaptureDialog from './components/CaptureDialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { useAuthStore } from '@/stores/auth'


/**
 * 知识中心 Tab 目录（平台简化批次收敛）。
 *
 * 普通用户（tester）视图**恰好 3 Tab**：影响面 / 项目知识 / 检索。
 * 维护/专家 Tab（概览/知识源/版本记录/复用建议/Wiki）需知识维护权限才可见。
 *
 * 平台简化批次：平台研发/图谱/实体/迭代/AI 审核台/知识差异对比/Skills 已随
 * 知识 AI 子能力删除。
 */
type KnowledgeTabDef = { value: string; label: string; icon: LucideIcon }

const KNOWLEDGE_TAB_DEFS: KnowledgeTabDef[] = [
  { value: 'impact', label: '影响面', icon: Target },
  { value: 'project', label: '项目知识', icon: FolderOpen },
  { value: 'versionrecords', label: '版本记录', icon: Calendar },
  { value: 'reuse', label: '复用建议', icon: Layers },
  { value: 'search', label: '检索', icon: Search },
  { value: 'overview', label: '概览', icon: LayoutDashboard },
  { value: 'sources', label: '知识源', icon: Database },
  { value: 'wiki', label: 'Wiki 知识库', icon: BookOpen },
]

/** 普通用户可见页签上限与清单（Batch 260 / B3-5：收敛到 3 个，与上面的 docblock 一致）。 */
export const NORMAL_TAB_LIMIT = 3
export const NORMAL_KNOWLEDGE_TABS = new Set(['impact', 'project', 'search'])

function visibleKnowledgeTabs(canMaintain: boolean): KnowledgeTabDef[] {
  if (canMaintain) return KNOWLEDGE_TAB_DEFS
  return KNOWLEDGE_TAB_DEFS.filter((def) => NORMAL_KNOWLEDGE_TABS.has(def.value))
}

/**
 * 知识中心 — 项目知识库（知识源/检索/版本记录/复用建议/影响面）。
 */
export default function KnowledgePage() {
  useDocumentTitle('知识中心')
  const [searchParams, setSearchParams] = useSearchParams()
  // (Batch 260 / B3-5) 普通用户只读 3 Tab，默认落在「影响面」（09 §2.4 的知识主线）；
  // 维护 Tab 需知识维护权限（专家/管理员）。
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const canMaintainKnowledge =
    hasPerm('*') || hasPerm('knowledge:manage') || hasPerm('knowledge:approve') ||
    hasPerm('wiki:manage') || hasPerm('wiki:approve')
  const allowedTabs = useMemo(
    () => visibleKnowledgeTabs(canMaintainKnowledge),
    [canMaintainKnowledge],
  )
  const requestedTab = searchParams.get('tab') || (canMaintainKnowledge ? 'overview' : 'impact')
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
        description="项目知识（需求/接口/用例）统一沉淀、可检索、可复用。"
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

        <TabsContent value="impact" className={cn('mt-4', tab !== 'impact' && 'hidden')} forceMount={visitedTabs.has('impact') ? true : undefined}>
          <ImpactTab />
        </TabsContent>
        <TabsContent value="project" className={cn('mt-4', tab !== 'project' && 'hidden')} forceMount={visitedTabs.has('project') ? true : undefined}>
          <ProjectTab />
        </TabsContent>
        <TabsContent value="versionrecords" className={cn('mt-4', tab !== 'versionrecords' && 'hidden')} forceMount={visitedTabs.has('versionrecords') ? true : undefined}>
          <VersionKnowledgeTab mode="records" />
        </TabsContent>
        <TabsContent value="reuse" className={cn('mt-4', tab !== 'reuse' && 'hidden')} forceMount={visitedTabs.has('reuse') ? true : undefined}>
          <VersionKnowledgeTab mode="reuse" />
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
        <TabsContent value="wiki" className={cn('mt-4', tab !== 'wiki' && 'hidden')} forceMount={visitedTabs.has('wiki') ? true : undefined}>
          <WikiTab />
        </TabsContent>
      </Tabs>

      {/* 灵感快速捕获浮动按钮 */}
      <CaptureDialog />
    </div>
  )
}
