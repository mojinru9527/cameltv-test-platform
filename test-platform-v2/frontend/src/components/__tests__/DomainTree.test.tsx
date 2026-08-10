import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import DomainTree from '../DomainTree'

describe('DomainTree', () => {
  it('renders accounting rows as clickable but visually distinct', () => {
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
                isAccounting: true,
                ariaLabel: 'FAQ帮助直属用例 18 条，点击查看并编辑',
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

    // Batch 132: 直属核算行可点击进入直属用例列表（查看/编辑）
    fireEvent.click(screen.getByRole('button', { name: /直属用例/ }))
    expect(onSelect).toHaveBeenLastCalledWith(['faq-direct'])

    fireEvent.click(screen.getByRole('button', { name: /faq内容/ }))
    expect(onSelect).toHaveBeenLastCalledWith(['faq-content'])
  })
})
