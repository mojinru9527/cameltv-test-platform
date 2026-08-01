export interface NotifyTestResult {
  sent: number
  failed: number
  skipped: number
}

export interface NotifyResultFeedback {
  level: 'success' | 'warning' | 'error'
  message: string
}

export function classifyNotifyTestResult(result: NotifyTestResult): NotifyResultFeedback {
  if (result.sent === 0 && result.failed === 0 && result.skipped === 0) {
    return { level: 'warning', message: '没有可测试的通知渠道' }
  }

  const message = `测试通知发送完成: 成功 ${result.sent}, 失败 ${result.failed}, 跳过 ${result.skipped}`
  if (result.failed > 0 || result.sent === 0) {
    return { level: 'error', message }
  }
  return { level: 'success', message }
}
