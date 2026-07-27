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

const toneStyles: Record<string, { bg: string; border: string; text: string }> = {
  neutral: {
    bg: 'bg-[rgba(255,255,255,0.03)]',
    border: 'border-[rgba(218,239,224,0.1)]',
    text: 'text-[#909f95]',
  },
  success: {
    bg: 'bg-[rgba(53,230,138,0.06)]',
    border: 'border-[rgba(53,230,138,0.2)]',
    text: 'text-[#80dba6]',
  },
  active: {
    bg: 'bg-[rgba(128,196,255,0.06)]',
    border: 'border-[rgba(128,196,255,0.2)]',
    text: 'text-[#80c4ff]',
  },
  risk: {
    bg: 'bg-[rgba(255,154,144,0.06)]',
    border: 'border-[rgba(255,154,144,0.2)]',
    text: 'text-[#ff9a90]',
  },
}

export function SpatialChain({ nodes, activeId, onSelect, variant = 'chain', className }: SpatialChainProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-[#718077] text-sm">
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
                'relative flex flex-col items-center gap-2 p-4 rounded-xl border transition-all duration-[180ms] text-left',
                styles.bg, styles.border,
                isActive && 'ring-2 ring-[#35e68a] ring-offset-1 ring-offset-[#0b100d] scale-[1.02]',
                isHovered && !isActive && 'border-[rgba(218,239,224,0.2)] translate-y-[-2px]',
              )}
              aria-pressed={isActive}
              aria-label={`${node.label}：${node.status}`}
            >
              {/* 序号 */}
              <span className="absolute top-2 right-2 text-[0.625rem] text-[#536159] font-mono">
                {String(i + 1).padStart(2, '0')}
              </span>

              {/* 风险/P0 标记 */}
              {(node.risk || node.p0) && (
                <span className={cn(
                  'absolute top-2 left-2 w-2 h-2 rounded-full',
                  node.p0 ? 'bg-[#ff6358] shadow-[0_0_6px_rgba(255,99,88,0.4)]' : 'bg-[#f5a623]',
                )} />
              )}

              <Icon className={cn('size-5', styles.text)} aria-hidden="true" />
              <b className="text-[1.125rem] font-[560] text-[#eef6f0] tracking-tight">{node.count}</b>
              <small className="text-[0.6875rem] text-[#718077] text-center leading-tight">{node.shortLabel}</small>
              <span className={cn('text-[0.625rem]', styles.text)}>{node.status}</span>
            </button>
          )
        })}
      </div>
    )
  }

  // Chain variant: horizontal stack with connecting lines
  return (
    <div className={cn('flex overflow-x-auto gap-2 pb-2 scrollbar-thin', className)} role="list" aria-label="质量链路">
      {nodes.map((node, i) => {
        const Icon = node.icon
        const isActive = activeId === node.id
        const isHovered = hoveredId === node.id
        const styles = toneStyles[node.tone]

        return (
          <button
            key={node.id}
            role="listitem"
            onClick={() => onSelect?.(node)}
            onMouseEnter={() => setHoveredId(node.id)}
            onMouseLeave={() => setHoveredId(null)}
            className={cn(
              'relative flex items-center gap-3 flex-shrink-0 min-w-[180px] px-4 py-3 rounded-xl border transition-all duration-[180ms]',
              styles.bg, styles.border,
              isActive && 'ring-2 ring-[#35e68a] ring-offset-1 ring-offset-[#0b100d]',
              isHovered && !isActive && 'border-[rgba(218,239,224,0.2)]',
            )}
            style={{ '--stage-index': i } as CSSProperties}
            aria-pressed={isActive}
            aria-label={`${node.label}：${node.status}`}
          >
            {/* 连接线（非最后一个） */}
            {i < nodes.length - 1 && (
              <div className="hidden sm:block absolute -right-[10px] top-1/2 -translate-y-1/2 z-10">
                <div className="w-2.5 h-0.5 bg-[rgba(218,239,224,0.15)]" />
              </div>
            )}

            {/* 序号 */}
            <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-[rgba(255,255,255,0.04)] text-[0.625rem] text-[#718077] font-mono">
              {String(i + 1).padStart(2, '0')}
            </span>

            <Icon className={cn('size-4 flex-shrink-0', styles.text)} aria-hidden="true" />

            <div className="min-w-0">
              <small className="block text-[0.6875rem] text-[#718077] truncate">{node.shortLabel}</small>
              <b className="block text-[0.9375rem] font-[560] text-[#eef6f0] tracking-tight truncate">{node.count}</b>
              <em className="block text-[0.625rem] not-italic truncate" style={{ color: styles.text.split('text-[')[1]?.replace(']', '') || '#718077' }}>
                {node.status}
              </em>
            </div>

            {/* 进度条 */}
            <div className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full overflow-hidden mx-3 mb-1.5">
              <div
                className="h-full rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${node.progress}%`,
                  background: isActive
                    ? 'linear-gradient(90deg, #35e68a, #67efa9)'
                    : 'rgba(255,255,255,0.1)',
                }}
              />
            </div>
          </button>
        )
      })}
    </div>
  )
}
