import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ThemeLab } from '../ThemeLab'

describe('ThemeLab', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('prefers-reduced-motion'),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  })

  it('switches all five themes without losing the active tab', () => {
    render(<ThemeLab />)

    fireEvent.click(screen.getByRole('tab', { name: /实时日志/ }))
    expect(screen.getByRole('tab', { name: /实时日志/ }).getAttribute('aria-selected')).toBe('true')

    fireEvent.click(screen.getByRole('button', { name: /黑域主题/ }))
    expect(document.querySelector('.theme-lab')?.getAttribute('data-theme')).toBe('xlab')
    fireEvent.click(screen.getByRole('button', { name: /列阵主题/ }))
    expect(document.querySelector('.theme-lab')?.getAttribute('data-theme')).toBe('column')
    fireEvent.click(screen.getByRole('button', { name: /软体主题/ }))
    expect(document.querySelector('.theme-lab')?.getAttribute('data-theme')).toBe('clay')
    fireEvent.click(screen.getByRole('button', { name: /液境主题/ }))
    expect(document.querySelector('.theme-lab')?.getAttribute('data-theme')).toBe('liquid')
    fireEvent.click(screen.getByRole('button', { name: /晶穹主题/ }))

    expect(screen.getByRole('tab', { name: /实时日志/ }).getAttribute('aria-selected')).toBe('true')
  })

  it('reuses existing interactions from the liquid component panorama', () => {
    render(<ThemeLab />)
    fireEvent.click(screen.getByRole('button', { name: /液境主题/ }))

    expect(screen.getByRole('region', { name: '液态组件全景' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '演示轻提示' }))
    expect(screen.getByText('液态玻璃轻提示已就绪')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '演示背景幕布' }))
    expect(screen.getByRole('dialog', { name: '启动回归确认' })).toBeTruthy()
  })

  it('shows skeleton feedback and a single snackbar', () => {
    vi.useFakeTimers()
    render(<ThemeLab />)

    fireEvent.click(screen.getByRole('button', { name: '模拟加载' }))
    expect(screen.getByLabelText('正在加载质量数据')).toBeTruthy()

    act(() => vi.advanceTimersByTime(950))
    expect(screen.getByText('质量数据已刷新')).toBeTruthy()
    expect(screen.getAllByRole('status')).toHaveLength(1)

    vi.useRealTimers()
  })

  it('confirms a regression run through a modal backdrop', () => {
    render(<ThemeLab />)

    fireEvent.click(screen.getByRole('button', { name: '启动回归' }))
    expect(screen.getByRole('dialog', { name: '启动回归确认' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '确认启动' }))
    expect(screen.queryByRole('dialog', { name: '启动回归确认' })).toBeNull()
    expect(screen.getByText(/正在编排新的回归批次/)).toBeTruthy()
  })

  it('opens the command palette with Ctrl+K', () => {
    render(<ThemeLab />)

    fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
    expect(screen.getByRole('dialog', { name: '全局命令面板' })).toBeTruthy()
    expect(screen.getByLabelText('搜索全局命令')).toBeTruthy()
  })
})
