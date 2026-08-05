import { describe, expect, it } from 'vitest'
import {
  jobStatusLabel,
  jobStatusTone,
  stageLabel,
  pageCaptureLabel,
  pageOcrLabel,
  reviewStatusLabel,
} from './labels'

describe('lanhu evidence labels', () => {
  it('job status 全映射中文', () => {
    expect(jobStatusLabel('pending')).toBe('排队中')
    expect(jobStatusLabel('running')).toBe('采集中')
    expect(jobStatusLabel('success')).toBe('成功')
    expect(jobStatusLabel('success_with_warnings')).toBe('成功(有告警)')
    expect(jobStatusLabel('failed')).toBe('失败')
    expect(jobStatusLabel('cancelled')).toBe('已取消')
    expect(jobStatusLabel('unknown')).toBe('unknown')
  })

  it('job status tone 语义化', () => {
    expect(jobStatusTone('success')).toBe('success')
    expect(jobStatusTone('failed')).toBe('danger')
    expect(jobStatusTone('success_with_warnings')).toBe('warning')
    expect(jobStatusTone('running')).toBe('info')
    expect(jobStatusTone('pending')).toBe('neutral')
    expect(jobStatusTone('cancelled')).toBe('neutral')
  })

  it('stage 全映射中文', () => {
    expect(stageLabel('queued')).toBe('排队中')
    expect(stageLabel('discovering')).toBe('发现页面')
    expect(stageLabel('capturing')).toBe('截图中')
    expect(stageLabel('exporting')).toBe('导出中')
    expect(stageLabel('done')).toBe('已完成')
    expect(stageLabel('weird')).toBe('weird')
  })

  it('页面捕获/OCR/审核映射', () => {
    expect(pageCaptureLabel('success')).toBe('已捕获')
    expect(pageCaptureLabel('failed')).toBe('失败')
    expect(pageCaptureLabel('skipped')).toBe('跳过')
    expect(pageOcrLabel('success')).toBe('已识别')
    expect(pageOcrLabel('unavailable')).toBe('无文本(待审核)')
    expect(pageOcrLabel('pending')).toBe('待处理')
    expect(reviewStatusLabel('pending')).toBe('待审核')
    expect(reviewStatusLabel('approved')).toBe('已通过')
    expect(reviewStatusLabel('rejected')).toBe('已驳回')
  })
})
