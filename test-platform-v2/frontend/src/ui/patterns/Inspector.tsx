/**
 * Inspector — 右侧详情检查器（黑曜流界核心交互组件）
 *
 * 替代 Modal，在侧边栏或主内容区域展示对象详情。
 * 支持 dark 主题下的玻璃材质和翡翠绿强调色。
 */

import { type ReactNode, type CSSProperties, useRef, useEffect } from 'react'
import { X, type LucideIcon } from '@/lib/icons'
import { cn } from '@/lib/utils'

export interface InspectorProps {
  open: boolean
  onClose: () => void
  title?: string
  subtitle?: string
  icon?: LucideIcon
  tone?: 'neutral' | 'success' | 'active' | 'risk'
  /** 标题行右侧的状态标签 */
  statusBadge?: ReactNode
  /** 主要指标区 */
  metrics?: Array<{ label: string; value: string; note?: string }>
  /** 摘要描述 */
  summary?: string
  /** 进度 (0-100) */
  progress?: number
  /** 底部操作 */
  actions?: ReactNode
  /** 自定义内容 */
  children?: ReactNode
  className?: string
  width?: string | number
}

export function Inspector({
  open,
  onClose,
  title,
  subtitle,
  icon: Icon,
  tone = 'neutral',
  statusBadge,
  metrics,
  summary,
  progress,
  actions,
  children,
  className,
  width = 380,
}: InspectorProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  useEffect(() => {
    if (open && panelRef.current) {
      panelRef.current.focus()
    }
  }, [open])

  if (!open) return null

  const toneColors: Record<string, string> = {
    neutral: '#909f95',
    success: '#35e68a',
    active: '#80c4ff',
    risk: '#ff9a90',
  }

  const toneColor = toneColors[tone] ?? toneColors.neutral

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label={title ?? '详情'}>
      {/* 遮罩 */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} aria-hidden="true" />

      {/* 面板 */}
      <div
        ref={panelRef}
        tabIndex={-1}
        className={cn(
          'relative flex flex-col h-full overflow-y-auto',
          'bg-[#141c17] border-l border-[rgba(218,239,224,0.1)]',
          'shadow-[-8px_0_32px_rgba(0,0,0,0.4)]',
          className,
        )}
        style={{ width, '--_tone': toneColor } as CSSProperties}
      >
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 z-10 flex items-center justify-center size-8 rounded-md text-[#718077] hover:text-[#eef6f0] hover:bg-white/5 transition-colors"
          aria-label="关闭检查器"
        >
          <X className="size-4" />
        </button>

        {/* 头部 */}
        <div className="flex items-center gap-3 px-5 pt-5 pb-4 border-b border-[rgba(218,239,224,0.08)]">
          {Icon && (
            <span className="flex items-center justify-center size-10 rounded-xl bg-white/5" style={{ color: toneColor }}>
              <Icon className="size-5" />
            </span>
          )}
          <div className="min-w-0 flex-1">
            {subtitle && <small className="block text-[0.6875rem] uppercase tracking-[0.08em] text-[#718077]">{subtitle}</small>}
            <b className="block text-[#eef6f0] text-[1.125rem] font-[580] tracking-tight">{title}</b>
          </div>
          {statusBadge}
        </div>

        {/* 指标 */}
        {metrics && metrics.length > 0 && (
          <div className="grid grid-cols-3 gap-px bg-[rgba(218,239,224,0.06)] mx-5 mt-4 rounded-lg overflow-hidden">
            {metrics.map((m, i) => (
              <div key={i} className="bg-[#141c17] p-3 text-center">
                <b className="block text-[1.25rem] font-[560] text-[#eef6f0] tracking-tight">{m.value}</b>
                <small className="text-[0.6875rem] text-[#718077]">{m.label}</small>
                {m.note && <small className="block text-[0.625rem] text-[#536159] mt-0.5">{m.note}</small>}
              </div>
            ))}
          </div>
        )}

        {/* 摘要 */}
        {summary && (
          <p className="px-5 mt-4 text-[0.875rem] text-[#a7b5ab] leading-relaxed">{summary}</p>
        )}

        {/* 进度 */}
        {progress !== undefined && (
          <div className="px-5 mt-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[0.75rem] text-[#718077] font-medium">完成度</span>
              <em className="text-[0.875rem] text-[#eef6f0] font-[560] not-italic">{progress}%</em>
            </div>
            <div className="h-1.5 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
              <span
                className="block h-full rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${progress}%`,
                  background: `linear-gradient(90deg, ${toneColor}, ${toneColor}88)`,
                }}
              />
            </div>
          </div>
        )}

        {/* 自定义内容 */}
        {children && <div className="flex-1 px-5 py-4">{children}</div>}

        {/* 底部操作 */}
        {actions && (
          <div className="sticky bottom-0 px-5 py-4 border-t border-[rgba(218,239,224,0.08)] bg-[#141c17]">
            {actions}
          </div>
        )}
      </div>
    </div>
  )
}
