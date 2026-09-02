import { cn } from '@/lib/utils'

interface PageIntroProps {
  title: string
  description: string
  children?: React.ReactNode
  className?: string
}

/** 页面一句话说明（batch-214 B4）：放在 PageHeader 下方，面向测试工程师业务语言。 */
export function PageIntro({ title, description, children, className }: PageIntroProps) {
  return (
    <div className={cn('space-y-1 border-b border-border pb-3', className)}>
      {title && <p className="text-sm font-medium text-foreground">{title}</p>}
      <p className="text-sm text-muted-hc">{description}</p>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  )
}

export default PageIntro
