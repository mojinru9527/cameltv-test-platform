/**
 * ListToolbar — Reusable search + filter bar for CRUD list pages.
 *
 * Renders a row with search on the left, filter controls in the middle,
 * and action buttons (create, reset) on the right.
 *
 * @example
 * <ListToolbar
 *   searchValue={keyword}
 *   onSearchChange={setKeyword}
 *   onSearch={refetch}
 *   createButton={<Button onClick={openCreate}><Plus />新建</Button>}
 * >
 *   <Select value={status} onValueChange={(v) => setFilter('status', v)}>
 *     ...
 *   </Select>
 * </ListToolbar>
 */

import type { ReactNode } from 'react'
import { Search, RotateCcw } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export interface ListToolbarProps {
  /** Current search input value. */
  searchValue: string
  /** Called on each keystroke. */
  onSearchChange: (value: string) => void
  /** Called on Enter or search button click. */
  onSearch?: () => void

  /** Placeholder for search input. @default "搜索..." */
  searchPlaceholder?: string

  /** Extra filter controls rendered between search and actions. */
  children?: ReactNode

  /** Action buttons on the right. */
  actions?: ReactNode

  /** Show a reset button that calls onReset. */
  onReset?: () => void

  /** Additional className for the outer container. */
  className?: string
}

export default function ListToolbar({
  searchValue,
  onSearchChange,
  onSearch,
  searchPlaceholder = '搜索...',
  children,
  actions,
  onReset,
  className,
}: ListToolbarProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && onSearch) onSearch()
  }

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      {/* Search */}
      <div className="flex items-center gap-1">
        <Input
          aria-label="搜索"
          placeholder={searchPlaceholder}
          className="w-[200px] h-9"
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        {onSearch && (
          <Button variant="outline" size="sm" onClick={onSearch} data-icon="inline-start">
            <Search />
            搜索
          </Button>
        )}
      </div>

      {/* Filter controls */}
      {children && (
        <div className="flex items-center gap-2">{children}</div>
      )}

      {/* Spacer */}
      <div className="flex-1 min-w-0" />

      {/* Actions */}
      <div className="flex items-center gap-2">
        {onReset && (
          <Button variant="ghost" size="sm" onClick={onReset}>
            <RotateCcw className="size-4" />
            重置
          </Button>
        )}
        {actions}
      </div>
    </div>
  )
}
