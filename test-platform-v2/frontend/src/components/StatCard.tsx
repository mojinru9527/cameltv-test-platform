import type { LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatCardProps {
  icon: LucideIcon
  label: string
  value: string | number
  /** Optional trend indicator like "+12%" or "-3%" */
  trend?: string
  trendUp?: boolean
  className?: string
  variant?: 'default' | 'glass'
}

export default function StatCard({ icon: Icon, label, value, trend, trendUp, className, variant = 'default' }: StatCardProps) {
  return (
    <Card
      size="sm"
      className={cn(
        variant === 'default' ? 'card-lift' : 'glass-card',
        className,
      )}
    >
      <CardContent className="flex items-center gap-4 py-4">
        <div className="stat-card-icon">
          <Icon className="size-5" />
        </div>
        <div className="flex flex-col min-w-0">
          <span className="text-xs text-muted-hc truncate">{label}</span>
          <span className="text-xl font-bold tracking-tight">{value}</span>
          {trend && (
            <span
              className={cn(
                'text-xs mt-0.5 font-medium',
                trendUp === true && 'text-green-600 dark:text-green-400',
                trendUp === false && 'text-destructive',
                trendUp == null && 'text-muted-foreground',
              )}
            >
              {trend}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
