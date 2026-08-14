import { Badge, Button } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, Search } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { TYPE_TAG } from './RequirementDocTable'

interface Props {
  title: string
  fileType: string | undefined
  isLoading: boolean
  isRefetching: boolean
  isError: boolean
  errorMessage: string | undefined
  content: string | undefined
  previewExpanded: boolean
  onTogglePreview: () => void
  onClose: () => void
  onRetry: () => void
}

export default function RequirementContentPreview({
  title,
  fileType,
  isLoading,
  isRefetching,
  isError,
  errorMessage,
  content,
  previewExpanded,
  onTogglePreview,
  onClose,
  onRetry,
}: Props) {
  return (
    <Card size="sm" className="ui-surface">
      <CardHeader className="border-b pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Search className="size-4" />
            内容预览：{title}
            {fileType && TYPE_TAG[fileType] && (
              <Badge
                tone="neutral"
                className={cn('gap-1', TYPE_TAG[fileType].className)}
              >
                {TYPE_TAG[fileType].icon}
                {TYPE_TAG[fileType].label}
              </Badge>
            )}
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            收起
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        {isLoading || isRefetching ? (
          <div className="flex min-h-[100px] items-center justify-center text-sm text-muted-foreground">
            <Loader2 className="mr-2 size-4 animate-spin" />
            正在加载完整内容…
          </div>
        ) : isError ? (
          <div className="flex min-h-[100px] flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
            <span>{errorMessage || '文档详情加载失败'}</span>
            <Button variant="secondary" size="sm" onClick={onRetry}>重试加载</Button>
          </div>
        ) : (
          <div className={cn(
            'whitespace-pre-wrap text-xs bg-muted/50 rounded-md p-3 overflow-auto',
            !previewExpanded && 'max-h-[200px]',
          )}>
            {content || '文档内容为空'}
          </div>
        )}
        {content && content.length > 400 && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-1"
            onClick={onTogglePreview}
          >
            {previewExpanded ? '收起' : '展开全部'}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
