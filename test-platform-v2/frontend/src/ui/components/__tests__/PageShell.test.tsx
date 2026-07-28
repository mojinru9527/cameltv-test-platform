import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PageShell } from '../PageShell'

describe('PageShell', () => {
  it('renders one page heading and a responsive action group', () => {
    render(
      <PageShell
        title="缺陷管理"
        description="追踪质量缺陷"
        actions={<button type="button">新建</button>}
      >
        <div>列表</div>
      </PageShell>,
    )

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
    expect(screen.getByRole('heading', { name: '缺陷管理' })).toBeTruthy()
    expect(screen.getByTestId('page-shell-actions').className).toContain('flex-wrap')
    expect(screen.getByText('列表')).toBeTruthy()
  })

  it('uses semantic theme classes instead of fixed colors', () => {
    const { container } = render(
      <PageShell title="环境配置" description="管理测试环境">
        <div>内容</div>
      </PageShell>,
    )

    const header = container.querySelector('header')
    expect(header?.className).toContain('bg-card')
    expect(header?.className).toContain('text-card-foreground')
    expect(screen.getByRole('heading').className).toContain('text-foreground')
  })
})
