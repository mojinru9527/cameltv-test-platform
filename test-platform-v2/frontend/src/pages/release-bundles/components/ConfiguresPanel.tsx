import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import {
  fetchAdminLinks,
  suggestConfigures,
  confirmConfigures,
  createAdminLink,
  deleteAdminLink,
} from '@/api/requirementModules'
import type { ModuleAdminLinkOut } from '@/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Link2,
  CheckCircle2,
  XCircle,
  Trash2,
  Sparkles,
  Shield,
  RefreshCw,
} from '@/lib/icons'
import { cn } from '@/lib/utils'

interface ConfiguresPanelProps {
  bundleId: number
}

export default function ConfiguresPanel({ bundleId }: ConfiguresPanelProps) {
  const [links, setLinks] = useState<ModuleAdminLinkOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [suggesting, setSuggesting] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const loadLinks = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAdminLinks(bundleId)
      setLinks(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载配置链路失败')
    } finally {
      setLoading(false)
    }
  }, [bundleId])

  useEffect(() => {
    loadLinks()
  }, [loadLinks])

  const handleSuggest = async () => {
    setSuggesting(true)
    try {
      await suggestConfigures(bundleId)
      toast.success('AI 推荐已触发，请刷新查看结果')
      await loadLinks()
    } catch {
      toast.error('AI 推荐失败')
    } finally {
      setSuggesting(false)
    }
  }

  const handleConfirm = async () => {
    setConfirming(true)
    try {
      const result = await confirmConfigures(bundleId)
      toast.success(`已确认 ${result.confirmed} 条链接，跳过 ${result.skipped} 条`)
      await loadLinks()
    } catch {
      toast.error('确认失败')
    } finally {
      setConfirming(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteAdminLink(id)
      setLinks((prev) => prev.filter((l) => l.id !== id))
      toast.success('链接已删除')
    } catch {
      toast.error('删除失败')
    }
  }

  const configuresLinks = links.filter((l) => l.relation_type === 'configures')
  const adminLinks = links.filter((l) => l.relation_type === 'links_to_admin')

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-base">配置链路</CardTitle>
            <Badge variant="secondary" className="text-xs">
              {links.length}
            </Badge>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSuggest}
              disabled={suggesting}
            >
              <Sparkles className="h-3.5 w-3.5 mr-1" />
              {suggesting ? '推荐中...' : 'AI 推荐'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleConfirm}
              disabled={confirming || links.length === 0}
            >
              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
              {confirming ? '确认中...' : '批量确认'}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-4">
            <p className="text-sm text-destructive mb-2">{error}</p>
            <Button variant="outline" size="sm" onClick={loadLinks}>
              <RefreshCw className="h-3 w-3 mr-1" /> 重试
            </Button>
          </div>
        ) : links.length === 0 ? (
          <div className="text-center py-6">
            <Link2 className="h-8 w-8 mx-auto mb-2 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              暂无配置链路
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              点击「AI 推荐」自动发现 client↔admin 关联
            </p>
          </div>
        ) : (
          <ScrollArea className="max-h-[400px]">
            <div className="space-y-2">
              {configuresLinks.map((link) => (
                <LinkRow
                  key={link.id}
                  link={link}
                  onDelete={() => handleDelete(link.id)}
                />
              ))}
              {adminLinks.map((link) => (
                <LinkRow
                  key={link.id}
                  link={link}
                  onDelete={() => handleDelete(link.id)}
                />
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}

function LinkRow({
  link,
  onDelete,
}: {
  link: ModuleAdminLinkOut
  onDelete: () => void
}) {
  const isConfigures = link.relation_type === 'configures'

  return (
    <div className="flex items-center gap-3 p-3 rounded-md border bg-muted/30">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className="text-sm font-medium text-blue-700 truncate">
          📱 客户端模块 #{link.client_module_id}
        </span>
        <Badge
          variant="outline"
          className={cn(
            'text-xs shrink-0',
            isConfigures
              ? 'border-orange-200 bg-orange-50 text-orange-700'
              : 'border-blue-200 bg-blue-50 text-blue-700',
          )}
        >
          {isConfigures ? '配置' : '关联'}
        </Badge>
        <span className="text-muted-foreground shrink-0">→</span>
        <Shield className="h-4 w-4 text-orange-500 shrink-0" />
        <span className="text-sm font-medium text-orange-700 truncate">
          🖥️ 运营后台 #{link.admin_module_id}
        </span>
      </div>
      <Badge variant="secondary" className="text-xs shrink-0">
        {(link.confidence * 100).toFixed(0)}%
      </Badge>
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7 text-muted-foreground hover:text-destructive shrink-0"
        onClick={onDelete}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}
