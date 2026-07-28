import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { X } from '@/lib/icons'
import { SpatialChain, type ChainNode } from '../SpatialChain'

afterEach(() => cleanup())

const nodes: ChainNode[] = [
  {
    id: 'requirements',
    label: '需求',
    shortLabel: '需求',
    count: '12',
    status: '已评审',
    progress: 75,
    tone: 'success',
    icon: X,
  },
  {
    id: 'defects',
    label: '缺陷',
    shortLabel: '缺陷',
    count: '2',
    status: '有风险',
    progress: 30,
    tone: 'risk',
    icon: X,
    risk: true,
    p0: true,
  },
]

describe('SpatialChain', () => {
  it.each(['chain', 'grid'] as const)('renders %s with semantic color tokens', (variant) => {
    const { container } = render(
      <SpatialChain nodes={nodes} activeId="requirements" variant={variant} />,
    )

    expect(screen.getByRole('button', { name: '需求：已评审' }).getAttribute('aria-pressed')).toBe('true')
    expect(container.innerHTML).toContain('var(--color-')
    expect(container.innerHTML).not.toMatch(/#[0-9a-f]{3,8}|rgba?\(/i)
    if (variant === 'chain') {
      expect(container.innerHTML).toContain('text-[var(--color-hover-text)]')
    }
  })

  it('uses readable semantic text for the empty state', () => {
    render(<SpatialChain nodes={[]} />)

    expect(screen.getByText('暂无链路数据').className).toContain('text-[var(--color-text-secondary)]')
  })
})
