import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AsyncState } from '../AsyncState'

describe('AsyncState production loading contract', () => {
  it('uses a structure-preserving skeleton for the default initial load', () => {
    render(
      <AsyncState
        isLoading
        isError={false}
        error={null}
        data={undefined}
      >
        {() => <div>已加载</div>}
      </AsyncState>,
    )

    const loading = screen.getByRole('status', { name: '加载中' })
    expect(loading.getAttribute('aria-busy')).toBe('true')
    expect(loading.querySelector('.animate-spin')).toBeNull()
  })
})
