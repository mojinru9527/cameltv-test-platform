import { QueryClient } from '@tanstack/react-query'

/**
 * V30-100：AITDE TanStack Query 基础设施。
 *
 * 工程规范（docs/engineering-standards.md §4）：每个 GET 只允许 1 次有效请求，
 * 因此关闭 refetchOnWindowFocus / retry —— 失败交由调用方 toast + 手动重试，
 * 不做静默自动重发。
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
    mutations: {
      retry: false,
    },
  },
})

/** Query key 工厂：missions 域（v331-remediation-2 B3）。 */
export const missionKeys = {
  all: ['missions'] as const,
  list: (filters: { keyword?: string; status?: string; page?: number }) =>
    ['missions', 'list', filters] as const,
  detail: (id: number) => ['missions', 'detail', id] as const,
}
