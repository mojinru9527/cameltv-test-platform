import { useState } from 'react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { FolderOpen, ChevronRight, FileText } from '@/lib/icons'
import { cn } from '@/lib/utils'

export interface DomainTreeNode {
  key: string
  title: React.ReactNode
  children?: DomainTreeNode[]
  isLeaf?: boolean
}

interface Props {
  treeData: DomainTreeNode[]
  onSelect: (keys: string[]) => void
  selectedKeys?: string[]
  className?: string
}

function TreeItem({ node, onSelect, depth = 0 }: { node: DomainTreeNode; onSelect: (keys: string[]) => void; depth?: number }) {
  const [open, setOpen] = useState(false)
  const hasChildren = node.children && node.children.length > 0

  const handleClick = () => {
    onSelect([node.key])
    if (hasChildren) setOpen((prev) => !prev)
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleClick}
        className={cn(
          'flex w-full items-center gap-1 rounded px-1.5 py-0.5 text-left text-xs transition-colors hover:bg-accent hover:text-accent-foreground',
          depth > 0 && 'pl-4'
        )}
      >
        {hasChildren ? (
          <>
            <ChevronRight className={cn('size-3 shrink-0 transition-transform', open && 'rotate-90')} />
            <FolderOpen className="size-3 shrink-0 text-muted-foreground" />
          </>
        ) : (
          <FileText className="size-3 shrink-0 text-muted-foreground ml-3" />
        )}
        <span className="truncate">{node.title}</span>
      </button>
      {hasChildren && (
        <Collapsible open={open} onOpenChange={setOpen}>
          <CollapsibleContent>
            <div className="ml-2 border-l border-border">
              {node.children!.map((child) => (
                <TreeItem key={child.key} node={child} onSelect={onSelect} depth={depth + 1} />
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  )
}

export default function DomainTree({ treeData, onSelect, className }: Props) {
  return (
    <div className={cn('space-y-0.5', className)}>
      {treeData.map((node) => (
        <TreeItem key={node.key} node={node} onSelect={onSelect} />
      ))}
    </div>
  )
}
