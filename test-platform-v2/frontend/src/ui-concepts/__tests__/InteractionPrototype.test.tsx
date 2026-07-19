import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { InteractionPrototype } from '../InteractionPrototype'

describe('InteractionPrototype', () => {
  it('keeps the active work surface while comparing both concepts', () => {
    render(<InteractionPrototype />)

    fireEvent.click(screen.getByRole('button', { name: '用例服务' }))
    expect(screen.getByRole('heading', { name: '用例服务' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /方案二/ }))
    expect(screen.getByRole('heading', { name: '用例服务' })).toBeTruthy()
    expect(screen.getByText('深色运维指挥台')).toBeTruthy()
  })

  it('supports operations controls and environment confirmation', () => {
    render(<InteractionPrototype />)

    fireEvent.click(screen.getByRole('button', { name: /方案二/ }))
    fireEvent.click(screen.getByRole('button', { name: '运行中心' }))
    fireEvent.click(screen.getByRole('button', { name: '暂停' }))
    expect(screen.getByRole('button', { name: '继续' })).toBeTruthy()

    fireEvent.change(screen.getByLabelText('执行环境'), { target: { value: '生产环境' } })
    expect(screen.getByRole('dialog', { name: '切换到生产环境' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '确认切换' }))
    expect(screen.getByDisplayValue('生产环境')).toBeTruthy()
  })

  it('opens the command palette with the platform shortcut', () => {
    vi.spyOn(navigator, 'platform', 'get').mockReturnValue('Win32')
    render(<InteractionPrototype />)

    fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
    expect(screen.getByRole('dialog', { name: '全局命令' })).toBeTruthy()
  })
})
