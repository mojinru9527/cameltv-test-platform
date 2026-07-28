/**
 * SpatialChain — 空间质量链路组件
 *
 * 将需求→用例→计划→执行→缺陷→报告以可点击空间堆栈表示。
 * 点击节点切换右侧 Inspector。
 *
 * 桌面：3D 层叠样式
 * 移动端：自动退化为横向滚动卡片
 */

import { type ReactNode, type CSSProperties, useState } from 'react'
import { cn } from '@/lib/utils'
import type { LucideIcon } from '@/lib/icons'

export interface ChainNode {
  id: string
  label: string
  shortLabel: string
  count: string
  status: string
  progress: number
  tone: 'neutral' | 'success' | 'active' | 'risk'
  icon: LucideIcon
  /** 是否有风险 */
  risk?: boolean
  /** 是否 P0 */
  p0?: boolean
}

export interface SpatialChainProps {
  nodes: ChainNode[]
  activeId?: string
  onSelect?: (node: ChainNode) => void
  /** 展示模式 */
  variant?: 'chain' | 'grid'
  className?: string
}

const toneStyles: Record<ChainNode['tone'], { bg: string; border: string; text: string; color: string }> = {
  neutral: {
    bg: 'bg-[var(--color-status-neutral-bg)]',
    border: 'border-[var(--color-border-default)]',
    text: 'text-[var(--color-status-neutral)]',
    color: 'var(--color-status-neutral)',
  },
  success: {
    bg: 'bg-[var(--color-status-success-bg)]',
    border: 'border-[var(--color-status-success-border)]',
    text: 'text-[var(--color-status-success)]',
    color: 'var(--color-status-success)',
  },
  active: {
    bg: 'bg-[var(--color-status-info-bg)]',
    border: 'border-[var(--color-status-info-border)]',
    text: 'text-[var(--color-status-info)]',
    color: 'var(--color-status-info)',
  },
  risk: {
    bg: 'bg-[var(--color-status-danger-bg)]',
    border: 'border-[var(--color-status-danger-border)]',
    text: 'text-[var(--color-status-danger)]',
    color: 'var(--color-status-danger)',
  },
}

export function SpatialChain({ nodes, activeId, onSelect, variant = 'chain', className }: SpatialChainProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-[var(--color-text-secondary)] text-sm">
        暂无链路数据
      </div>
    )
  }

  if (variant === 'grid') {
    return (
      <div className={cn('grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3', className)}>
        {nodes.map((node, i) => {
          const Icon = node.icon
          const isActive = activeId === node.id
          const isHovered = hoveredId === node.id
          const styles = toneStyles[node.tone]

          return (
            <button
              key={node.id}
              onClick={() => onSelect?.(node)}
              onMouseEnter={() => setHoveredId(node.id)}
              onMouseLeave={() => setHoveredId(null)}
              className={cn(
                'relative flex flex-col items-center gap-2 p-4 rounded-xl border transition-colors duration-200 text-left',
                styles.bg, styles.border,
                isActive && 'ring-2 ring-[var(--color-border-focus)] ring-offset-1 ring-offset-[var(--color-canvas)] scale-[1.02]',
                isHovered && !isActive && 'border-[var(--color-border-strong)] translate-y-[-2px]',
              )}
              aria-pressed={isActive}
              aria-label={`${node.label}：${node.status}`}
            >
              {/* 序号 */}
              <span className="absolute top-2 right-2 text-[0.625rem] text-[var(--color-text-muted)] font-mono">
                {String(i + 1).padStart(2, '0')}
              </span>

              {/* 风险/P0 标记 */}
              {(node.risk || node.p0) && (
                <span className={cn(
                  'absolute top-2 left-2 w-2 h-2 rounded-full',
                  node.p0
                    ? 'bg-[var(--color-status-danger)] shadow-[0_0_6px_var(--color-status-danger-glow)]'
                    : 'bg-[var(--color-status-warning)]',
                )} />
              )}

              <Icon className={cn('size-5', styles.text)} aria-hidden="true" />
              <b className="text-[1.125rem] font-[560] text-[var(--color-text)] tracking-tight">{node.count}</b>
              <small className="text-[0.6875rem] text-[var(--color-text-muted)] text-center leading-tight">{node.shortLabel}</small>
              <span className={cn('text-[0.625rem]', styles.text)}>{node.status}</span>
            </button>
          )
        })}
      </div>
    )
  }

  // Chain variant: horizontal stack with connecting lines
  return (
    <div className={cn('flex overflow-x-auto gap-2 pb-2 scrollbar-thin', className)} aria-label="质量链路">
      {nodes.map((node, i) => {
        const Icon = node.icon
        const isActive = activeId === node.id
        const isHovered = hoveredId === node.id
        const styles = toneStyles[node.tone]

        return (
          <button
            key={node.id}
            onClick={() => onSelect?.(node)}
            onMouseEnter={() => setHoveredId(node.id)}
            onMouseLeave={() => setHoveredId(null)}
            className={cn(
              'relative flex items-center gap-3 flex-shrink-0 min-w-[180px] px-4 py-3 rounded-xl border transition-colors duration-200',
              styles.bg, styles.border,
              isActive && 'ring-2 ring-[var(--color-border-focus)] ring-offset-1 ring-offset-[var(--color-canvas)]',
              isHovered && !isActive && 'border-[var(--color-border-strong)]',
            )}
            style={{ '--stage-index': i } as CSSProperties}
            aria-pressed={isActive}
            aria-label={`${node.label}：${node.status}`}
          >
            {/* 连接线（非最后一个） */}
            {i < nodes.length - 1 && (
              <div className="hidden sm:block absolute -right-[10px] top-1/2 -translate-y-1/2 z-10">
                <div className="w-2.5 h-0.5 bg-[var(--color-border-strong)]" />
              </div>
            )}

            {/* 序号 */}
            <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-[var(--color-hover)] text-[0.625rem] text-[var(--color-hover-text)] font-mono">
              {String(i + 1).padStart(2, '0')}
            </span>

            <Icon className={cn('size-4 flex-shrink-0', styles.text)} aria-hidden="true" />

            <div className="min-w-0">
              <small className="block text-[0.6875rem] text-[var(--color-text-muted)] truncate">{node.shortLabel}</small>
              <b className="block text-[0.9375rem] font-[560] text-[var(--color-text)] tracking-tight truncate">{node.count}</b>
              <em className="block text-[0.625rem] not-italic truncate" style={{ color: styles.color }}>
                {node.status}
              </em>
            </div>

            {/* 进度条 */}
            <div className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full overflow-hidden mx-3 mb-1.5">
              <div
                className="size-full origin-left rounded-full transition-transform duration-200 ease-out"
                style={{
                  transform: `scaleX(${Math.min(100, Math.max(0, node.progress)) / 100})`,
                  background: isActive
                    ? 'var(--color-action-primary)'
                    : 'var(--color-progress-track)',
                }}
              />
            </div>
          </button>
        )
      })}
    </div>
  )
}
