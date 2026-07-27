import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchMetrics } from '@/api/perftest'
import type { MetricDataPoint } from '@/api/perftest'

// 从 JWT token 中提取（与 Axios client 一致）
function getJwtToken(): string {
  const raw = localStorage.getItem('auth-storage')
  if (!raw) return ''
  try {
    const state = JSON.parse(raw)?.state
    return state?.token ?? ''
  } catch {
    return ''
  }
}

type ConnectionMode = 'websocket' | 'polling' | 'disconnected'

interface UsePerfWebSocketOptions {
  sessionId: number
  enabled: boolean                     // 是否开始连接
  onSnapshot?: (point: MetricDataPoint) => void
  onEvent?: (event: { event_type: string; detail: string }) => void
  onEnd?: (reason: string) => void
}

export function usePerfWebSocket({
  sessionId,
  enabled,
  onSnapshot,
  onEvent,
  onEnd,
}: UsePerfWebSocketOptions) {
  const [mode, setMode] = useState<ConnectionMode>('disconnected')
  const [reconnectCount, setReconnectCount] = useState(0)
  // Refs for values read inside useCallback callbacks, avoiding stale-closure
  // and the SET-state-in-deps cascade (engineering-standards §4.2)
  const modeRef = useRef(mode)
  const reconnectCountRef = useRef(reconnectCount)
  const wsRef = useRef<WebSocket | null>(null)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastTsRef = useRef(0)
  const reconnectTimersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  // Keep refs in sync with state so callbacks always read latest values
  useEffect(() => { modeRef.current = mode }, [mode])
  useEffect(() => { reconnectCountRef.current = reconnectCount }, [reconnectCount])

  const cleanup = useCallback(() => {
    // 清理 WebSocket
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    // 清理轮询
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
    // 清理重连定时器
    reconnectTimersRef.current.forEach(clearTimeout)
    reconnectTimersRef.current = []
    lastTsRef.current = 0
  }, [])

  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return
    setMode('polling')
    lastTsRef.current = 0

    const poll = async () => {
      try {
        const data = await fetchMetrics(sessionId, lastTsRef.current)
        for (const pt of data.metrics) {
          lastTsRef.current = Math.max(lastTsRef.current, pt.timestamp)
          onSnapshot?.(pt)
        }
      } catch {
        // 静默失败，下次轮询继续
      }
    }

    poll() // 立即拉一次
    pollTimerRef.current = setInterval(poll, 500)
  }, [sessionId, onSnapshot])

  const connectWebSocket = useCallback(() => {
    if (wsRef.current) return

    const token = getJwtToken()
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host

    try {
      const ws = new WebSocket(
        `${protocol}//${host}/api/v1/perf-sessions/${sessionId}/stream?token=${token}`,
      )
      wsRef.current = ws

      ws.onopen = () => {
        setMode('websocket')
        setReconnectCount(0)
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'metrics_snapshot') {
            onSnapshot?.({
              timestamp: msg.timestamp,
              elapsed_s: msg.elapsed_s,
              values: msg.metrics,
            })
          } else if (msg.type === 'session_end') {
            onEnd?.(msg.reason)
            cleanup()
            setMode('disconnected')
          } else if (msg.type === 'event') {
            onEvent?.(msg.event)
          }
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = () => {
        wsRef.current = null
        // Read from refs to avoid stale-closure on mode/reconnectCount
        if (modeRef.current === 'websocket' && reconnectCountRef.current < 3) {
          // 自动重连（指数退避: 1s, 2s, 4s）
          const delay = Math.min(1000 * Math.pow(2, reconnectCountRef.current), 4000)
          setReconnectCount((c) => c + 1)
          const timer = setTimeout(() => connectWebSocket(), delay)
          reconnectTimersRef.current.push(timer)
        } else {
          // 重连耗尽，降级为轮询
          startPolling()
        }
      }

      ws.onerror = () => {
        wsRef.current?.close()
        wsRef.current = null
        // 立即降级轮询
        startPolling()
      }
    } catch {
      // WebSocket 构造函数失败，直接降级
      startPolling()
    }
    // mode and reconnectCount read via refs — NOT in deps (engineering-standards §4.2)
  }, [sessionId, onSnapshot, onEnd, onEvent, cleanup, startPolling])

  useEffect(() => {
    if (!enabled || !sessionId) {
      cleanup()
      setMode('disconnected')
      return
    }

    connectWebSocket()
    return cleanup
    // connectWebSocket excluded deliberately: it's stable (no SET-state deps)
  }, [enabled, sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  return { mode, reconnectCount }
}
