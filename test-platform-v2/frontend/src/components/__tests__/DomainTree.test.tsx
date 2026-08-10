import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import DomainTree from '../DomainTree'

describe('DomainTree', () => {
  it('renders accounting-only nodes without making them selectable', () => {
    const onSelect = vi.fn()
    render(
      <DomainTree
        treeData={[
          {
            key: 'faq',
            title: 'FAQ帮助 (27)',
            children: [
              {
                key: 'faq-direct',
                title: '直属用例 (18)',
                isLeaf: true,
                selectable: false,
                ariaLabel: 'FAQ帮助直属用例 18 条，仅用于数量核算',
              },
              { key: 'faq-content', title: 'faq内容 (5)', isLeaf: true },
            ],
          },
        ]}
        onSelect={onSelect}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /FAQ帮助/ }))
    expect(screen.getByText('直属用例 (18)')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /直属用例/ })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /faq内容/ }))
    expect(onSelect).toHaveBeenLastCalledWith(['faq-content'])
  })
})
