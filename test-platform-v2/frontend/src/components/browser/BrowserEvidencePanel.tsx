import { Badge } from '@/ui'
import { type BrowserSessionEvent } from '@/api/browserInteractions'
import { JsonBlock } from './JsonView'

export interface BrowserEvidencePanelProps {
  events: BrowserSessionEvent[]
}

const CAPTURE_TYPES = ['capture_screenshot', 'capture_dom', 'capture_network']

function isCaptureEvent(event: BrowserSessionEvent): boolean {
  return CAPTURE_TYPES.some((t) => event.event_type.toLowerCase().includes(t))
}

function evidenceRef(event: BrowserSessionEvent): string | null {
  const payload = event.payload_ref_json
  if (!payload) return null
  const ref = payload.ref ?? payload.reference ?? payload.url ?? payload.screenshot_url
  return typeof ref === 'string' ? ref : null
}

/**
 * Renders captured browser evidence (screenshots / DOM / network capture)
 * referenced by observation events. Any referenced URL is surfaced; the full
 * payload is always available so nothing is hidden.
 */
export function BrowserEvidencePanel({ events }: BrowserEvidencePanelProps) {
  const captureEvents = events.filter(isCaptureEvent).sort((a, b) => a.sequence - b.sequence)

  if (captureEvents.length === 0) {
    return (
      <div className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
        尚未捕获到浏览器证据（截图 / DOM / 网络）。
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {captureEvents.map((event) => {
        const ref = evidenceRef(event)
        return (
          <div key={event.id} className="rounded-md border px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-muted-foreground">#{event.sequence}</span>
              <Badge variant="outline" className="font-mono text-[11px]">
                {event.event_type}
              </Badge>
              {ref && <span className="font-mono text-[11px] text-muted-foreground">{ref}</span>}
            </div>
            <div className="mt-2">
              {ref ? (
                <div className="space-y-1.5">
                  <p className="font-mono text-[11px] break-all text-primary">{ref}</p>
                  {event.payload_ref_json && (
                    <JsonBlock label="载荷详情" data={event.payload_ref_json} />
                  )}
                </div>
              ) : (
                <JsonBlock label="凭证引用载荷" data={event.payload_ref_json} />
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
