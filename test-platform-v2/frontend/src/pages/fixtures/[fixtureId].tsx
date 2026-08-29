import { useParams } from 'react-router'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { FixtureView } from '@/components/data/FixtureView'

export default function FixtureDetailPage() {
  const { fixtureId } = useParams()
  const id = Number(fixtureId)
  useDocumentTitle(`Fixture #${id}`)

  if (!id) return <p className="text-sm text-muted-foreground">无效的 Fixture ID</p>
  return <FixtureView fixtureId={id} />
}
