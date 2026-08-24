import { useEffect, useState } from 'react'
import { fetchRunArtifactBlob } from '@/api/uitest'
import { Download, FileText } from '@/lib/icons'

export function ProtectedArtifactMedia({
  runId,
  path,
  name,
  kind,
}: {
  runId: number
  path: string
  name: string
  kind: 'image' | 'video' | 'download' | 'link'
}) {
  const [objectUrl, setObjectUrl] = useState('')
  const [loadFailed, setLoadFailed] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    let createdUrl = ''

    fetchRunArtifactBlob(runId, path, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return
        createdUrl = URL.createObjectURL(blob)
        setObjectUrl(createdUrl)
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoadFailed(true)
      })

    return () => {
      controller.abort()
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
  }, [runId, path])

  if (loadFailed) {
    return <span role="alert" className="text-xs text-status-danger">{name} 加载失败</span>
  }
  if (!objectUrl) {
    return <span className="text-xs text-muted-foreground">{name} 加载中…</span>
  }
  if (kind === 'image') {
    return (
      <a href={objectUrl} target="_blank" rel="noreferrer" className="block rounded border overflow-hidden hover:ring-2 hover:ring-primary">
        <img src={objectUrl} alt={name} className="w-full h-24 object-cover" />
        <div className="text-xs p-1 truncate">{name}</div>
      </a>
    )
  }
  if (kind === 'video') {
    return <video aria-label={name} controls className="w-full max-h-[300px]" src={objectUrl} />
  }
  return (
    <a
      href={objectUrl}
      {...(kind === 'download' ? { download: name } : { target: '_blank', rel: 'noreferrer' })}
      className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
    >
      {kind === 'download' ? <Download className="size-3" /> : <FileText className="size-4" />}
      {name}
    </a>
  )
}
