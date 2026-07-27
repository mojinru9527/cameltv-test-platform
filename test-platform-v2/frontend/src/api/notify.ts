import client from './client'

const BASE = '/notify'

// ── Types ──

export interface NotificationChannel {
  id: number
  project_id: number
  name: string
  channel_type: 'webhook' | 'email'
  provider?: string
  webhook_url?: string
  enabled: boolean
  events: string[]
  created_at: string
  updated_at?: string
}

export interface ChannelCreate {
  project_id?: number
  name: string
  channel_type: 'webhook' | 'email'
  provider?: string
  webhook_url?: string
  email_to?: string
  enabled?: boolean
  events?: string[]
}

export interface ChannelUpdate {
  name?: string
  provider?: string
  webhook_url?: string
  email_to?: string
  enabled?: boolean
  events?: string[]
}

// ── API Functions ──

export async function fetchChannels(): Promise<NotificationChannel[]> {
  return client.get(`${BASE}/channels`)
}

export async function createChannel(data: ChannelCreate): Promise<NotificationChannel> {
  return client.post(`${BASE}/channels`, data)
}

export async function updateChannel(id: number, data: ChannelUpdate): Promise<NotificationChannel> {
  return client.put(`${BASE}/channels/${id}`, data)
}

export async function deleteChannel(id: number): Promise<{ deleted: boolean }> {
  return client.delete(`${BASE}/channels/${id}`)
}

export async function testNotify(): Promise<{ sent: number; failed: number; skipped: number }> {
  return client.post(`${BASE}/test`, {})
}
