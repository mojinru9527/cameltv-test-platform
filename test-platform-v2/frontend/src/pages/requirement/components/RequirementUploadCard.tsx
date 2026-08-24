import { Button, Input } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Cloud, Inbox, Link2, Loader2, XCircle } from '@/lib/icons'
import { cn } from '@/lib/utils'

interface Props {
  canWriteDocs: boolean
  getRootProps: any
  getInputProps: any
  isDragActive: boolean
  uploading: boolean
  lanhuUrl: string
  onLanhuUrlChange: (value: string) => void
  onLanhuSubmit: () => void
}

export default function RequirementUploadCard({
  canWriteDocs,
  getRootProps,
  getInputProps,
  isDragActive,
  uploading,
  lanhuUrl,
  onLanhuUrlChange,
  onLanhuSubmit,
}: Props) {
  return (
    <Card size="sm" className={'ui-surface' + (canWriteDocs ? '' : ' opacity-60 pointer-events-none')}>
      <CardHeader className="border-b pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Cloud className="size-4" />
          上传需求
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4">
        <Tabs defaultValue="file">
          <TabsList>
            <TabsTrigger value="file">文件上传</TabsTrigger>
            <TabsTrigger value="lanhu">蓝湖链接</TabsTrigger>
          </TabsList>
          <TabsContent value="file" className="pt-4">
            <div
              {...getRootProps()}
              className={cn(
                'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
                isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50',
                uploading && 'opacity-50 cursor-not-allowed',
              )}
            >
              <input {...getInputProps({ 'aria-label': '上传需求文档' })} />
              <Inbox className="size-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm">点击或拖拽文件到此区域上传</p>
              <p className="text-xs text-muted-foreground mt-1">
                支持 .md（Markdown）、.docx（Word）、.xlsx（Excel）格式
              </p>
            </div>
          </TabsContent>
          <TabsContent value="lanhu" className="pt-4 space-y-3">
            <div className="flex w-full flex-col gap-2 sm:flex-row sm:gap-0">
              <div className="relative flex-1">
                <Link2 className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-primary pointer-events-none" />
                <Input
                  className="pl-8 sm:rounded-r-none sm:border-r-0 focus-visible:z-10"
                  placeholder="输入蓝湖设计稿链接…"
                  value={lanhuUrl}
                  onChange={(e) => onLanhuUrlChange(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && onLanhuSubmit()}
                />
                {lanhuUrl && (
                  <button
                    type="button"
                    className="absolute right-1 top-1/2 min-h-11 min-w-11 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    onClick={() => onLanhuUrlChange('')}
                    aria-label="清空蓝湖链接"
                  >
                    <XCircle className="size-4" />
                  </button>
                )}
              </div>
              <Button className="sm:rounded-l-none" onClick={onLanhuSubmit} disabled={uploading}>
                {uploading ? <Loader2 className="size-4 animate-spin" /> : null}
                证据采集
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                全页面滚动截图 + OCR，生成可追溯证据包（Word/JSON），再入需求 / RAG / Wiki
              </span>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
