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
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { importLanhu } from '@/api/wiki'
import type { LanhuImportResult } from '@/types'
import { Loader2, AlertCircle, CheckCircle2 } from '@/lib/icons'
import LanhuEvidenceDialog from './LanhuEvidenceDialog'
import LanhuEvidenceJobDrawer from './LanhuEvidenceJobDrawer'

// 蓝湖提取状态 → 前端提示（对齐落地方案 §6.1 状态表）
const STATUS_HINT: Record<string, { ok: boolean; label: string }> = {
  success: { ok: true, label: '提取成功，可入库、可生成 Wiki' },
  partial: { ok: true, label: '部分页面无文本，已入库（建议补充说明）' },
  image_only: { ok: false, label: '原型为图片无法提取文本，请填写补充说明后重试' },
  auth_failed: { ok: false, label: '蓝湖登录态失效，请检查账号 / Cookie / MCP 配置' },
  permission_denied: { ok: false, label: '无项目权限，请联系设计 / 产品开权限' },
  invalid_url: { ok: false, label: '链接缺少 docId/pageId，请复制具体设计稿页面链接' },
  failed: { ok: false, label: '提取失败，请稍后重试或联系管理员' },
}

interface Props {
  open: boolean
  onOpenChange: (v: boolean) => void
  onImported?: (r: LanhuImportResult) => void
}

export default function WikiImportDialog({ open, onOpenChange, onImported }: Props) {
  const [url, setUrl] = useState('')
  const [description, setDescription] = useState('')
  const [ingestKnowledge, setIngestKnowledge] = useState(true)
  const [buildWiki, setBuildWiki] = useState(true)
  const [extractGraph, setExtractGraph] = useState(true)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<LanhuImportResult | null>(null)
  const [evOpen, setEvOpen] = useState(false)
  const [drawerJobId, setDrawerJobId] = useState<number | null>(null)

  const reset = () => {
    setUrl(''); setDescription(''); setResult(null)
    setIngestKnowledge(true); setBuildWiki(true); setExtractGraph(true)
  }

  const submit = () => {
    const u = url.trim()
    if (!u) return
    // image_only 状态时强制要求补充说明
    if (result?.extraction_status === 'image_only' && !description.trim()) {
      toast.warning('原型为图片无法提取文本，请填写补充说明后重试')
      return
    }
    setLoading(true)
    setResult(null)
    importLanhu({
      url: u,
      description: description.trim(),
      target: { ingest_knowledge: ingestKnowledge, build_wiki: buildWiki, extract_graph: extractGraph },
    })
      .then((r) => {
        setResult(r)
        const hint = STATUS_HINT[r.extraction_status]
        if (hint?.ok) {
          toast.success(r.extraction_summary || hint.label)
          onImported?.(r)
        } else {
          toast.warning(hint?.label || r.extraction_summary || '提取未成功')
        }
      })
      .catch((e) => toast.error(e?.message || '导入失败（需启用 Wiki 且有 wiki:manage 权限）'))
      .finally(() => setLoading(false))
  }

  return (
    <>
    <Dialog open={open} onOpenChange={(v) => { if (!v) reset(); onOpenChange(v) }}>
      <DialogContent className="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>导入蓝湖需求</DialogTitle>
          <DialogDescription>
            通过 lanhu_mcp 提取设计稿为原始知识（Raw Source），可同步进入 RAG 知识库并生成 Wiki。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="lanhu-url">蓝湖设计稿页面链接</Label>
            <Input
              id="lanhu-url"
              placeholder="https://lanhuapp.com/web/#/item/project/...&docId=...&pageId=..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="lanhu-desc">补充说明（图片型原型必填）</Label>
            <Textarea
              id="lanhu-desc"
              rows={3}
              placeholder="当原型仅为图片、无法提取文本时，请在此描述关键需求与规则"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="t-ingest" className="font-normal">同步进 RAG 知识库</Label>
              <Switch id="t-ingest" checked={ingestKnowledge} onCheckedChange={setIngestKnowledge} />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="t-wiki" className="font-normal">生成 Wiki 页面</Label>
              <Switch id="t-wiki" checked={buildWiki} onCheckedChange={setBuildWiki} />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="t-graph" className="font-normal">抽取知识图谱</Label>
              <Switch id="t-graph" checked={extractGraph} onCheckedChange={setExtractGraph} />
            </div>
          </div>

          {result && (
            <div className={`flex items-start gap-2 rounded-md border p-3 text-sm ${
              STATUS_HINT[result.extraction_status]?.ok
                ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
                : 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
            }`}>
              {STATUS_HINT[result.extraction_status]?.ok
                ? <CheckCircle2 className="size-4 mt-0.5 shrink-0" />
                : <AlertCircle className="size-4 mt-0.5 shrink-0" />}
              <div className="space-y-0.5">
                <div className="font-medium">
                  {STATUS_HINT[result.extraction_status]?.label || result.extraction_status}
                </div>
                {result.extraction_summary && (
                  <div className="text-xs opacity-80">{result.extraction_summary}</div>
                )}
                {result.raw_source_id && (
                  <div className="text-xs opacity-80">Raw Source #{result.raw_source_id}
                    {result.knowledge_source_id ? ` · 知识源 #${result.knowledge_source_id}` : ''}
                    {result.wiki_job_id ? ` · Wiki 任务 #${result.wiki_job_id}` : ''}
                  </div>
                )}
                {result.extraction_status === 'image_only' && !description.trim() && (
                  <div className="text-xs font-medium mt-1 text-red-600 dark:text-red-400">
                    请在「补充说明」中填写关键需求描述，然后再次点击「开始导入」
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => setEvOpen(true)}>使用证据包 OCR 导入</Button>
          <Button variant="outline" onClick={() => onOpenChange(false)}>关闭</Button>
          <Button disabled={loading || !url.trim()} onClick={submit}>
            {loading ? <Loader2 className="size-4 animate-spin mr-1" /> : null}
            开始导入
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <LanhuEvidenceDialog
      open={evOpen}
      onOpenChange={setEvOpen}
      initialUrl={url}
      onCreated={(job) => setDrawerJobId(job.id)}
    />
    <LanhuEvidenceJobDrawer
      open={drawerJobId != null}
      onOpenChange={(v) => { if (!v) setDrawerJobId(null) }}
      jobId={drawerJobId}
    />
    </>
  )
}
