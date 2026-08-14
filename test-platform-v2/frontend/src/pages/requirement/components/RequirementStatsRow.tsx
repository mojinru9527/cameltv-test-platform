import StatCard from '@/components/StatCard'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/ui'
import { BookOpen, Layers, Sparkles } from '@/lib/icons'

interface Props {
  totalDocuments: number
  domainCount: number
  totalModules: number
  coverage: number
  isCoverageLoading: boolean
  isCoverageRefetching: boolean
  activeDocId: number | null
  importedCaseCount: number
}

export default function RequirementStatsRow({
  totalDocuments,
  domainCount,
  totalModules,
  coverage,
  isCoverageLoading,
  isCoverageRefetching,
  activeDocId,
  importedCaseCount,
}: Props) {
  return (
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
        value={domainCount}
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
        value={importedCaseCount}
        variant="glass"
      />
    </div>
  )
}
