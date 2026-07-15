import { useEffect, useState } from 'react'
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
import { createLanhuEvidenceJob } from '@/api/lanhuEvidence'
import type { LanhuEvidenceJob } from '@/api/lanhuEvidence'
import { Loader2 } from '@/lib/icons'
import { useAuthStore } from '@/stores/auth'

interface Props {
  open: boolean
  onOpenChange: (v: boolean) => void
  initialUrl?: string
  initialImportRequirement?: boolean
  initialImportKnowledge?: boolean
  initialImportWiki?: boolean
  onCreated?: (job: LanhuEvidenceJob) => void
}

/**
 * 证据包 OCR 导入对话框 —— 提交蓝湖链接启动全页面截图 + OCR 采集任务。
 * 纯操作型 UI（无营销文案）：链接 + 采集/导出/导入开关。
 */
export default function LanhuEvidenceDialog({
  open,
  onOpenChange,
  initialUrl,
  initialImportRequirement = false,
  initialImportKnowledge = false,
  initialImportWiki = false,
  onCreated,
}: Props) {
  const canImport = useAuthStore((state) => state.hasPerm('lanhu_evidence:import'))
  const [url, setUrl] = useState(initialUrl || '')
  const [captureAll, setCaptureAll] = useState(true)
  const [includeWord, setIncludeWord] = useState(true)
  const [includeJson, setIncludeJson] = useState(true)
  const [importRequirement, setImportRequirement] = useState(false)
  const [importKnowledge, setImportKnowledge] = useState(false)
  const [importWiki, setImportWiki] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open) {
      setUrl(initialUrl || '')
      setImportRequirement(initialImportRequirement)
      setImportKnowledge(initialImportKnowledge)
      setImportWiki(initialImportWiki)
    }
  }, [
    open,
    initialUrl,
    initialImportRequirement,
    initialImportKnowledge,
    initialImportWiki,
  ])

  const submit = () => {
    const u = url.trim()
    if (!u) {
      toast.warning('请输入蓝湖链接')
      return
    }
    setLoading(true)
    createLanhuEvidenceJob({
      url: u,
      capture_all_pages: captureAll,
      include_word: includeWord,
      include_json: includeJson,
      import_to_requirement: canImport && importRequirement,
      import_to_knowledge: canImport && importKnowledge,
      import_to_wiki: canImport && importWiki,
    })
      .then((job) => {
        toast.success(`证据包任务已创建 #${job.id}`)
        onCreated?.(job)
        onOpenChange(false)
      })
      .catch((e) => toast.error(e?.message || '创建失败（需启用 lanhu_evidence 且有 lanhu_evidence:run 权限）'))
      .finally(() => setLoading(false))
  }

  const rows: Array<[string, string, boolean, (v: boolean) => void]> = [
    ['ev-all', '发现并采集全部页面', captureAll, setCaptureAll],
    ['ev-word', '生成 Word 文档', includeWord, setIncludeWord],
    ['ev-json', '生成结构化 JSON', includeJson, setIncludeJson],
    ...(canImport ? [
      ['ev-req', '完成后导入需求文档', importRequirement, setImportRequirement],
      ['ev-rag', '完成后导入 RAG 知识库', importKnowledge, setImportKnowledge],
      ['ev-wiki', '完成后导入 Wiki', importWiki, setImportWiki],
    ] as Array<[string, string, boolean, (v: boolean) => void]> : []),
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>证据包 OCR 导入</DialogTitle>
          <DialogDescription>
            对蓝湖链接下的全部页面滚动截图并 OCR，生成可追溯的证据包（Word + JSON），再入需求 / RAG / Wiki。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="ev-url">蓝湖设计稿链接</Label>
            <Input
              id="ev-url"
              placeholder="https://lanhuapp.com/web/#/item/project/...&docId=...&pageId=..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            {rows.map(([id, label, checked, setter]) => (
              <div key={id} className="flex items-center justify-between">
                <Label htmlFor={id} className="font-normal">{label}</Label>
                <Switch id={id} checked={checked} onCheckedChange={setter} />
              </div>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>关闭</Button>
          <Button disabled={loading || !url.trim()} onClick={submit}>
            {loading ? <Loader2 className="size-4 animate-spin mr-1" /> : null}
            开始采集
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
