import api from './client'
import type { DashboardStats } from '@/types'

export interface DashboardParams {
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
}

export async function fetchDashboardStats(params: DashboardParams = {}): Promise<DashboardStats> {
  return api.get('/dashboard/stats', { params })
}
