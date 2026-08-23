import { useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { toast } from 'sonner'
import { Button } from '@/ui'
import { Plus, Loader2, X } from '@/lib/icons'
import { uploadDshTaskImage } from '@/api/dshTasks'

/** 一条待提交的图片附件（uploading=true 表示正在上传，file_id 未定）。 */
export interface AttachImage {
  file_id: string
  name: string
  uploading?: boolean
  /** 会话内唯一标识（上传中占位匹配用） */
  token: string
}

/** 从粘贴事件中取图片文件（供 Textarea onPaste 转发）。 */
export function clipPasteImages(e: { clipboardData?: DataTransfer | null }): File[] {
  const items = Array.from(e.clipboardData?.items ?? [])
  return items
    .filter((i) => i.type.startsWith('image/'))
    .map((i) => i.getAsFile())
    .filter((f): f is File => !!f)
}

/** 批量添加图片：先占位（上传中），成功后回填 file_id，失败移除并提示。 */
export function attachFiles(
  setImages: Dispatch<SetStateAction<AttachImage[]>>,
  files: File[],
): void {
  for (const f of files) {
    const token = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    setImages((prev) => [...prev, { file_id: '', name: f.name, uploading: true, token }])
    uploadDshTaskImage(f)
      .then((r) => {
        setImages((prev) =>
          prev.map((im) =>
            im.token === token
              ? { ...im, file_id: r.file_id, name: r.filename || f.name, uploading: false }
              : im,
          ),
        )
        toast.success(`已添加图片：${f.name}`)
      })
      .catch((e: any) => {
        setImages((prev) => prev.filter((im) => im.token !== token))
        toast.error(e?.message || '图片上传失败')
      })
  }
}

/** 图片附件选择/拖拽区 + 预览列表（可用于 DSH 任务创建表单）。 */
export default function DshImageAttach({
  images,
  setImages,
}: {
  images: AttachImage[]
  setImages: Dispatch<SetStateAction<AttachImage[]>>
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFiles = (files: FileList | null) => {
    const list = Array.from(files ?? []).filter((f) => f.type.startsWith('image/'))
    if (list.length) attachFiles(setImages, list)
  }

  const remove = (token: string) => {
    setImages((prev) => prev.filter((im) => im.token !== token))
  }

  return (
    <div className="space-y-2">
      <div
        className={`flex items-center gap-2 rounded-md border border-dashed p-3 ${
          dragOver ? 'border-status-info bg-status-info-muted' : 'border-border'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          multiple
          className="hidden"
          onChange={(e) => { handleFiles(e.target.files); e.target.value = '' }}
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => inputRef.current?.click()}
        >
          <Plus className="size-4 mr-1" />
          添加图片
        </Button>
        <span className="text-xs text-muted-foreground">
          支持 PNG/JPEG/WebP/GIF，≤10MB；可拖拽或直接粘贴
        </span>
      </div>
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((im) => (
            <div key={im.token} className="flex items-center gap-1 rounded-md border px-2 py-1 text-xs">
              {im.uploading ? (
                <Loader2 className="size-3 animate-spin text-muted-foreground" />
              ) : (
                <span className="size-3 rounded-sm bg-status-info-muted" />
              )}
              <span className="max-w-[140px] truncate">{im.name}</span>
              <button
                type="button"
                aria-label={`移除图片 ${im.name}`}
                className="text-muted-foreground hover:text-status-danger"
                onClick={() => remove(im.token)}
              >
                <X className="size-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
