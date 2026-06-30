import { useState, useMemo } from 'react'
import { ArrowUp, ArrowDown, Columns2 } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { SkeletonTable } from '@/components/ui/skeleton'
import EmptyState from '@/components/EmptyState'
import Pagination from '@/components/Pagination'
import { cn } from '@/lib/utils'

// ── Types ──

export interface DataTableColumn<T = any> {
  key: string
  header: string
  sortable?: boolean
  hidden?: boolean
  width?: string
  className?: string
  headerClassName?: string
  /** Custom cell render. Falls back to `row[key]` when omitted. */
  render?: (row: T) => React.ReactNode
}

interface DataTablePagination {
  page: number
  totalPages: number
  total: number
  onChange: (page: number) => void
}

interface DataTableSelection<T> {
  selected: Set<string>
  onSelectionChange: (selected: Set<string>) => void
  getId: (row: T) => string
}

interface DataTableEmptyState {
  title: string
  description?: string
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  data: T[]
  rowKey: (row: T) => string | number
  loading?: boolean
  /** Number of skeleton rows when loading (default 5). Set to 0 to disable. */
  loadingRows?: number
  /** Empty state config. Falls back to title="暂无数据". */
  emptyState?: DataTableEmptyState
  /** Attach pagination below the table. */
  pagination?: DataTablePagination
  /** Enable checkbox row selection. */
  selection?: DataTableSelection<T>
  /** Slot for toolbar content (search, filters, actions) rendered above the table. */
  toolbar?: React.ReactNode
  stickyHeader?: boolean
  columnVisibility?: boolean
  onRowClick?: (row: T) => void
  className?: string
}

// ── Helpers ──

type SortDir = 'asc' | 'desc' | null

function getCheckedState(all: boolean, some: boolean): boolean | 'indeterminate' {
  if (all) return true
  if (some) return 'indeterminate'
  return false
}

// ── Component ──

export default function DataTable<T extends Record<string, any>>({
  columns,
  data,
  rowKey,
  loading = false,
  loadingRows = 5,
  emptyState,
  pagination,
  selection,
  toolbar,
  stickyHeader = false,
  columnVisibility: showColumnToggle = false,
  onRowClick,
  className,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>(null)
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(() => {
    const initial = new Set<string>()
    columns.forEach((c) => {
      if (c.hidden) initial.add(c.key)
    })
    return initial
  })

  // ── Derived state ──

  const visibleColumns = columns.filter((c) => !hiddenKeys.has(c.key))
  const totalCols = visibleColumns.length + (selection ? 1 : 0)
  const showSkeleton = loading && data.length === 0 && loadingRows > 0

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDir) return data
    return [...data].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (av == null) return 1
      if (bv == null) return -1
      if (av < bv) return sortDir === 'asc' ? -1 : 1
      if (av > bv) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [data, sortKey, sortDir])

  // ── Selection state ──

  const allSelected =
    selection && data.length > 0 && data.every((row) => selection.selected.has(selection.getId(row)))
  const someSelected =
    selection && !allSelected && data.some((row) => selection.selected.has(selection.getId(row)))

  const handleSelectAll = () => {
    if (!selection) return
    if (allSelected) {
      selection.onSelectionChange(new Set())
    } else {
      selection.onSelectionChange(new Set(data.map((row) => selection.getId(row))))
    }
  }

  const handleSelectRow = (row: T) => {
    if (!selection) return
    const id = selection.getId(row)
    const next = new Set(selection.selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    selection.onSelectionChange(next)
  }

  // ── Sorting ──

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      if (sortDir === 'asc') setSortDir('desc')
      else if (sortDir === 'desc') {
        setSortKey(null)
        setSortDir(null)
      }
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  // ── Column visibility ──

  const toggleColumn = (key: string) => {
    setHiddenKeys((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  // ── Render ──

  return (
    <div className={cn('rounded-lg border', stickyHeader && 'overflow-hidden', className)}>
      {/* ── Toolbar + Column visibility toggle ── */}
      {(toolbar || showColumnToggle) && (
        <div className="flex items-center justify-between px-3 pt-2 pb-2 gap-2">
          <div className="flex-1 min-w-0">{toolbar}</div>
          {showColumnToggle && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="xs" className="gap-1 shrink-0">
                  <Columns2 className="size-3.5" />
                  列显示
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-40">
                <DropdownMenuGroup>
                  {columns.map((col) => (
                    <DropdownMenuItem
                      key={col.key}
                      onClick={(e) => {
                        e.preventDefault()
                        toggleColumn(col.key)
                      }}
                      className="flex items-center gap-2 text-sm"
                    >
                      <Checkbox checked={!hiddenKeys.has(col.key)} className="pointer-events-none" />
                      <span>{col.header}</span>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      )}

      <div className={cn(stickyHeader && 'overflow-auto max-h-[70vh]')}>
        <Table>
          <TableHeader className={cn(stickyHeader && 'sticky top-0 z-10 bg-card')}>
            <TableRow>
              {/* Selection checkbox column */}
              {selection && (
                <TableHead className="w-10">
                  <Checkbox
                    checked={getCheckedState(!!allSelected, !!someSelected)}
                    onCheckedChange={handleSelectAll}
                    aria-label="全选"
                  />
                </TableHead>
              )}
              {visibleColumns.map((col) => {
                const isSorted = sortKey === col.key && sortDir
                const canSort = col.sortable
                return (
                  <TableHead
                    key={col.key}
                    style={col.width ? { width: col.width } : undefined}
                    className={cn(
                      canSort && 'cursor-pointer select-none hover:bg-muted/50 transition-colors',
                      col.headerClassName,
                    )}
                    onClick={canSort ? () => toggleSort(col.key) : undefined}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.header}
                      {canSort && (
                        <span className="inline-flex flex-col -space-y-1.5 text-muted-foreground/60">
                          <ArrowUp
                            className={cn(
                              'size-2.5',
                              isSorted && sortDir === 'asc' && 'text-foreground',
                            )}
                          />
                          <ArrowDown
                            className={cn(
                              'size-2.5',
                              isSorted && sortDir === 'desc' && 'text-foreground',
                            )}
                          />
                        </span>
                      )}
                    </span>
                  </TableHead>
                )
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {showSkeleton ? (
              <TableRow>
                <TableCell colSpan={totalCols} className="p-0">
                  <SkeletonTable
                    rows={loadingRows}
                    cols={totalCols}
                    className="border-0 rounded-none"
                  />
                </TableCell>
              </TableRow>
            ) : sortedData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={totalCols}>
                  <EmptyState
                    title={emptyState?.title || '暂无数据'}
                    description={emptyState?.description}
                    className="py-8"
                  />
                </TableCell>
              </TableRow>
            ) : (
              sortedData.map((row) => {
                const selId = selection?.getId(row)
                const isSelected = selId != null ? selection!.selected.has(selId) : false
                return (
                  <TableRow
                    key={rowKey(row)}
                    className={cn(
                      onRowClick && 'cursor-pointer',
                      isSelected && 'bg-accent',
                    )}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    data-state={isSelected ? 'selected' : undefined}
                  >
                    {selection && (
                      <TableCell className="w-10" onClick={(e) => e.stopPropagation()}>
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={() => handleSelectRow(row)}
                          aria-label={`选择 ${selId}`}
                        />
                      </TableCell>
                    )}
                    {visibleColumns.map((col) => (
                      <TableCell
                        key={col.key}
                        className={col.className}
                        style={col.width ? { width: col.width } : undefined}
                      >
                        {col.render ? col.render(row) : (row[col.key] ?? '—')}
                      </TableCell>
                    ))}
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* ── Pagination ── */}
      {pagination && (
        <div className="px-4 py-3 border-t">
          <Pagination
            page={pagination.page}
            totalPages={pagination.totalPages}
            total={pagination.total}
            onChange={pagination.onChange}
          />
        </div>
      )}
    </div>
  )
}
