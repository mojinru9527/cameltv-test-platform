/**
 * AITDE V3/V4 功能开关（运行时解析）。
 *
 * 历史缺陷（V4.0 生产黑盒复盘 P0-1）：本文件原先只导出构建期常量
 * `import.meta.env.VITE_AITDE_V3_ENABLED === 'true'`，而 `frontend/Dockerfile`
 * 与 `deploy/docker-compose.yml` 从未声明/透传该构建参数 —— 前端因此**永远**为 false，
 * 即使后端 `AITDE_V3_ENABLED=true`（菜单可见、`/api/v2` 可用）也只能看到「未开放」占位。
 *
 * 根治方式：**以后端为唯一事实源**。后端 `GET /api/v2/health` 不受特性门控影响，
 * 始终返回 `{ status, aitde_v3_enabled }`（见 `backend/app/api/v2/router.py`）。
 * 前端在运行时读取该值，从根上消除「前后端开关不一致」这一类缺陷。
 *
 * 构建期变量降级为**可选覆盖**（本地开发/演示用）：
 *   - `VITE_AITDE_V3_ENABLED=true`  → 强制开启，不请求后端
 *   - `VITE_AITDE_V3_ENABLED=false` → 强制关闭，不请求后端
 *   - 未设置（默认）                → 跟随后端 `/api/v2/health`
 */
import { useEffect, useState } from 'react'

/** 构建期覆盖：'true' | 'false' | undefined（未设置 = 跟随后端）。 */
const BUILD_OVERRIDE_RAW = import.meta.env.VITE_AITDE_V3_ENABLED

export const AITDE_V3_BUILD_OVERRIDE: boolean | null =
  BUILD_OVERRIDE_RAW === 'true' ? true : BUILD_OVERRIDE_RAW === 'false' ? false : null

export type AitdeV3State = 'loading' | 'enabled' | 'disabled' | 'unknown'

/** 进程内缓存：一次会话只探测一次，避免每条路由都打一次 health。 */
let cachedState: AitdeV3State = AITDE_V3_BUILD_OVERRIDE === null
  ? 'loading'
  : AITDE_V3_BUILD_OVERRIDE
    ? 'enabled'
    : 'disabled'
let inflight: Promise<AitdeV3State> | null = null
const subscribers = new Set<(s: AitdeV3State) => void>()

function publish(next: AitdeV3State) {
  cachedState = next
  subscribers.forEach((fn) => fn(next))
}

/** 读取当前已解析状态（同步，可能是 'loading'）。 */
export function getAitdeV3State(): AitdeV3State {
  return cachedState
}

/**
 * 解析 AITDE 开关。构建期有显式覆盖时直接返回；否则探测后端 health。
 * 后端不可达时返回 'unknown'——**不静默当作关闭**，由 UI 区分「未开放」与「探测失败」。
 */
export function resolveAitdeV3(): Promise<AitdeV3State> {
  if (AITDE_V3_BUILD_OVERRIDE !== null) {
    return Promise.resolve(AITDE_V3_BUILD_OVERRIDE ? 'enabled' : 'disabled')
  }
  if (cachedState === 'enabled' || cachedState === 'disabled') {
    return Promise.resolve(cachedState)
  }
  if (inflight) return inflight

  inflight = fetch('/api/v2/health', {
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`health ${r.status}`))))
    .then((body: { aitde_v3_enabled?: boolean }) => {
      const next: AitdeV3State = body?.aitde_v3_enabled === true ? 'enabled' : 'disabled'
      publish(next)
      return next
    })
    .catch(() => {
      publish('unknown')
      return 'unknown' as AitdeV3State
    })
    .finally(() => {
      inflight = null
    })

  return inflight
}

/** React 订阅入口。首次挂载时触发解析。 */
export function useAitdeV3State(): AitdeV3State {
  const [state, setState] = useState<AitdeV3State>(cachedState)

  useEffect(() => {
    let cancelled = false
    subscribers.add(setState)
    // 'unknown' 允许重试（例如后端刚恢复）
    if (cachedState === 'loading' || cachedState === 'unknown') {
      resolveAitdeV3().then((s) => {
        if (!cancelled) setState(s)
      })
    } else {
      setState(cachedState)
    }
    return () => {
      cancelled = true
      subscribers.delete(setState)
    }
  }, [])

  return state
}

/** 仅供测试重置内部缓存。 */
export function __resetAitdeV3CacheForTests(next: AitdeV3State = 'loading') {
  cachedState = next
  inflight = null
  subscribers.clear()
}

/**
 * 便捷布尔入口：仅当后端明确开启时为 true。
 * 'loading' / 'unknown' 一律视为未开启，避免在未确认前渲染 AITDE 专属内容。
 * 需要区分三态的场景（如路由占位页）请直接用 `useAitdeV3State`。
 */
export function useAitdeV3Enabled(): boolean {
  return useAitdeV3State() === 'enabled'
}
