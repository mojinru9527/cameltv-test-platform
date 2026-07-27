import api from './client'
import type { CrossProjectStats, DashboardStats } from '@/types'

export interface DashboardParams {
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
}

export async function fetchDashboardStats(params: DashboardParams = {}): Promise<DashboardStats> {
  return api.get('/dashboard/stats', { params })
}

export async function fetchCrossProjectStats(params: DashboardParams = {}): Promise<CrossProjectStats> {
  return api.get('/dashboard/cross-project', { params })
}
