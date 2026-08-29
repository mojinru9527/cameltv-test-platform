// StaleConflictBanner tests (V30-107)
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import { StaleConflictBanner } from '../StaleConflictBanner'

describe('StaleConflictBanner（V30-107 409 STALE）', () => {
  it('role=alert 呈现冲突提示并提供「刷新后重试」而非原样重试', () => {
    const onReload = vi.fn()
    render(<StaleConflictBanner onReload={onReload} />)
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByText(/409 STALE/)).toBeTruthy()
    const button = screen.getByRole('button', { name: '刷新后重试' })
    fireEvent.click(button)
    expect(onReload).toHaveBeenCalledTimes(1)
  })
})
