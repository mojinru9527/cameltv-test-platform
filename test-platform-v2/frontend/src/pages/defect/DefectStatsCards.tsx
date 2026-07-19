import { AlertTriangle, Bug, CheckCircle2, Clock } from '@/lib/icons'
import StatCard from '@/components/StatCard'

interface DefectStats {
  total: number
  by_severity: Record<string, number>
  by_status: Record<string, number>
}

interface DefectStatsCardsProps {
  stats: DefectStats
}

export default function DefectStatsCards({ stats }: DefectStatsCardsProps) {
  return (
    <div className="grid grid-cols-4 gap-4 mb-4">
      <StatCard
        icon={Bug}
        label="缺陷总数"
        value={stats.total}
        variant="glass"
      />
      <StatCard
        icon={AlertTriangle}
        label="P0 致命"
        value={stats.by_severity?.P0 || 0}
        trendUp={false}
        variant="glass"
      />
      <StatCard
        icon={Clock}
        label="待处理"
        value={stats.by_status?.open || 0}
        trendUp={false}
        variant="glass"
      />
      <StatCard
        icon={CheckCircle2}
        label="已解决"
        value={(stats.by_status?.resolved || 0) + (stats.by_status?.closed || 0)}
        trendUp={true}
        variant="glass"
      />
    </div>
  )
}
