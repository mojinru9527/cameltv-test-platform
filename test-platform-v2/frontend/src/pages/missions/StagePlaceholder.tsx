import { useParams } from 'react-router'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export default function StagePlaceholder({ title }: { title: string }) {
  const { id } = useParams()
  useDocumentTitle(title)
  return (
    <div className="rounded-lg border border-dashed bg-card p-10 text-center">
      <p className="text-lg font-medium">{title}</p>
      <p className="mt-2 text-sm text-muted-foreground">
        该阶段（Mission #{id}）即将在后续版本开放。
      </p>
    </div>
  )
}
