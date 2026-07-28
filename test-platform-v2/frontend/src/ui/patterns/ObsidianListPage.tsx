/**
 * ObsidianListPage — 黑曜流界列表页壳
 *
 * 为所有列表类页面提供统一的暗色玻璃页头和内容平面。
 * 兼容现有业务组件，零侵入式包裹。
 */

import { type ReactNode, type PointerEvent, useState } from 'react'
import { RefreshCw } from '@/lib/icons'
import { cn } from '@/lib/utils'

export interface ObsidianListPageProps {
  title: string
  subtitle?: string
  description?: string
  actions?: ReactNode
  /** 页头右侧操作 */
  headerRight?: ReactNode
  /** 筛选/搜索栏 */
  filterBar?: ReactNode
  /** 页面内容 */
  children: ReactNode
  /** 是否加载中 */
  loading?: boolean
  /** 刷新 */
  onRefresh?: () => void
  className?: string
}

function setSpotlight(event: PointerEvent<HTMLElement>) {
  const bounds = event.currentTarget.getBoundingClientRect()
  event.currentTarget.style.setProperty('--spotlight-x', `${event.clientX - bounds.left}px`)
  event.currentTarget.style.setProperty('--spotlight-y', `${event.clientY - bounds.top}px`)
}

export function ObsidianListPage({
  title,
  subtitle,
  description,
  actions,
  headerRight,
  filterBar,
  children,
  loading,
  onRefresh,
  className,
}: ObsidianListPageProps) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      className={cn('relative min-h-full text-[#eef6f0]', className)}
      onPointerMove={setSpotlight}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Spotlight 光晕 */}
      <div
        className="fixed inset-0 pointer-events-none transition-opacity duration-200 z-0"
        style={{
          opacity: hovered ? 1 : 0,
          background: `radial-gradient(520px circle at var(--spotlight-x, 50%) var(--spotlight-y, 40%), rgba(53,230,138,0.02), transparent 60%)`,
        }}
      />

      {/* 页头 */}
      <header className="relative z-10 mb-6">
        {subtitle && (
          <div className="flex items-center gap-2 mb-3 text-[0.75rem] font-[650] tracking-[0.09em] text-[#91a398]">
            <span className="w-[22px] h-px bg-[#35e68a] shadow-[0_0_10px_rgba(53,230,138,0.55)]" />
            {subtitle}
          </div>
        )}

        <div className="flex items-center justify-between gap-6">
          <div className="min-w-0">
            <h1 className="text-[clamp(1.75rem,2.4vw,2.25rem)] font-[580] tracking-[-0.03em] leading-[1.08] text-[#f5faf6] text-balance">
              {title}
            </h1>
            {description && (
              <p className="mt-3 max-w-[70ch] text-[0.9375rem] leading-relaxed text-[#a7b5ab]">
                {description}
              </p>
            )}
          </div>

          <div className="flex flex-shrink-0 items-center gap-2">
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={loading}
                className="inline-flex items-center gap-2 min-h-[42px] px-4 rounded-[9px] border border-[rgba(218,239,224,0.12)] text-[0.875rem] text-[#d9e4dc] bg-[rgba(255,255,255,0.025)] hover:bg-[rgba(255,255,255,0.05)] transition-colors disabled:opacity-40"
              >
                <RefreshCw className={cn('size-4', loading && 'animate-spin')} aria-hidden="true" />
                {loading ? '加载中...' : '刷新'}
              </button>
            )}
            {actions}
            {headerRight}
          </div>
        </div>
      </header>

      {/* 筛选栏 */}
      {filterBar && (
        <div className="relative z-10 mb-4 p-4 rounded-xl bg-[#141c17] border border-[rgba(218,239,224,0.08)]">
          {filterBar}
        </div>
      )}

      {/* 内容平面 */}
      <div className="relative z-10 bg-[#141c17] rounded-xl border border-[rgba(218,239,224,0.08)] overflow-hidden">
        {loading ? (
          <div className="p-8 space-y-4 animate-pulse" aria-busy="true">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 bg-[rgba(255,255,255,0.03)] rounded-lg" />
            ))}
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  )
}
