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
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }

      if (e.key !== 'Tab' || !panelRef.current) return

      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => element.getAttribute('aria-hidden') !== 'true')

      if (focusable.length === 0) {
        e.preventDefault()
        panelRef.current.focus()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement

      if (e.shiftKey && (active === first || active === panelRef.current || !panelRef.current.contains(active))) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && (active === last || active === panelRef.current || !panelRef.current.contains(active))) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  useEffect(() => {
    if (!open) return

    const opener = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    panelRef.current?.focus()

    return () => {
      if (opener?.isConnected) opener.focus()
    }
  }, [open])

  if (!open) return null

  const toneColors: Record<string, string> = {
    neutral: 'var(--color-status-neutral)',
    success: 'var(--color-status-success)',
    active: 'var(--color-status-info)',
    risk: 'var(--color-status-danger)',
  }

  const toneColor = toneColors[tone] ?? toneColors.neutral
  const customWidth = width === 380 ? undefined : width

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label={title ?? '详情'}>
      {/* 遮罩 */}
      <div className="absolute inset-0 bg-[var(--color-overlay-scrim)]" onClick={onClose} aria-hidden="true" />

      {/* 面板 */}
      <div
        ref={panelRef}
        tabIndex={-1}
        className={cn(
          'relative flex h-full w-[min(100vw,380px)] max-w-full flex-col overflow-y-auto',
          'bg-[var(--color-surface)] border-l border-[var(--color-border-default)]',
          'shadow-[var(--shadow-inspector)]',
          className,
        )}
        style={{ width: customWidth, maxWidth: '100%', '--inspector-tone': toneColor } as CSSProperties}
      >
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          className="absolute top-1.5 right-1.5 z-10 flex size-11 items-center justify-center rounded-md text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-hover)] hover:text-[var(--color-hover-text)]"
          aria-label="关闭检查器"
        >
          <X className="size-4" />
        </button>

        {/* 头部 */}
        <div className="flex items-center gap-3 px-5 pt-5 pb-4 border-b border-[var(--color-border-subtle)]">
          {Icon && (
            <span className="flex items-center justify-center size-10 rounded-xl bg-[var(--color-hover)]" style={{ color: toneColor }}>
              <Icon className="size-5" />
            </span>
          )}
          <div className="min-w-0 flex-1">
            {subtitle && <small className="block text-[0.6875rem] uppercase tracking-[0.08em] text-[var(--color-text-muted)]">{subtitle}</small>}
            <b className="block text-[var(--color-text)] text-[1.125rem] font-[580] tracking-tight">{title}</b>
          </div>
          {statusBadge}
        </div>

        {/* 指标 */}
        {metrics && metrics.length > 0 && (
          <div className="grid grid-cols-3 gap-px bg-[var(--color-border-subtle)] mx-5 mt-4 rounded-lg overflow-hidden">
            {metrics.map((m, i) => (
              <div key={i} className="bg-[var(--color-surface)] p-3 text-center">
                <b className="block text-[1.25rem] font-[560] text-[var(--color-text)] tracking-tight">{m.value}</b>
                <small className="text-[0.6875rem] text-[var(--color-text-muted)]">{m.label}</small>
                {m.note && <small className="block text-[0.625rem] text-[var(--color-text-secondary)] mt-0.5">{m.note}</small>}
              </div>
            ))}
          </div>
        )}

        {/* 摘要 */}
        {summary && (
          <p className="px-5 mt-4 text-[0.875rem] text-[var(--color-text-secondary)] leading-relaxed">{summary}</p>
        )}

        {/* 进度 */}
        {progress !== undefined && (
          <div className="px-5 mt-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[0.75rem] text-[var(--color-text-muted)] font-medium">完成度</span>
              <em className="text-[0.875rem] text-[var(--color-text)] font-[560] not-italic">{progress}%</em>
            </div>
            <div className="h-1.5 bg-[var(--color-progress-track)] rounded-full overflow-hidden">
              <span
                className="block size-full origin-left rounded-full transition-transform duration-200 ease-out"
                style={{
                  transform: `scaleX(${Math.min(100, Math.max(0, progress)) / 100})`,
                  background: toneColor,
                }}
              />
            </div>
          </div>
        )}

        {/* 自定义内容 */}
        {children && <div className="flex-1 px-5 py-4">{children}</div>}

        {/* 底部操作 */}
        {actions && (
          <div className="sticky bottom-0 px-5 py-4 border-t border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
            {actions}
          </div>
        )}
      </div>
    </div>
  )
}
