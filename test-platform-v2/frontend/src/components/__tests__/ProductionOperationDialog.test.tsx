import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ProductionOperationDialog from '../ProductionOperationDialog'

const productionProps = {
  open: true,
  onOpenChange: vi.fn(),
  project: '业务直播平台',
  environment: '生产环境',
  baseUrl: 'https://api.example.com',
  operation: '发送 POST /matches 请求',
  classification: 'write' as const,
  affectedCount: 1,
  isProduction: true,
  onConfirm: vi.fn(),
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ProductionOperationDialog', () => {
  it('shows the complete operation target and a clear production warning', () => {
    render(<ProductionOperationDialog {...productionProps} />)

    expect(screen.getByRole('alertdialog', { name: '确认生产环境操作' })).toBeTruthy()
    expect(screen.getByText('业务直播平台')).toBeTruthy()
    expect(screen.getByText('生产环境')).toBeTruthy()
    expect(screen.getByText('https://api.example.com')).toBeTruthy()
    expect(screen.getByText('发送 POST /matches 请求')).toBeTruthy()
    expect(screen.getByText('写操作')).toBeTruthy()
    expect(screen.getByText('1 个资源')).toBeTruthy()
    expect(screen.getByText(/将向真实生产服务发送请求/)).toBeTruthy()
  })

  it('never preselects production acknowledgement and resets it after reopening', () => {
    const { rerender } = render(<ProductionOperationDialog {...productionProps} />)
    const acknowledgement = screen.getByRole('checkbox', { name: /我已核对以上生产目标/ })
    const confirm = screen.getByRole('button', { name: '确认执行生产操作' })

    expect(acknowledgement.getAttribute('data-state')).toBe('unchecked')
    expect(confirm).toHaveProperty('disabled', true)

    fireEvent.click(acknowledgement)
    expect(confirm).toHaveProperty('disabled', false)

    rerender(<ProductionOperationDialog {...productionProps} open={false} />)
    rerender(<ProductionOperationDialog {...productionProps} open />)

    expect(screen.getByRole('checkbox', { name: /我已核对以上生产目标/ }).getAttribute('data-state')).toBe('unchecked')
    expect(screen.getByRole('button', { name: '确认执行生产操作' })).toHaveProperty('disabled', true)
  })

  it('does not allow Enter to submit before or after acknowledgement', () => {
    const onConfirm = vi.fn()
    render(<ProductionOperationDialog {...productionProps} onConfirm={onConfirm} />)
    const dialog = screen.getByRole('alertdialog')

    fireEvent.keyDown(dialog, { key: 'Enter', code: 'Enter' })
    fireEvent.click(screen.getByRole('checkbox', { name: /我已核对以上生产目标/ }))
    fireEvent.keyDown(dialog, { key: 'Enter', code: 'Enter' })

    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('labels a test-environment operation without requiring production acknowledgement', () => {
    const onConfirm = vi.fn()
    render(
      <ProductionOperationDialog
        {...productionProps}
        environment="Test5 测试环境"
        baseUrl="https://test5.example.com"
        operation="读取模块列表"
        classification="read"
        affectedCount={12}
        isProduction={false}
        onConfirm={onConfirm}
      />,
    )

    expect(screen.getByRole('alertdialog', { name: '确认测试环境操作' })).toBeTruthy()
    expect(screen.getByText('读操作')).toBeTruthy()
    expect(screen.getByText('12 个资源')).toBeTruthy()
    expect(screen.getByText(/这是测试环境操作/)).toBeTruthy()
    expect(screen.queryByRole('checkbox')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '确认执行测试操作' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })
})
