import api from './client'
import type { CrossProjectStats, DashboardStats, DashboardTodo } from '@/types'

export interface DashboardParams {
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
}

export async function fetchDashboardStats(
  params: DashboardParams = {},
  signal?: AbortSignal,
): Promise<DashboardStats> {
  return api.get('/dashboard/stats', { params, signal })
}

export async function fetchCrossProjectStats(
  params: DashboardParams = {},
  signal?: AbortSignal,
): Promise<CrossProjectStats> {
  return api.get('/dashboard/cross-project', { params, signal })
}


export async function fetchDashboardTodo(signal?: AbortSignal): Promise<DashboardTodo> {
  return api.get('/dashboard/todo', { signal })
}
