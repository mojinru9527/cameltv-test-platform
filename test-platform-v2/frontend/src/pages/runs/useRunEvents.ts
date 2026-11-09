import { useEffect, useRef, useState } from 'react'
import { API_BASE_URL } from '@/api/baseUrl'
import { listRunEvents } from '@/api/aiqeRuns'
import type { AiqeRunEvent } from '@/types/aiqe'

/**
 * 订阅 Run 事件：先补拉 after_seq，再走 SSE；断线自动降级为 3s 轮询。
 * 刷新页面后从 0 重放，保证事件不丢（TA-008 验收）。
 */
export function useRunEvents(runId: string | undefined): AiqeRunEvent[] {
  const [events, setEvents] = useState<AiqeRunEvent[]>([])
  const lastSeq = useRef(0)

  useEffect(() => {
    if (!runId) return
    let cancelled = false
    let source: EventSource | null = null
    let timer: number | undefined
    setEvents([])
    lastSeq.current = 0

    const append = (items: AiqeRunEvent[]) => {
      if (cancelled || !items.length) return
      const fresh = items.filter((item) => item.seq > lastSeq.current)
      if (!fresh.length) return
      lastSeq.current = fresh[fresh.length - 1].seq
      setEvents((prev) => [...prev, ...fresh])
    }

    const poll = async () => {
      try {
        const data = await listRunEvents(runId, lastSeq.current)
        append(data.items)
      } catch {
        // 轮询失败保留已有事件，等待下一次重试
      }
    }

    void poll()
    try {
      source = new EventSource(
        `${API_BASE_URL}/aiqe/runs/${runId}/events/stream?after_seq=${lastSeq.current}`,
        { withCredentials: true },
      )
      source.onmessage = (event) => {
        try {
          append([JSON.parse(event.data) as AiqeRunEvent])
        } catch {
          // 忽略无法解析的心跳/脏消息
        }
      }
      source.onerror = () => {
        source?.close()
        source = null
        if (!timer) timer = window.setInterval(() => void poll(), 3000)
      }
    } catch {
      timer = window.setInterval(() => void poll(), 3000)
    }

    return () => {
      cancelled = true
      source?.close()
      if (timer) window.clearInterval(timer)
    }
  }, [runId])

  return events
}
