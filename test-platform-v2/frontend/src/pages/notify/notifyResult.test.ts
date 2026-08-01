import { describe, expect, it } from 'vitest'

import { classifyNotifyTestResult } from './notifyResult'

describe('classifyNotifyTestResult', () => {
  it('does not report success when no channel was exercised', () => {
    expect(classifyNotifyTestResult({ sent: 0, failed: 0, skipped: 0 })).toEqual({
      level: 'warning',
      message: '没有可测试的通知渠道',
    })
  })

  it('reports a partial failure when any delivery fails', () => {
    expect(classifyNotifyTestResult({ sent: 1, failed: 1, skipped: 0 })).toEqual({
      level: 'error',
      message: '测试通知发送完成: 成功 1, 失败 1, 跳过 0',
    })
  })

  it('reports success only when at least one delivery succeeds and none fail', () => {
    expect(classifyNotifyTestResult({ sent: 2, failed: 0, skipped: 1 })).toEqual({
      level: 'success',
      message: '测试通知发送完成: 成功 2, 失败 0, 跳过 1',
    })
  })
})
