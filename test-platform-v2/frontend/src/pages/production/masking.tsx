import { useState } from 'react'
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/ui'
import PageHeader from '@/components/PageHeader'
import type { MaskingProfile } from '@/api/production'
import { ProdReadOnlyBanner } from './components/ProdReadOnlyBanner'
import { MaskingProfilePanel } from './components/MaskingProfilePanel'
import { ShieldCheck } from '@/lib/icons'

/**
 * /admin/masking — masking profiles + rules composer.
 * Backend persistence endpoints for masking profiles are not part of the V36
 * contract, so profiles are composed and listed in-page.
 */
export default function ProductionMaskingPage() {
  const [profiles, setProfiles] = useState<MaskingProfile[]>([])

  const handleSave = (profile: MaskingProfile) => {
    setProfiles((prev) => [profile, ...prev.filter((p) => p.id !== profile.id)])
  }

  return (
    <div className="space-y-4">
      <ProdReadOnlyBanner />
      <PageHeader title="脱敏配置" description="创建 masking profile 与规则（V36-013/014）" />
      <MaskingProfilePanel onSave={handleSave} />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="size-4" /> 已保存配置
            <Badge tone="neutral">{profiles.length}</Badge>
          </CardTitle>
          <CardDescription>本页保存的 masking profile 列表。</CardDescription>
        </CardHeader>
        <CardContent>
          {profiles.length === 0 ? (
            <p className="text-sm text-muted-foreground">尚未保存配置。</p>
          ) : (
            <div className="space-y-2">
              {profiles.map((profile) => (
                <div key={profile.id} className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2 text-sm">
                  <span className="font-medium">{profile.name}</span>
                  <Badge tone="neutral">{profile.rules.length} 规则</Badge>
                  {profile.description && (
                    <span className="text-muted-foreground">{profile.description}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
