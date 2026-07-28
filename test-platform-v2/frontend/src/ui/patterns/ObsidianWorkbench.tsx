/**
 * ObsidianWorkbench — 黑曜流界工作台生产级外壳
 *
 * 包裹业务页面内容，提供：
 * - 玻璃材质页头（kicker + 标题 + 操作）
 * - 实时状态栏
 * - Bento 指标条
 * - 可选的 SpatialChain / Inspector / RiskRadar / ReleasePulse
 */

import { type ReactNode, type CSSProperties, type PointerEvent, useState } from 'react'
import { cn } from '@/lib/utils'
import { RefreshCw } from '@/lib/icons'

export interface WorkbenchMetric {
  label: string
  value: string
  note: string
  tone: 'positive' | 'active' | 'risk' | 'neutral'
}

export interface ObsidianWorkbenchProps {
  /** 页头 kicker 小字 */
  kicker?: string
  /** 面包屑 */
  breadcrumbs?: string
  /** 主标题 */
  title: string
  /** 副标题描述 */
  description?: string
  /** 标题右侧操作 */
  actions?: ReactNode
  /** 状态栏信息 */
  statusLine?: Array<{ label: string; live?: boolean }>
  /** Bento 指标 */
  metrics?: WorkbenchMetric[]
  /** 是否加载中 */
  loading?: boolean
  /** 刷新回掉 */
  onRefresh?: () => void
  /** 页面内容 */
  children: ReactNode
  className?: string
}

function setSpotlight(event: PointerEvent<HTMLElement>) {
  const bounds = event.currentTarget.getBoundingClientRect()
  event.currentTarget.style.setProperty('--spotlight-x', `${event.clientX - bounds.left}px`)
  event.currentTarget.style.setProperty('--spotlight-y', `${event.clientY - bounds.top}px`)
}

const toneVars: Record<string, string> = {
  positive: '#80dba6',
  active: '#80c4ff',
  risk: '#ff9a90',
  neutral: '#909f95',
}

export function ObsidianWorkbench({
  kicker = 'TEST PLATFORM',
  breadcrumbs,
  title,
  description,
  actions,
  statusLine,
  metrics,
  loading,
  onRefresh,
  children,
  className,
}: ObsidianWorkbenchProps) {
  const [hovered, setHovered] = useState(false)

  return (
    <section
      className={cn('relative text-[#eef6f0]', className)}
      role="region"
      aria-label={title}
      onPointerMove={setSpotlight}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* ── 页头 ── */}
      <header className="mb-6">
        {/* Kicker */}
        <div className="flex items-center gap-2 mb-3 text-[0.75rem] font-[650] tracking-[0.09em] text-[#91a398]">
          <span className="w-[22px] h-px bg-[#35e68a] shadow-[0_0_10px_rgba(53,230,138,0.55)]" />
          {kicker}
        </div>

        {/* 标题行 */}
        <div className="flex items-center justify-between gap-8">
          <div className="min-w-0 max-w-[850px]">
            {breadcrumbs && (
              <span className="block mb-2 text-[0.8125rem] text-[#829087]">{breadcrumbs}</span>
            )}
            <h1 className="max-w-[32ch] text-[clamp(1.75rem,2.4vw,2.25rem)] font-[580] tracking-[-0.03em] leading-[1.08] text-[#f5faf6] text-balance">
              {title}
            </h1>
            {description && (
              <p className="max-w-[70ch] mt-4 text-[1rem] leading-relaxed text-[#a7b5ab]">
                {description}
              </p>
            )}
          </div>

          {/* 操作区 */}
          <div className="flex flex-shrink-0 gap-2">
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
          </div>
        </div>

        {/* 状态栏 */}
        {statusLine && statusLine.length > 0 && (
          <div className="flex items-center gap-4 mt-4 text-[0.8125rem] text-[#819086]">
            {statusLine.map((item, i) => (
              <span
                key={i}
                className={cn(
                  'flex items-center gap-2',
                  item.live && 'text-[#bbf3d0]',
                  i > 0 && 'relative pl-4 before:absolute before:top-1/2 before:left-0 before:w-[3px] before:h-[3px] before:rounded-full before:bg-[#536159] before:-translate-y-1/2',
                )}
              >
                {item.live && (
                  <i className="w-[7px] h-[7px] rounded-full bg-[#35e68a] shadow-[0_0_0_4px_rgba(53,230,138,0.09),0_0_12px_rgba(53,230,138,0.4)]" />
                )}
                {item.label}
              </span>
            ))}
          </div>
        )}
      </header>

      {/* ── 指标条 ── */}
      {metrics && metrics.length > 0 && (
        <div
          className={cn(
            'grid mb-6 py-3 border-y border-[rgba(218,239,224,0.08)]',
            metrics.length <= 2
              ? 'grid-cols-1 sm:grid-cols-2'
              : metrics.length === 3
                ? 'grid-cols-1 sm:grid-cols-3'
                : 'grid-cols-2 lg:grid-cols-4',
          )}
          aria-label="关键指标"
        >
          {metrics.map((m, i) => (
            <div
              key={m.label}
              className={cn(
                'relative grid grid-cols-[1fr_auto] gap-x-3 gap-y-[5px] min-w-0 px-3 py-2 sm:px-6',
                metrics.length <= 3
                  ? i > 0 && 'sm:border-l sm:border-[rgba(218,239,224,0.08)]'
                  : i % 2 === 1 && 'border-l border-[rgba(218,239,224,0.08)] lg:border-l',
                metrics.length > 3 && i > 0 && 'lg:border-l lg:border-[rgba(218,239,224,0.08)]',
                i === 0 && 'pl-0',
              )}
            >
              <span className="flex items-center gap-[7px] text-[0.8125rem]" style={{ color: toneVars[m.tone] }}>
                {m.label}
              </span>
              <b className="row-span-2 col-start-2 self-center text-[1.75rem] font-[560] tracking-[-0.03em] text-[#eef6f0]">
                {m.value}
              </b>
              <small className="text-[0.75rem] text-[#91a398]">{m.note}</small>
            </div>
          ))}
        </div>
      )}

      {/* ── 内容区 ── */}
      <div className={cn('relative z-10')}>
        {/* Spotlight 光晕 */}
        <div
          className="absolute inset-0 pointer-events-none transition-opacity duration-200"
          style={{
            opacity: hovered ? 1 : 0,
            background: `radial-gradient(520px circle at var(--spotlight-x, 50%) var(--spotlight-y, 40%), rgba(53,230,138,0.03), transparent 60%)`,
            zIndex: 0,
          }}
        />
        <div className="relative z-[1]">
          {loading ? (
            <WorkbenchSkeleton />
          ) : (
            children
          )}
        </div>
      </div>
    </section>
  )
}

function WorkbenchSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="加载中">
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 bg-[rgba(255,255,255,0.03)] rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 h-64 bg-[rgba(255,255,255,0.03)] rounded-xl" />
        <div className="h-64 bg-[rgba(255,255,255,0.03)] rounded-xl" />
      </div>
    </div>
  )
}
