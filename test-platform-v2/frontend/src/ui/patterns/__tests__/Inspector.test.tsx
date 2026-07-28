import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Inspector } from '../Inspector'

afterEach(() => cleanup())

describe('Inspector', () => {
  it('keeps the panel within the viewport and exposes a 44px close target', () => {
    render(<Inspector open onClose={vi.fn()} title="执行详情" />)

    const dialog = screen.getByRole('dialog', { name: '执行详情' })
    const panel = dialog.querySelector<HTMLElement>('[tabindex="-1"]')
    const closeButton = screen.getByRole('button', { name: '关闭检查器' })

    expect(panel).toBeTruthy()
    expect(panel?.classList.contains('w-[min(100vw,380px)]')).toBe(true)
    expect(panel?.classList.contains('max-w-full')).toBe(true)
    expect(closeButton.classList.contains('size-11')).toBe(true)
  })

  it('traps Tab focus inside the panel', () => {
    render(
      <Inspector
        open
        onClose={vi.fn()}
        title="执行详情"
        actions={(
          <>
            <button type="button">取消</button>
            <button type="button">保存</button>
          </>
        )}
      />,
    )

    const dialog = screen.getByRole('dialog', { name: '执行详情' })
    const panel = dialog.querySelector<HTMLElement>('[tabindex="-1"]')
    const closeButton = screen.getByRole('button', { name: '关闭检查器' })
    const saveButton = screen.getByRole('button', { name: '保存' })

    expect(document.activeElement).toBe(panel)

    fireEvent.keyDown(panel!, { key: 'Tab' })
    expect(document.activeElement).toBe(closeButton)

    fireEvent.keyDown(closeButton, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(saveButton)

    fireEvent.keyDown(saveButton, { key: 'Tab' })
    expect(document.activeElement).toBe(closeButton)
  })

  it('closes with Escape and restores focus to the opener', () => {
    const opener = document.createElement('button')
    opener.textContent = '外部触发器'
    document.body.appendChild(opener)
    opener.focus()

    const onClose = vi.fn()
    const { rerender } = render(<Inspector open onClose={onClose} title="执行详情" />)
    const dialog = screen.getByRole('dialog', { name: '执行详情' })

    fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)

    rerender(<Inspector open={false} onClose={onClose} title="执行详情" />)
    expect(document.activeElement).toBe(opener)
    opener.remove()
  })

  it('renders semantic theme tokens without embedded color literals', () => {
    const { container } = render(
      <Inspector
        open
        onClose={vi.fn()}
        title="执行详情"
        subtitle="API 回归"
        metrics={[{ label: '通过率', value: '98%', note: '较昨日 +2%' }]}
        summary="回归执行稳定。"
        progress={98}
        actions={<button type="button">查看报告</button>}
      />,
    )

    expect(container.innerHTML).toContain('var(--color-')
    expect(container.innerHTML).not.toMatch(/#[0-9a-f]{3,8}|rgba?\(/i)
  })
})
