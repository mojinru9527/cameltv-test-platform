import { Construction } from '@/lib/icons'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export default function Placeholder({ title }: { title: string }) {
  useDocumentTitle(title)
  return (
    <div>
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="flex flex-col items-center justify-center py-20">
        <Construction className="size-16 text-muted-foreground/40" />
        <p className="mt-4 text-sm text-muted-foreground">
          「{title}」模块建设中（后续阶段实现）
        </p>
      </div>
    </div>
  )
}
