import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TeamProgress from '../team-progress'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function teamFixture(): Record<string, any> {
  return {
    id: 'team-abc',
    name: '登录模块回归团队',
    captainSessionId: 'cap-1',
    members: [
      { id: 'm1', name: 'product', role: '产品', status: 'active' },
      { id: 'm2', name: 'qa', role: '测试', status: 'active' },
    ],
    tasks: [
      { id: 't1', subject: 'PRD', status: 'completed', assignee: 'product' },
      { id: 't2', subject: '用例设计', status: 'completed', assignee: 'qa', dependencies: ['t1'] },
      { id: 't3', subject: '门禁回归', status: 'in_progress', assignee: 'qa', dependencies: ['t2'] },
    ],
    conclusion: '全部完成，回归通过。',
  }
}

describe('TeamProgress 团队进度树（Batch 191）', () => {
  it('渲染团队头、成员卡、任务列表与结论', () => {
    render(<TeamProgress teamJson={teamFixture()} status="running" outputText="" />)
    expect(screen.getByText('登录模块回归团队')).toBeTruthy()
    expect(screen.getByText('#team-abc')).toBeTruthy()
    // 团队头阶段 Badge（running → 执行中）；任务列表的「执行中」断言见下方 getAllByText
    // 成员卡：名字 + 角色 + 在队徽标（名字可能同时出现在任务 assignee 列 → getAllByText）
    expect(screen.getAllByText('product').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('产品')).toBeTruthy()
    expect(screen.getAllByText('qa').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('测试')).toBeTruthy()
    expect(screen.getAllByText('在队').length).toBe(2)
    // 任务列表：中文状态映射（RF-3 禁裸英文）
    expect(screen.getByText('PRD')).toBeTruthy()
    expect(screen.getByText('用例设计')).toBeTruthy()
    expect(screen.getByText('门禁回归')).toBeTruthy()
    // t1/t2 均为 completed → 「已完成」出现 2 次（getAllByText）
    expect(screen.getAllByText('已完成').length).toBe(2)
    // P3-1：'执行中' 有歧义（团队头阶段 + 任务 t3 状态各一处）→ 用 getAllByText 精确计数
    expect(screen.getAllByText('执行中').length).toBe(2)
    // 依赖展示
    expect(screen.getByText(/依赖 #t1/)).toBeTruthy()
    expect(screen.getByText(/依赖 #t2/)).toBeTruthy()
    // 结论
    expect(screen.getByText('团队结论')).toBeTruthy()
    expect(screen.getByText('全部完成，回归通过。')).toBeTruthy()
  })

  it('空 team_json 显示空态（无团队数据时）', () => {
    render(<TeamProgress teamJson={{}} status="running" outputText="" />)
    // 空对象不渲染成员/任务区；页面层在 team_json 为空时显示「等待船长建队」，
    // 组件本身不崩溃即可
    expect(screen.queryByTestId('team-progress')).toBeTruthy()
    expect(screen.queryByTestId('team-tasks')).toBeNull()
  })

  it('_truncated 标记显示截断提示', () => {
    const data = teamFixture()
    data._truncated = true
    render(<TeamProgress teamJson={data} status="running" outputText="" />)
    expect(screen.getByText('进度数据已截断')).toBeTruthy()
  })

  it('成员当前任务推导：首个 in_progress 且 assignee==成员 的任务', () => {
    render(<TeamProgress teamJson={teamFixture()} status="running" outputText="" />)
    // qa 的当前任务 = 门禁回归（in_progress 且 assignee=qa）
    expect(screen.getByText(/当前：门禁回归/)).toBeTruthy()
    // product 无 in_progress 任务 → 「—」
    expect(screen.getByText(/当前：—/)).toBeTruthy()
  })
})
