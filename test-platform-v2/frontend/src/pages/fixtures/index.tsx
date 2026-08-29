import { useState } from 'react'
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { FixtureView } from '@/components/data/FixtureView'

export default function FixturesPage() {
  useDocumentTitle('Fixture')
  const [fixtureId, setFixtureId] = useState<number>(0)

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold tracking-[-0.02em]">Fixture 查看</h2>
      <Card>
        <CardHeader>
          <CardTitle>输入 Fixture ID</CardTitle>
        </CardHeader>
        <CardContent className="flex items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium">Fixture ID</label>
            <Input
              type="number"
              value={fixtureId || ''}
              onChange={(e) => setFixtureId(Number(e.target.value))}
              placeholder="例如 1"
            />
          </div>
          <Button onClick={() => setFixtureId((v) => v)} disabled={!fixtureId}>查看</Button>
        </CardContent>
      </Card>
      {fixtureId > 0 && <FixtureView fixtureId={fixtureId} />}
    </div>
  )
}
