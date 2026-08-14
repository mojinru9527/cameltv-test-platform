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
    <div className="space-y-4 mb-4">
      {/* Batch 180（FIX-173-P3-01/02）：严重度/状态分两行展示，标签与表格统一
          「P0-致命」连字符风格；消除 四卡维度混排（3+7+1≠8）的误导。 */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          icon={Bug}
          label="缺陷总数"
          value={stats.total}
          variant="glass"
        />
        <StatCard
          icon={AlertTriangle}
          label="P0-致命"
          value={stats.by_severity?.P0 || 0}
          trendUp={false}
          variant="glass"
        />
        <StatCard
          icon={AlertTriangle}
          label="P1-严重"
          value={stats.by_severity?.P1 || 0}
          trendUp={false}
          variant="glass"
        />
        <StatCard
          icon={AlertTriangle}
          label="P2-一般"
          value={(stats.by_severity?.P2 || 0) + (stats.by_severity?.P3 || 0)}
          trendUp={false}
          variant="glass"
        />
      </div>
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          icon={Clock}
          label="待处理"
          value={stats.by_status?.open || 0}
          trendUp={false}
          variant="glass"
        />
        <StatCard
          icon={Clock}
          label="已确认"
          value={(stats.by_status?.confirmed || 0) + (stats.by_status?.fixing || 0) + (stats.by_status?.pending_review || 0)}
          trendUp={false}
          variant="glass"
        />
        <StatCard
          icon={CheckCircle2}
          label="已关闭"
          value={(stats.by_status?.closed || 0) + (stats.by_status?.rejected || 0)}
          trendUp={true}
          variant="glass"
        />
      </div>
    </div>
  )
}
