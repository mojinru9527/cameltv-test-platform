import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { captureInsight } from '@/api/knowledge'
import { Plus, X, Loader2, Lightbulb } from '@/lib/icons'
import { toast } from 'sonner'

interface CaptureDialogProps {
  onCaptured?: () => void
}

export default function CaptureDialog({ onCaptured }: CaptureDialogProps) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  const addTag = () => {
    const t = tagInput.trim()
    if (t && !tags.includes(t)) {
      setTags([...tags, t])
    }
    setTagInput('')
  }

  const removeTag = (t: string) => {
    setTags(tags.filter((tag) => tag !== t))
  }

  const handleSubmit = async () => {
    if (!title.trim() || !content.trim()) return
    setSubmitting(true)
    try {
      await captureInsight({
        title: title.trim(),
        content: content.trim(),
        source_url: sourceUrl.trim() || undefined,
        tags: tags.length > 0 ? tags : undefined,
      })
      toast.success('灵感已捕获！已放入 Inbox，AI 将自动加工')
      setTitle('')
      setContent('')
      setSourceUrl('')
      setTags([])
      setOpen(false)
      onCaptured?.()
    } catch (e: any) {
      toast.error(e?.message || '捕获失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          size="sm"
          className="fixed bottom-6 right-6 z-50 shadow-lg rounded-full h-12 w-12 p-0"
          title="快速捕获灵感"
        >
          <Plus className="size-5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lightbulb className="size-5 text-yellow-500" />
            灵感快速捕获
          </DialogTitle>
          <DialogDescription>
            捕捉想法、链接、代码片段——自动入库，AI 后续加工分类
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 pt-2">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              标题 <span className="text-red-500">*</span>
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="简短描述你的想法…"
              maxLength={200}
            />
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              内容 <span className="text-red-500">*</span>
            </label>
            <textarea
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="详细内容、上下文、你的思考…"
              rows={5}
              maxLength={5000}
            />
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              来源链接
            </label>
            <Input
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://... (选填)"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">
              标签
            </label>
            <div className="flex items-center gap-1 mb-1.5 flex-wrap">
              {tags.map((t) => (
                <Badge key={t} variant="secondary" className="gap-1 pr-1">
                  {t}
                  <button
                    onClick={() => removeTag(t)}
                    className="hover:text-red-500 transition-colors"
                  >
                    <X className="size-3" />
                  </button>
                </Badge>
              ))}
            </div>
            <div className="flex gap-1">
              <Input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addTag()
                  }
                }}
                placeholder="输入标签后回车"
                className="h-8 text-xs"
              />
              <Button variant="outline" size="sm" onClick={addTag} className="h-8 text-xs">
                添加
              </Button>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={() => setOpen(false)}>
            取消
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!title.trim() || !content.trim() || submitting}
          >
            {submitting ? (
              <>
                <Loader2 className="size-4 mr-1 animate-spin" />
                捕获中…
              </>
            ) : (
              '捕获灵感'
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
