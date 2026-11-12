import { useEffect, useRef, useState } from 'react'
import { API_BASE_URL } from '@/api/baseUrl'
import { listRunEvents } from '@/api/aiqeRuns'
import type { AiqeRunEvent } from '@/types/aiqe'

export type RunEventConnection = 'connecting' | 'live' | 'polling' | 'idle'

/**
 * 订阅 Run 事件（batch-339 长连接增强）：
 * - 先按 `after_seq` 补拉，再建立 SSE；
 * - SSE 断线不主动关闭：浏览器按 `retry:` 自动重连，并携带 `Last-Event-ID` 续传；
 * - 重连期间降级为 3s 轮询兜底，`onopen` 后停止轮询；
 * - 返回连接状态供页面展示「实时/轮询中」。
 */
export function useRunEvents(runId: string | undefined): {
  events: AiqeRunEvent[]
  connection: RunEventConnection
} {
  const [events, setEvents] = useState<AiqeRunEvent[]>([])
  const [connection, setConnection] = useState<RunEventConnection>('idle')
  const lastSeq = useRef(0)

  useEffect(() => {
    if (!runId) {
      setConnection('idle')
      return
    }
    let cancelled = false
    let source: EventSource | null = null
    let timer: number | undefined
    setEvents([])
    lastSeq.current = 0
    setConnection('connecting')

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

    const startPolling = () => {
      if (timer) return
      timer = window.setInterval(() => void poll(), 3000)
    }

    const stopPolling = () => {
      if (!timer) return
      window.clearInterval(timer)
      timer = undefined
    }

    void poll()
    try {
      source = new EventSource(
        `${API_BASE_URL}/aiqe/runs/${runId}/events/stream?after_seq=${lastSeq.current}`,
        { withCredentials: true },
      )
      source.onopen = () => {
        if (cancelled) return
        setConnection('live')
        stopPolling()
      }
      source.onmessage = (event) => {
        try {
          append([JSON.parse(event.data) as AiqeRunEvent])
        } catch {
          // 忽略无法解析的心跳/脏消息
        }
      }
      source.onerror = () => {
        if (cancelled) return
        // 不 close：让浏览器按 retry 自动重连并携带 Last-Event-ID
        setConnection('polling')
        startPolling()
      }
    } catch {
      setConnection('polling')
      startPolling()
    }

    return () => {
      cancelled = true
      source?.close()
      stopPolling()
    }
  }, [runId])

  return { events, connection }
}
