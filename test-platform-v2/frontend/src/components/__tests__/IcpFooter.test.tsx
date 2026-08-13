import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import IcpFooter from '../IcpFooter'

describe('IcpFooter 备案号 footer', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('未配置 VITE_ICP_NUMBER 时不渲染', () => {
    vi.stubEnv('VITE_ICP_NUMBER', '')
    const { container } = render(<IcpFooter />)
    expect(container.firstChild).toBeNull()
  })

  it('配置备案号后展示备案号并链接工信部备案系统', () => {
    vi.stubEnv('VITE_ICP_NUMBER', '粤ICP备12345678号-1')
    render(<IcpFooter />)
    const link = screen.getByRole('link', { name: '粤ICP备12345678号-1' })
    expect(link.getAttribute('href')).toBe('https://beian.miit.gov.cn/')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toContain('noreferrer')
  })
})
