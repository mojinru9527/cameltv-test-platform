import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import Forbidden from '@/pages/Forbidden'
import { useAuthStore } from '@/stores/auth'

export default function RequireAuth({ children }: { children: ReactNode }) {
  // P1-1: token 不再持久化，登录态以 user 为准（鉴权走 httpOnly cookie）。
  // cookie 若失效，首个 API 请求会 401 → 拦截器登出并跳转登录。
  const user = useAuthStore((s) => s.user)
  const location = useLocation()
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return <>{children}</>
}

/**
 * 菜单权限路由守卫（batch-336）。
 *
 * 与后端 `require_permission("menu:aiqe_runs")` 对齐：无权限时渲染 403 页面，
 * 不发起页面级 API 请求；`*`（超级管理员）由 authStore.hasPerm 统一放行。
 */
export function RequirePermission({
  code,
  children,
}: {
  code: string
  children: ReactNode
}) {
  const user = useAuthStore((s) => s.user)
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const location = useLocation()
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  if (!hasPerm(code)) {
    return <Forbidden />
  }
  return <>{children}</>
}
