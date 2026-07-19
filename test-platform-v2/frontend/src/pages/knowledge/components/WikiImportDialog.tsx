import { useState } from 'react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import LanhuEvidenceDialog from './LanhuEvidenceDialog'
import LanhuEvidenceJobDrawer from './LanhuEvidenceJobDrawer'

interface Props {
  open: boolean
  onOpenChange: (v: boolean) => void
  // Retained for caller compatibility; imports now finish asynchronously in
  // the evidence job drawer after the quality gate opens.
  onImported?: (result: unknown) => void
}

export default function WikiImportDialog({ open, onOpenChange }: Props) {
  const [url, setUrl] = useState('')
  const [ingestKnowledge, setIngestKnowledge] = useState(true)
  const [buildWiki, setBuildWiki] = useState(true)
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const [drawerJobId, setDrawerJobId] = useState<number | null>(null)

  const reset = () => {
    setUrl('')
    setIngestKnowledge(true)
    setBuildWiki(true)
  }

  const submit = () => {
    if (!url.trim()) {
      toast.warning('请输入蓝湖链接')
      return
    }
    setEvidenceOpen(true)
  }

  return (
    <>
      <Dialog open={open} onOpenChange={(nextOpen) => {
        if (!nextOpen) reset()
        onOpenChange(nextOpen)
      }}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader>
            <DialogTitle>导入蓝湖需求</DialogTitle>
            <DialogDescription>
              蓝湖内容必须先完成全页面截图、OCR 与质量审核，达标后才能进入 RAG 或 Wiki。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="lanhu-url">蓝湖设计稿页面链接</Label>
              <Input
                id="lanhu-url"
                placeholder="https://lanhuapp.com/web/#/item/project/...&docId=...&pageId=..."
                value={url}
                onChange={(event) => setUrl(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="t-ingest" className="font-normal">质量达标后同步到 RAG 知识库</Label>
                <Switch
                  id="t-ingest"
                  checked={ingestKnowledge}
                  onCheckedChange={setIngestKnowledge}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="t-wiki" className="font-normal">质量达标后生成 Wiki 原始来源</Label>
                <Switch id="t-wiki" checked={buildWiki} onCheckedChange={setBuildWiki} />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>关闭</Button>
            <Button disabled={!url.trim()} onClick={submit}>创建证据任务</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <LanhuEvidenceDialog
        open={evidenceOpen}
        onOpenChange={setEvidenceOpen}
        initialUrl={url}
        initialImportKnowledge={ingestKnowledge}
        initialImportWiki={buildWiki}
        onCreated={(job) => setDrawerJobId(job.id)}
      />
      <LanhuEvidenceJobDrawer
        open={drawerJobId != null}
        onOpenChange={(nextOpen) => { if (!nextOpen) setDrawerJobId(null) }}
        jobId={drawerJobId}
      />
    </>
  )
}
