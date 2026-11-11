import { Badge, Card, CardContent } from '@/ui'

export interface RunDiff {
  fixed: string[]
  regressed: string[]
  still_failing: string[]
  new_assertions: string[]
  total_previous: number
  total_current: number
}

interface RunComparisonProps {
  diff: RunDiff
}

function Section({ title, keys, tone }: { title: string; keys: string[]; tone: 'neutral' | 'success' | 'danger' }) {
  if (keys.length === 0) return null
  return (
    <div className="space-y-1.5">
      <div className="text-sm text-muted-foreground">
        {title}（{keys.length}）
      </div>
      <div className="flex flex-wrap gap-1.5">
        {keys.map((key) => (
          <Badge key={key} tone={tone}>
            {key}
          </Badge>
        ))}
      </div>
    </div>
  )
}

export default function RunComparison({ diff }: RunComparisonProps) {
  const hasChanges =
    diff.fixed.length + diff.regressed.length + diff.still_failing.length + diff.new_assertions.length > 0

  return (
    <Card size="sm" data-testid="run-comparison">
      <div className="text-sm font-medium px-[var(--card-spacing)] pt-[var(--card-spacing)]">
        Run 对比（旧 {diff.total_previous} 条 → 新 {diff.total_current} 条）
      </div>
      <CardContent className="space-y-3">
        {!hasChanges && <p className="text-sm text-muted-foreground">无差异</p>}
        <Section title="已修复" keys={diff.fixed} tone="success" />
        <Section title="回归失败" keys={diff.regressed} tone="danger" />
        <Section title="仍失败" keys={diff.still_failing} tone="neutral" />
        <Section title="新增断言" keys={diff.new_assertions} tone="neutral" />
      </CardContent>
    </Card>
  )
}
