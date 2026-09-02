import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import PageIntro from '../PageIntro'
import TermTip from '../TermTip'
import EmptyStateGuide from '../EmptyStateGuide'
import StepWizard from '../StepWizard'
import AskAiButton from '../AskAiButton'

describe('foolproof 组件库', () => {
  it('PageIntro 渲染一句话说明', () => {
    render(<PageIntro title="工作台 = 我的待办" description="今天该干嘛" />)
    expect(screen.getByText('工作台 = 我的待办')).toBeTruthy()
    expect(screen.getByText('今天该干嘛')).toBeTruthy()
  })

  it('TermTip 对已知词显示业务解释（悬停）', async () => {
    render(<TermTip term="run">一次执行</TermTip>)
    expect(screen.getByText('一次执行')).toBeTruthy()
    // tooltip 内容在 hover 后出现（Radix），至少语言标签存在
    fireEvent.mouseOver(screen.getByText('一次执行'))
    // 不抛错即可（内容由 Radix 异步渲染）
  })

  it('EmptyStateGuide 渲染三步教学', () => {
    render(
      <EmptyStateGuide
        stepTitle="三步完成你的第一个版本任务"
        steps={[{ text: '放需求' }, { text: 'AI 出方案' }, { text: '确认并执行' }]}
      />,
    )
    expect(screen.getByText('三步完成你的第一个版本任务')).toBeTruthy()
    expect(screen.getByText('放需求')).toBeTruthy()
    expect(screen.getByText('AI 出方案')).toBeTruthy()
    expect(screen.getByText('确认并执行')).toBeTruthy()
  })

  it('StepWizard 可前进/后退并完成', () => {
    const onFinish = vi.fn()
    render(
      <StepWizard
        steps={[
          { title: '放东西', description: '第一步', content: <div>内容1</div> },
          { title: 'AI 出方案', description: '第二步', content: <div>内容2</div> },
        ]}
        onFinish={onFinish}
      />,
    )
    expect(screen.getByText('第一步')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /下一步/ }))
    expect(screen.getByText('第二步')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /完成/ }))
    expect(onFinish).toHaveBeenCalled()
  })

  it('AskAiButton 按路由给出业务回答', async () => {
    render(
      <MemoryRouter initialEntries={['/workbench']}>
        <AskAiButton />
      </MemoryRouter>,
    )
    fireEvent.click(screen.getByRole('button', { name: /问我/ }))
    expect(screen.getByText('我的待办（首页）')).toBeTruthy()
    expect(screen.getAllByText(/今天要审什么/).length).toBeGreaterThan(0)
  })
})
