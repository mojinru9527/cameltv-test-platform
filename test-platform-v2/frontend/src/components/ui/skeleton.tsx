import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  )
}

/** Circle skeleton — for avatars, icons */
function SkeletonCircle({ className, size = "size-10", ...props }: React.ComponentProps<"div"> & { size?: string }) {
  return <Skeleton className={cn("rounded-full", size, className)} {...props} />
}

/** Text line skeleton — for headings, paragraphs */
function SkeletonText({ className, lines = 1, ...props }: React.ComponentProps<"div"> & { lines?: number }) {
  if (lines === 1) {
    return <Skeleton className={cn("h-4 w-full", className)} {...props} />
  }
  return (
    <div className="flex flex-col gap-2" {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            "h-4",
            i === lines - 1 ? "w-3/4" : "w-full",
            className,
          )}
        />
      ))}
    </div>
  )
}

/** Card skeleton — simulates a card with header + content */
function SkeletonCard({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton-card"
      className={cn("rounded-xl border bg-card p-4 space-y-4", className)}
      {...props}
    >
      <div className="flex items-center gap-3">
        <SkeletonCircle size="size-10" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </div>
      <Skeleton className="h-24 w-full rounded-lg" />
    </div>
  )
}

/** Table row skeleton — N rows of table-like loading */
function SkeletonTable({ rows = 5, cols = 4, className, ...props }: React.ComponentProps<"div"> & { rows?: number; cols?: number }) {
  return (
    <div className={cn("rounded-lg border overflow-hidden", className)} {...props}>
      {/* header */}
      <div className="flex gap-3 px-4 py-3 bg-muted/50 border-b">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      {/* body */}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-3 px-4 py-3 border-b last:border-0">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-3 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

/** Page-level skeleton — header + stat cards + table */
function SkeletonPage({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div className={cn("space-y-4", className)} {...props}>
      <Skeleton className="h-7 w-48" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <SkeletonTable rows={5} cols={4} />
    </div>
  )
}

export { Skeleton, SkeletonCircle, SkeletonText, SkeletonCard, SkeletonTable, SkeletonPage }
