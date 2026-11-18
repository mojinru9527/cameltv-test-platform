import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Badge } from '@/ui'
import { fetchArtifactBlob } from '@/api/aiqeArtifacts'
import type { AiqeRunArtifact } from '@/types/aiqe'

type ViewerKind = 'image' | 'video' | 'har' | 'json' | 'text' | 'download'

const IMAGE_TYPES = new Set(['SCREENSHOT', 'screenshot'])
const VIDEO_TYPES = new Set(['VIDEO', 'video'])
const HAR_TYPES = new Set(['HAR', 'har'])
const JSON_TYPES = new Set([
  'DOM_SNAPSHOT',
  'dom',
  'ACCESSIBILITY_TREE',
  'a11y',
  'DB_RESULT_SUMMARY',
  'db_snapshot',
])
const TEXT_TYPES = new Set([
  'CONSOLE_LOG',
  'RUNNER_LOG',
  'DEVICE_LOG',
  'log',
  'HTTP_REQUEST',
  'HTTP_RESPONSE',
  'request',
  'response',
  'report',
  'NETWORK_PROFILE',
  'ENVIRONMENT_SNAPSHOT',
])

/** AUD-008 §7：按 Artifact 类型选择 Viewer（图片/视频/HAR/JSON/日志/下载）。 */
export function viewerKind(artifactType: string): ViewerKind {
  const key = String(artifactType || '')
  if (IMAGE_TYPES.has(key)) return 'image'
  if (VIDEO_TYPES.has(key)) return 'video'
  if (HAR_TYPES.has(key)) return 'har'
  if (key === 'PLAYWRIGHT_TRACE' || key === 'trace') return 'download'
  if (JSON_TYPES.has(key)) return 'json'
  if (TEXT_TYPES.has(key)) return 'text'
  return 'download'
}

interface Props {
  runId: string
  artifacts: AiqeRunArtifact[]
}

export default function EvidencePanel({ runId, artifacts }: Props) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [objectUrl, setObjectUrl] = useState('')
  const [text, setText] = useState('')
  const [har, setHar] = useState<Array<{ method: string; url: string; status: number }>>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const urlRef = useRef('')

  const active = useMemo(
    () => artifacts.find((item) => item.id === activeId) ?? null,
    [artifacts, activeId],
  )

  const revoke = useCallback(() => {
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current)
      urlRef.current = ''
    }
    setObjectUrl('')
  }, [])

  useEffect(() => revoke, [revoke])

  const openArtifact = useCallback(
    async (artifact: AiqeRunArtifact) => {
      setActiveId(artifact.id)
      setError('')
      setText('')
      setHar([])
      revoke()
      setLoading(true)
      try {
        const blob = await fetchArtifactBlob(artifact.id)
        const kind = viewerKind(artifact.artifact_type)
        if (kind === 'image' || kind === 'video') {
          const url = URL.createObjectURL(blob)
          urlRef.current = url
          setObjectUrl(url)
        } else if (kind === 'har') {
          const parsed = JSON.parse(await blob.text()) as {
            log?: { entries?: Array<{ request?: { method?: string; url?: string }; response?: { status?: number } }> }
          }
          const entries = parsed.log?.entries ?? []
          setHar(
            entries.slice(0, 200).map((entry) => ({
              method: entry.request?.method ?? '',
              url: entry.request?.url ?? '',
              status: entry.response?.status ?? 0,
            })),
          )
        } else if (kind === 'json' || kind === 'text') {
          const raw = await blob.text()
          setText(raw.length > 20_000 ? `${raw.slice(0, 20_000)}\n…[truncated]` : raw)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '证据加载失败')
      } finally {
        setLoading(false)
      }
    },
    [revoke],
  )

  const kind = active ? viewerKind(active.artifact_type) : null

  return (
    <section className="space-y-3" data-testid="evidence-panel">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold">证据（{artifacts.length}）</h2>
        <span className="text-xs text-muted-foreground">Run {runId}</span>
      </div>

      <div className="overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left">
            <tr>
              <th className="px-3 py-2">类型</th>
              <th className="px-3 py-2">大小</th>
              <th className="px-3 py-2">上传</th>
              <th className="px-3 py-2">脱敏</th>
              <th className="px-3 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {artifacts.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-center text-muted-foreground" colSpan={5}>
                  暂无 Artifact
                </td>
              </tr>
            ) : (
              artifacts.map((artifact) => (
                <tr key={artifact.id} className="border-t">
                  <td className="px-3 py-2">{artifact.artifact_type}</td>
                  <td className="px-3 py-2">{artifact.size_bytes} B</td>
                  <td className="px-3 py-2">
                    {artifact.upload_status === 'PENDING_UPLOAD' ? (
                      <Badge tone="warning">上传中</Badge>
                    ) : artifact.upload_status === 'CORRUPTED' ? (
                      <Badge tone="danger">已损坏</Badge>
                    ) : artifact.upload_status === 'PURGED' ? (
                      <Badge tone="neutral">已清理</Badge>
                    ) : (
                      <Badge tone="success">可用</Badge>
                    )}
                  </td>
                  <td className="px-3 py-2">{artifact.redaction_status}</td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      className="text-primary hover:underline"
                      onClick={() => void openArtifact(artifact)}
                    >
                      查看
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {loading ? <p className="text-sm text-muted-foreground">加载证据中…</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {active && !loading && !error ? (
        <div className="rounded-lg border p-3" data-testid="evidence-viewer">
          <p className="mb-2 text-xs text-muted-foreground">
            {active.artifact_type} · {kind}
          </p>
          {kind === 'image' && objectUrl ? (
            <img src={objectUrl} alt={`证据 ${active.artifact_type}`} className="max-h-[420px] max-w-full rounded" />
          ) : null}
          {kind === 'video' && objectUrl ? (
            <video src={objectUrl} controls className="max-h-[420px] max-w-full rounded" />
          ) : null}
          {kind === 'har' ? (
            <div className="max-h-[320px] overflow-auto">
              <table className="w-full text-xs">
                <thead className="text-left">
                  <tr>
                    <th className="py-1 pr-2">Method</th>
                    <th className="py-1 pr-2">URL</th>
                    <th className="py-1">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {har.length === 0 ? (
                    <tr>
                      <td className="py-2 text-muted-foreground" colSpan={3}>
                        HAR 中没有请求记录
                      </td>
                    </tr>
                  ) : (
                    har.map((entry, index) => (
                      <tr key={`${entry.method}-${entry.url}-${index}`} className="border-t">
                        <td className="py-1 pr-2 font-mono">{entry.method}</td>
                        <td className="py-1 pr-2">{entry.url}</td>
                        <td className="py-1">{entry.status}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          ) : null}
          {kind === 'json' || kind === 'text' ? (
            <pre className="max-h-[320px] overflow-auto whitespace-pre-wrap break-all rounded bg-muted/30 p-2 text-xs">
              {text || '（空内容）'}
            </pre>
          ) : null}
          {kind === 'download' && objectUrl ? (
            <a className="text-primary hover:underline" href={objectUrl} download={`${active.id}-${active.artifact_type}`}>
              下载 Trace / 原始证据
            </a>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
