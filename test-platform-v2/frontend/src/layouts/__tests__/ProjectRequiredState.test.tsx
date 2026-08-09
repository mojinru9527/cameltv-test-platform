import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ProjectRequiredState from '../ProjectRequiredState'

describe('无项目引导', () => {
  it('有自助创建权限时明确引导创建第一个项目', () => {
    const openProjects = vi.fn()
    render(<ProjectRequiredState canCreateProject onOpenProjects={openProjects} />)

    expect(screen.getByRole('heading', { name: '先创建一个项目' })).toBeTruthy()
    expect(screen.getByText('2. 创建项目')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '创建第一个项目' }))
    expect(openProjects).toHaveBeenCalledTimes(1)
  })

  it('无自助创建权限时提示联系管理员加入项目', () => {
    render(<ProjectRequiredState canCreateProject={false} onOpenProjects={vi.fn()} />)

    expect(screen.getByRole('heading', { name: '还没有可用项目' })).toBeTruthy()
    expect(screen.getByText(/联系管理员/)).toBeTruthy()
  })
})
