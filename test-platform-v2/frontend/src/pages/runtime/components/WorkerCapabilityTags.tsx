const CAP_COLORS: Record<string, string> = {
  HTTP: 'bg-status-info-muted text-status-info',
  BROWSER: 'bg-status-success-muted text-status-success',
  MYSQL: 'bg-status-warning-muted text-status-warning',
  POSTGRES: 'bg-status-warning-muted text-status-warning',
  LOG: 'bg-muted text-muted-foreground',
  KAFKA: 'bg-status-info-muted text-status-info',
}

export function WorkerCapabilityTags({ capabilities }: { capabilities: string[] }) {
  if (!capabilities?.length) return <span className="text-muted-foreground">无</span>
  return (
    <div className="flex flex-wrap gap-1">
      {capabilities.map((cap) => (
        <span key={cap} className={`rounded px-1.5 py-0.5 text-xs ${CAP_COLORS[cap] ?? 'bg-muted text-muted-foreground'}`}>
          {cap}
        </span>
      ))}
    </div>
  )
}
