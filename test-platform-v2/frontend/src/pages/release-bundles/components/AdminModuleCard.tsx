import { useState, useEffect, useCallback } from 'react'
import {
  fetchAdminLinks,
  deleteAdminLink,
} from '@/api/requirementModules'
import type { ModuleAdminLinkOut, ModuleTreeNode } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  ChevronRight,
  Link2,
  Trash2,
  Shield,
  RefreshCw,
  Sparkles,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

interface AdminModuleCardProps {
  bundleId: number
  modules: ModuleTreeNode[]
}

interface LinkWithNames extends ModuleAdminLinkOut {
  clientName?: string
  adminName?: string
}

export default function AdminModuleCard({ bundleId, modules }: AdminModuleCardProps) {
  const [links, setLinks] = useState<LinkWithNames[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(true)
  const [deleting, setDeleting] = useState<number | null>(null)

  // Build module name lookup
  const buildModuleLookup = useCallback(() => {
    const lookup: Record<number, string> = {}
    function walkNodes(nodes: ModuleTreeNode[]) {
      for (const node of nodes) {
        lookup[node.id] = node.name
        if (node.children) walkNodes(node.children)
      }
    }
    walkNodes(modules)
    return lookup
  }, [modules])

  const loadLinks = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAdminLinks(bundleId)
      const nameLookup = buildModuleLookup()
      setLinks(
        data.map((link) => ({
          ...link,
          clientName: nameLookup[link.client_module_id] ?? `模块#${link.client_module_id}`,
          adminName: nameLookup[link.admin_module_id] ?? `模块#${link.admin_module_id}`,
        })),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载关联失败')
    } finally {
      setLoading(false)
    }
  }, [bundleId, buildModuleLookup])

  useEffect(() => {
    loadLinks()
  }, [loadLinks])

  const handleDelete = async (id: number) => {
    setDeleting(id)
    try {
      await deleteAdminLink(id)
      setLinks((prev) => prev.filter((l) => l.id !== id))
      toast.success('关联已删除')
    } catch {
      toast.error('删除关联失败')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <Card>
      <Collapsible open={open} onOpenChange={setOpen}>
        <CardHeader className="pb-2">
          <CollapsibleTrigger asChild>
            <button
              className={cn(
                'flex items-center gap-2 w-full text-left',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md',
              )}
            >
              <ChevronRight
                className={cn(
                  'h-4 w-4 shrink-0 transition-transform duration-200',
                  open && 'rotate-90',
                )}
              />
              <Link2 className="h-5 w-5 text-muted-foreground" />
              <CardTitle className="text-base">运营后台关联</CardTitle>
              <Badge variant="secondary" className="text-xs ml-auto">
                {links.length} 链接
              </Badge>
            </button>
          </CollapsibleTrigger>
        </CardHeader>
        <CollapsibleContent>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : error ? (
              <div className="text-center py-2">
                <p className="text-sm text-destructive mb-2">{error}</p>
                <Button variant="outline" size="sm" onClick={loadLinks}>
                  <RefreshCw className="h-3 w-3 mr-1" /> 重试
                </Button>
              </div>
            ) : links.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                暂无运营后台关联
              </p>
            ) : (
              <div className="space-y-2">
                {links.map((link) => (
                  <div
                    key={link.id}
                    className="flex items-center gap-3 p-3 rounded-md border bg-muted/30"
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="text-sm font-medium text-blue-700 truncate">
                        {link.clientName}
                      </span>
                      <Badge
                        variant="outline"
                        className={cn(
                          'text-xs shrink-0',
                          link.relation_type === 'configures'
                            ? 'border-orange-200 bg-orange-50 text-orange-700'
                            : 'border-blue-200 bg-blue-50 text-blue-700',
                        )}
                      >
                        {link.relation_type === 'configures' ? '配置' : '关联'}
                      </Badge>
                      <span className="text-muted-foreground shrink-0">→</span>
                      <Shield className="h-4 w-4 text-orange-500 shrink-0" />
                      <span className="text-sm font-medium text-orange-700 truncate">
                        {link.adminName}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant="secondary" className="text-xs">
                        {(link.confidence * 100).toFixed(0)}%
                      </Badge>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-muted-foreground hover:text-destructive"
                        disabled={deleting === link.id}
                        onClick={() => handleDelete(link.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
