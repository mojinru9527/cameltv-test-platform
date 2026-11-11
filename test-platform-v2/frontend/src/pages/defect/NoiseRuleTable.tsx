import { Badge, Card, CardContent } from '@/ui'

export interface NoiseRuleItem {
  id: number
  pattern: string
  action: string
  scope?: string
  expires_at: string
  status: string
}

const ACTION_LABEL: Record<string, string> = {
  suppress: '抑制',
  hint: '提示',
  quarantine: '隔离',
}

function isExpired(rule: NoiseRuleItem) {
  return rule.status !== 'active' || new Date(rule.expires_at).getTime() <= Date.now()
}

export default function NoiseRuleTable({ rules }: { rules: NoiseRuleItem[] }) {
  if (rules.length === 0) {
    return (
      <Card size="sm">
        <CardContent>
          <p className="text-sm text-muted-foreground">暂无噪音抑制规则</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card size="sm">
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="p-3 font-medium">规则</th>
              <th className="p-3 font-medium">动作</th>
              <th className="p-3 font-medium">到期时间</th>
              <th className="p-3 font-medium">状态</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr key={rule.id} className="border-b last:border-0">
                <td className="p-3">{rule.pattern}</td>
                <td className="p-3">{ACTION_LABEL[rule.action] ?? rule.action}</td>
                <td className="p-3 font-mono text-xs">{rule.expires_at}</td>
                <td className="p-3">
                  <Badge tone={isExpired(rule) ? 'neutral' : 'success'}>
                    {isExpired(rule) ? '待复核' : '生效中'}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}
