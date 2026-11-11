import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import PlatformMatrix from '../PlatformMatrix'

const rows = [
  {
    ac_id: 'AC-001',
    ac_text: '直播入口在两端均可见',
    semantic_type: '跨端一致性',
    bindings: [
      {
        platform: 'web',
        build: 'web-1.2.3',
        device: 'Chrome 131',
        profile: 'core_isolated',
        actual: '入口可见',
        evidence: ['artifact:web-dom'],
      },
      {
        platform: 'h5',
        build: 'h5-2.0.1',
        device: 'iPhone 15',
        profile: 'integration',
        actual: '入口被广告遮挡',
        evidence: ['artifact:h5-shot'],
      },
    ],
  },
]

describe('PlatformMatrix', () => {
  it('展示同一 AC 的多端独立数据与语义类型', () => {
    render(<PlatformMatrix rows={rows} />)
    expect(screen.getByText('AC-001')).toBeTruthy()
    expect(screen.getByText('跨端一致性')).toBeTruthy()
    expect(screen.getByText('web-1.2.3 · Chrome 131 · core_isolated')).toBeTruthy()
    expect(screen.getByText('h5-2.0.1 · iPhone 15 · integration')).toBeTruthy()
    expect(screen.getByText('入口可见')).toBeTruthy()
    expect(screen.getByText('入口被广告遮挡')).toBeTruthy()
    expect(screen.getByText('artifact:web-dom')).toBeTruthy()
    expect(screen.getByText('artifact:h5-shot')).toBeTruthy()
  })

  it('缺失平台显示占位且空态可用', () => {
    render(
      <PlatformMatrix
        rows={[
          rows[0],
          {
            ac_id: 'AC-002',
            ac_text: '小程序入口',
            bindings: [
              {
                platform: 'miniapp',
                build: 'mp-1.0.0',
                device: 'WeChat 8.0',
                profile: 'core_isolated',
                actual: '可见',
                evidence: [],
              },
            ],
          },
        ]}
      />
    )
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    render(<PlatformMatrix rows={[]} />)
    expect(screen.getByText('暂无平台验收数据')).toBeTruthy()
  })
})
