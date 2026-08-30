import { Badge } from '@/ui'

const ZONE_LABELS: Record<string, string> = {
  OFFICE: '办公网',
  TEST: '测试网',
  PROD_RO: '生产(只读)',
}

export function NetworkZoneBadge({ zone }: { zone: string }) {
  const tones: Record<string, 'default' | 'secondary' | 'destructive'> = {
    OFFICE: 'secondary',
    TEST: 'default',
    PROD_RO: 'destructive',
  }
  return <Badge variant={tones[zone] ?? 'secondary'}>{ZONE_LABELS[zone] ?? zone}</Badge>
}
