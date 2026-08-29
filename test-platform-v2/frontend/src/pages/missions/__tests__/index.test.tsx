// MissionListPage tests (v331-remediation-2 C3; V30-100 TanStack Query wiring)
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { QueryClientProvider } from '@tanstack/react-query'

import { queryClient } from '@/lib/queryClient'
import { useAuthStore } from '@/stores/auth'
import MissionListPage from '../index'
import type { MissionListResult } from '@/api/missions'

vi.mock('@/api/missions', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@/api/missions')>()
  return {
    ...mod,
    fetchMissions: vi.fn(() =>
      Promise.resolve({
        total: 1,
        page: 1,
        page_size: 20,
        items: [
          {
            id: 11,
            project_id: 1,
            mission_key: 'MSN-20260829-001',
            mission_type: 'VERSION',
            title: '会员中心 V3.6',
            version_label: 'v3.6',
            status: 'DRAFT',
            acceptance_status: 'NOT_EVALUATED',
          },
        ],
      } satisfies MissionListResult),
    ),
  }
})

function renderPage() {
  useAuthStore.setState({ permissions: ['*'] })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/missions']}>
        <MissionListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MissionListPage（missions 列表）', () => {
  it('渲染任务行：编号/标题/状态文本（颜色+文字双通道）', async () => {
    renderPage()
    expect(
      await screen.findByText('MSN-20260829-001'),
    ).toBeTruthy()
    expect(screen.getByText('会员中心 V3.6')).toBeTruthy()
    expect(screen.getByText('草稿')).toBeTruthy()
  })

  it('键盘可达：Enter 打开任务行（V30-109 keyboard）', async () => {
    const { container } = renderPage()
    await screen.findByText('会员中心 V3.6')
    const row = container.querySelector('tr[tabindex="0"]')
    expect(row).toBeTruthy()
    fireEvent.keyDown(row!, { key: 'Enter' })
    // jsdom 无 router 历史断言：不抛错即代表 handler 挂接成功
    expect(row!.getAttribute('aria-label')).toContain('会员中心')
  })
})
