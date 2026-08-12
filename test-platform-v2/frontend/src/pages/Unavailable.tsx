import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { Construction } from '@/lib/icons'

interface Props {
  title?: string
  description?: string
}

export default function Unavailable({ title = '功能未开放', description = '' }: Props) {
  useDocumentTitle(title)
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <Construction className="size-14 text-muted-foreground/40" />
      <h2 className="mt-4 text-lg font-semibold">{title}</h2>
      {description && <p className="mt-2 max-w-md text-sm text-muted-foreground">{description}</p>}
    </div>
  )
}
