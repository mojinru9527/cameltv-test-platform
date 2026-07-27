import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
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
