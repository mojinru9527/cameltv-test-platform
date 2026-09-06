import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/hooks/useApi', () => ({
  default: () => ({
    data: [
      {
        id: 5,
        project_id: 1,
        name: 'Test5-接口',
        env_type: 'test',
        base_url: 'https://test5.example.internal',
        description: '内网接口环境',
        access_type: 'internal',
        execution_mode: 'runner',
        runner_key: 'test5-internal-01',
        created_at: null,
        updated_at: null,
      },
    ],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (state: { hasPerm: () => boolean }) => unknown) =>
    selector({ hasPerm: () => true }),
}))

vi.mock('@/api/environment', () => ({
  fetchEnvironments: vi.fn(),
  fetchVariables: vi.fn().mockResolvedValue([]),
  createEnvironment: vi.fn(),
  updateEnvironment: vi.fn(),
  deleteEnvironment: vi.fn(),
  createVariable: vi.fn(),
  updateVariable: vi.fn(),
  deleteVariable: vi.fn(),
}))

import EnvironmentPage from './index'

describe('Environment details', () => {
  it('shows the execution-critical environment configuration', async () => {
    render(<EnvironmentPage />)

    expect(await screen.findByText('https://test5.example.internal')).toBeTruthy()
    expect(screen.getByText('内网')).toBeTruthy()
    expect(screen.getByText('专属 Runner')).toBeTruthy()
    expect(screen.getByText('test5-internal-01')).toBeTruthy()
  })
})
