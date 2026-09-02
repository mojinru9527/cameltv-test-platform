import { useState } from 'react'
import { useLocation } from 'react-router'
import { Button } from '@/ui'
import { MessageSquare, Sparkles } from '@/lib/icons'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/dialog'
import { getExplanation } from '@/lib/page-explanations'
import { cn } from '@/lib/utils'

interface AskAiButtonProps {
  className?: string
}

/** 「问我」助手 MVP（batch-214 B4）：按路由返回业务语言解释 + 常见动作。 */
export function AskAiButton({ className }: AskAiButtonProps) {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const exp = getExplanation(location.pathname)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn('gap-1.5 text-muted-foreground', className)}
          aria-label="问我这页怎么用"
        >
          <MessageSquare className="size-4" />
          <span className="hidden sm:inline">问我</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <Sparkles className="size-4 text-primary" aria-hidden="true" />
            {exp.title}
          </DialogTitle>
          <DialogDescription className="text-left">{exp.description}</DialogDescription>
        </DialogHeader>
        <div className="space-y-1 text-sm">
          <p className="text-xs font-medium text-foreground">你可以：</p>
          <ul className="list-disc pl-5 text-xs text-muted-hc">
            {exp.actions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="secondary" size="sm">
              关闭
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default AskAiButton

