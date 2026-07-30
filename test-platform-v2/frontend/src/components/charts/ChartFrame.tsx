import { useId, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

export interface ChartColumn<T extends Record<string, unknown>> {
  key: keyof T & string
  label: string
  format?: (value: T[keyof T], row: T) => ReactNode
}

export interface ChartFrameProps<T extends Record<string, unknown>> {
  title: string
  summary: string
  data: T[]
  columns: ChartColumn<T>[]
  children: ReactNode
  className?: string
}

export default function ChartFrame<T extends Record<string, unknown>>({
  title,
  summary,
  data,
  columns,
  children,
  className,
}: ChartFrameProps<T>) {
  const summaryId = useId()

  return (
    <figure
      aria-label={title}
      aria-describedby={summaryId}
      className={cn('min-w-0', className)}
    >
      <div aria-hidden="true" inert>{children}</div>
      <figcaption id={summaryId} className="mt-3 text-sm text-muted-foreground">
        {summary}
      </figcaption>
      <details className="mt-3 rounded-md border border-border">
        <summary className="min-h-11 cursor-pointer rounded-md px-3 py-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          查看图表数据
        </summary>
        <div className="overflow-auto border-t" role="region" aria-label={`${title}数据表区域`} tabIndex={0}>
          <table className="w-full min-w-max text-sm" aria-label={`${title}数据`}>
            <thead>
              <tr className="border-b bg-muted/40 text-left">
                {columns.map((column) => (
                  <th key={column.key} scope="col" className="px-3 py-2 font-medium">
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, rowIndex) => (
                <tr key={rowIndex} className="border-b last:border-b-0">
                  {columns.map((column) => (
                    <td key={column.key} className="px-3 py-2">
                      {column.format
                        ? column.format(row[column.key], row)
                        : String(row[column.key] ?? '—')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  )
}
