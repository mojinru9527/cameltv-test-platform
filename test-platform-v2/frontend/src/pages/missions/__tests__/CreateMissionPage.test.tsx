// CreateMissionPage tests (v331-remediation-2 C3)
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

import CreateMissionPage from '../CreateMissionPage'
import { createMission } from '@/api/missions'

vi.mock('@/api/missions', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@/api/missions')>()
  return {
    ...mod,
    createMission: vi.fn(() =>
      Promise.resolve({
        id: 42,
        project_id: 1,
        mission_key: 'MSN-20260829-042',
        mission_type: 'VERSION',
        title: '会员中心 V3.6',
        version_label: 'v3.6',
        status: 'DRAFT',
        acceptance_status: 'NOT_EVALUATED',
      }),
    ),
  }
})

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/missions/new']}>
      <CreateMissionPage />
    </MemoryRouter>,
  )
}

describe('CreateMissionPage（三步创建）', () => {
  beforeEach(() => {
    vi.mocked(createMission).mockClear()
  })

  it('任务名称为空时「下一步」不可用（V30-105 校验门）', () => {
    renderPage()
    const next = screen.getByRole('button', { name: '下一步' })
    expect((next as HTMLButtonElement).disabled).toBe(true)
  })

  it('填写名称 → 确认页展示输入 → 提交调用 createMission', async () => {
    renderPage()
    fireEvent.change(screen.getByLabelText('任务名称'), {
      target: { value: '会员中心 V3.6' },
    })
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    // 步骤条与卡片标题都含「确认信息」；用确认页专属文案断言
    expect(screen.getByText(/任务名称：/)).toBeTruthy()
    expect(screen.getByText('会员中心 V3.6')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))
    await waitFor(() => {
      expect(createMission).toHaveBeenCalledWith({
        title: '会员中心 V3.6',
        mission_type: 'VERSION',
        version_label: null,
      })
    })
  })
})
