import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockFetchSkills = vi.fn()
const mockApplySkill = vi.fn()

vi.mock('@/api/knowledge', () => ({
  fetchSkills: (...args: unknown[]) => mockFetchSkills(...args),
  applySkill: (...args: unknown[]) => mockApplySkill(...args),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

describe('SkillsTab availability', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows the unavailable reason and prevents opening an unavailable Skill', async () => {
    mockFetchSkills.mockResolvedValue([{
      name: 'generate-testcases',
      label: '生成测试用例',
      description: '基于真实知识生成测试用例',
      icon: 'TestTube',
      category: '生成',
      input_params: [],
      available: false,
      unavailable_reason: 'AI_API_KEY 未配置',
    }])

    const { default: SkillsTab } = await import('./SkillsTab')
    render(<SkillsTab />)

    expect(await screen.findByText('0/1 个 AI 能力模板可用')).not.toBeNull()
    expect(screen.getByText('AI_API_KEY 未配置')).not.toBeNull()

    const card = screen.getByText('生成测试用例').closest('[data-slot="card"]')
    expect(card?.getAttribute('aria-disabled')).toBe('true')
    fireEvent.click(card!)

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(mockApplySkill).not.toHaveBeenCalled()
  })
})
