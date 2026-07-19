import { describe, expect, it } from 'vitest'

import {
  formatNumberedText,
  formatStepActions,
  formatStepExpectations,
  formatStepsForEditor,
  sortCasesNewestFirst,
} from '../caseListFormatters'

describe('用例列表内容格式化', () => {
  it('把换行文本和已有序号统一为中文序号', () => {
    expect(formatNumberedText('打开登录页\n输入账号密码')).toEqual([
      '1、打开登录页',
      '2、输入账号密码',
    ])
    expect(formatNumberedText('1. 准备账号\n2、准备验证码')).toEqual([
      '1、准备账号',
      '2、准备验证码',
    ])
  })

  it('把 JSON 步骤分别格式化为操作步骤和逐步预期', () => {
    const steps = JSON.stringify([
      { step: 1, desc: '打开登录页', expected: '登录页展示成功' },
      { step: 2, desc: '提交账号密码', expected: '登录成功并进入首页' },
    ])

    expect(formatStepActions(steps)).toEqual([
      '1、打开登录页',
      '2、提交账号密码',
    ])
    expect(formatStepExpectations(steps, '整体登录成功')).toEqual([
      '1、登录页展示成功',
      '2、登录成功并进入首页',
    ])
    expect(formatStepsForEditor(steps)).toBe('1、打开登录页\n2、提交账号密码')
  })

  it('兼容历史类 JSON 步骤并拆分操作与预期', () => {
    const steps = '[{step:1,desc:打开首页,expected:首页正常展示},{step:2,desc:点击推荐,expected:进入推荐列表}]'

    expect(formatStepActions(steps)).toEqual([
      '1、打开首页',
      '2、点击推荐',
    ])
    expect(formatStepExpectations(steps, '')).toEqual([
      '1、首页正常展示',
      '2、进入推荐列表',
    ])
  })

  it('步骤没有逐步预期时使用整体预期结果', () => {
    const steps = JSON.stringify([{ step: 1, desc: '打开首页' }])
    expect(formatStepExpectations(steps, '首页加载完成')).toEqual(['1、首页加载完成'])
  })

  it('部分步骤缺少预期时仍保持与操作步骤相同的编号', () => {
    const steps = JSON.stringify([
      { step: 1, desc: '第一步' },
      { step: 2, desc: '第二步', expected: '第二步成功' },
    ])
    expect(formatStepExpectations(steps, '')).toEqual([
      '1、-',
      '2、第二步成功',
    ])
  })

  it('最新创建的用例始终排在第一条', () => {
    const sorted = sortCasesNewestFirst([
      { id: 3, created_at: '2026-07-15T10:00:00' },
      { id: 9, created_at: '2026-07-16T08:00:00' },
      { id: 8, created_at: '2026-07-16T08:00:00' },
    ])
    expect(sorted.map((item) => item.id)).toEqual([9, 8, 3])
  })
})
