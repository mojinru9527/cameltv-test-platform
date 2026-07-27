import { useState } from 'react'
import type { ModuleTreeNode } from '@/types'
import { Badge } from '@/components/ui/badge'
import {
  ChevronRight,
  ChevronDown,
  FolderOpen,
  FileText,
  Box,
  Paperclip,
  Monitor,
  Smartphone,
  Globe,
  Shield,
  GitBranch,
  ExternalLink,
  type LucideIcon,
} from '@/lib/icons'
import { cn } from '@/lib/utils'

const NODE_TYPE_CONFIG: Record<
  string,
  { icon: LucideIcon; label: string; className: string }
> = {
  module: {
    icon: FolderOpen,
    label: '模块',
    className: 'text-blue-600 bg-blue-50 border-blue-200',
  },
  page: {
    icon: FileText,
    label: '页面',
    className: 'text-green-600 bg-green-50 border-green-200',
  },
  function_point: {
    icon: Box,
    label: '功能点',
    className: 'text-purple-600 bg-purple-50 border-purple-200',
  },
  attachment: {
    icon: Paperclip,
    label: '附件',
    className: 'text-amber-600 bg-amber-50 border-amber-200',
  },
}

const PLATFORM_ICONS: Record<string, LucideIcon> = {
  APP: Smartphone,
  PC: Monitor,
  WEB: Globe,
  ADMIN: Shield,
}

const CHANGE_BADGE: Record<string, { label: string; className: string }> = {
  new: { label: '新增', className: 'border-green-200 bg-green-50 text-green-700' },
  modified: { label: '变更', className: 'border-amber-200 bg-amber-50 text-amber-700' },
  deleted: { label: '删除', className: 'border-red-200 bg-red-50 text-red-700' },
  unchanged: { label: '不变', className: '' },
}

// ── Interaction pill ──

function InteractionPill({ interactionsJson }: { interactionsJson: string }) {
  const [open, setOpen] = useState(false)
  let interactions: Array<Record<string, string>> = []
  try {
    interactions = JSON.parse(interactionsJson)
  } catch {
    return null
  }
  if (!Array.isArray(interactions) || interactions.length === 0) return null

  return (
    <div className="mt-1">
      <button
        className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-0.5"
        onClick={(e) => {
          e.stopPropagation()
          setOpen(!open)
        }}
      >
        <GitBranch className="size-3" />
        {interactions.length} 个交互
      </button>
      {open && (
        <div className="mt-1 space-y-0.5 pl-2 border-l-2 border-muted">
          {interactions.map((ia, idx) => (
            <div key={idx} className="text-xs text-muted-foreground flex items-center gap-1">
              <ExternalLink className="size-2.5 shrink-0" />
              <span className="font-medium">{ia.trigger || '?'}</span>
              <span>→</span>
              <span>{ia.target_page || '?'}</span>
              {ia.interaction_type && (
                <Badge variant="secondary" className="text-[9px] px-1 py-0">
                  {ia.interaction_type}
                </Badge>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Single tree node ──

function TreeNode({ node, depth = 0 }: { node: ModuleTreeNode; depth?: number }) {
  const [expanded, setExpanded] = useState(depth < 2) // auto-expand first 2 levels
  const hasChildren = node.children && node.children.length > 0
  const config = NODE_TYPE_CONFIG[node.node_type] ?? NODE_TYPE_CONFIG.module
  const PlatformIcon = PLATFORM_ICONS[node.platform]

  return (
    <div className="select-none">
      {/* Node row */}
      <div
        className={cn(
          'flex items-center gap-1.5 py-1.5 px-2 rounded-md cursor-pointer hover:bg-muted/60 transition-colors',
          depth > 0 && 'ml-0',
        )}
        style={{ paddingLeft: `${8 + depth * 20}px` }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {/* Expand toggle */}
        <span className="w-4 shrink-0 flex items-center justify-center">
          {hasChildren ? (
            expanded ? (
              <ChevronDown className="size-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="size-3.5 text-muted-foreground" />
            )
          ) : (
            <span className="w-3.5" />
          )}
        </span>

        {/* Node type icon */}
        <Badge
          variant="outline"
          className={cn('text-[10px] px-1 py-0 gap-0.5 shrink-0', config.className)}
        >
          <config.icon className="size-3" />
          {config.label}
        </Badge>

        {/* Platform icon */}
        {PlatformIcon && (
          <span title={node.platform}>
            <PlatformIcon className="size-3.5 text-muted-foreground shrink-0" />
          </span>
        )}

        {/* Name */}
        <span className={cn(
          'text-sm truncate',
          node.change_type === 'deleted' && 'line-through text-muted-foreground',
        )}>
          {node.name}
        </span>

        {/* Change badge */}
        {node.change_type && node.change_type !== 'unchanged' && (
          <Badge
            variant="outline"
            className={cn('text-[9px] px-1 py-0 shrink-0', CHANGE_BADGE[node.change_type]?.className)}
          >
            {CHANGE_BADGE[node.change_type]?.label ?? node.change_type}
          </Badge>
        )}

        {/* Description tooltip */}
        {node.description && (
          <span className="text-xs text-muted-foreground truncate hidden sm:inline">
            — {node.description.slice(0, 60)}{node.description.length > 60 ? '...' : ''}
          </span>
        )}

        {/* Child count */}
        {hasChildren && !expanded && (
          <span className="text-[10px] text-muted-foreground ml-auto shrink-0">
            {node.child_count || node.children.length}
          </span>
        )}
      </div>

      {/* Interaction pills (for page nodes) */}
      {node.node_type === 'page' && node.page_interactions && node.page_interactions !== '[]' && (
        <div style={{ paddingLeft: `${28 + depth * 20}px` }}>
          <InteractionPill interactionsJson={node.page_interactions} />
        </div>
      )}

      {/* Children */}
      {expanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Root component ──

export default function ModuleTreeView({ roots }: { roots: ModuleTreeNode[] }) {
  if (!roots || roots.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground text-sm">
        暂无模块节点
      </div>
    )
  }

  return (
    <div className="border rounded-lg bg-card">
      {/* Header */}
      <div className="flex items-center gap-4 px-3 py-2 border-b bg-muted/30 text-xs text-muted-foreground">
        <span className="w-4" />
        <span className="w-16">类型</span>
        <span>名称</span>
        <span className="ml-auto">变更</span>
      </div>

      {/* Tree */}
      <div className="py-1">
        {roots.map((root) => (
          <TreeNode key={root.id} node={root} />
        ))}
      </div>
    </div>
  )
}
