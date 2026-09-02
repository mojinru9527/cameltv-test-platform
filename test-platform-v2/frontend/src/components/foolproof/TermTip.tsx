import { Info } from '@/lib/icons'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { getTerm } from '@/lib/terminology'
import { cn } from '@/lib/utils'

interface TermTipProps {
  term: string
  children?: React.ReactNode
  className?: string
}

/** 术语提示（batch-214 B4）：悬停引擎词显示业务解释，词表来自 terminology.ts。 */
export function TermTip({ term, className, children }: TermTipProps) {
  const entry = getTerm(term)
  if (!entry) return <>{children ?? term}</>
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={cn(
              'inline-flex cursor-help items-center gap-1 underline decoration-dotted underline-offset-2',
              className,
            )}
          >
            {children ?? entry.label}
            <Info className="size-3.5 text-muted-foreground" aria-hidden="true" />
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-md text-xs">
          <div className="font-medium text-foreground">{entry.label}</div>
          <div className="text-muted-hc">{entry.explanation}</div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

export default TermTip
