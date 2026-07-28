import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import {
  Badge,
  Button,
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Progress,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
  SkeletonCard,
  SkeletonCircle,
  SkeletonPage,
  SkeletonTable,
  SkeletonText,
  Textarea,
} from '@/ui'

afterEach(() => cleanup())

describe('semantic primitives', () => {
  it('keeps core controls styled in the default UI', () => {
    const { container } = render(
      <>
        <Button loading>保存</Button>
        <Input aria-label="名称" error="名称必填" disabled />
        <Badge tone="danger">失败</Badge>
        <Progress value={50} />
      </>,
    )

    const button = screen.getByRole('button', { name: '保存' })
    const input = screen.getByLabelText('名称') as HTMLInputElement
    expect(button.classList.contains('inline-flex')).toBe(true)
    expect(button.classList.contains('focus-visible:ring-3')).toBe(true)
    expect(button.getAttribute('aria-busy')).toBe('true')
    expect((button as HTMLButtonElement).disabled).toBe(true)
    expect(button.querySelector('.ui-spinner')?.classList.contains('animate-spin')).toBe(true)
    expect(input.classList.contains('border-input')).toBe(true)
    expect(input.classList.contains('aria-invalid:ring-3')).toBe(true)
    expect(input.getAttribute('aria-invalid')).toBe('true')
    expect(input.disabled).toBe(true)
    expect(screen.getByText('失败').classList.contains('bg-destructive/10')).toBe(true)

    const progress = screen.getByRole('progressbar')
    const indicator = container.querySelector('[data-slot="progress-indicator"]') as HTMLElement
    expect(progress.classList.contains('bg-muted')).toBe(true)
    expect(progress.getAttribute('aria-valuenow')).toBe('50')
    expect(indicator.style.transform).toBe('scaleX(0.5)')
    expect(indicator.style.width).toBe('')
  })

  it('keeps Obsidian selectors while rendering token fallbacks', () => {
    const { container } = render(
      <div data-theme="obsidian-flow">
        <Button variant="primary">运行</Button>
        <Input aria-label="环境" />
        <Badge tone="success">通过</Badge>
        <Progress value={25} tone="warning" />
        <Card>
          <CardContent>内容</CardContent>
        </Card>
        <Textarea aria-label="备注" />
        <Skeleton />
      </div>,
    )

    expect(screen.getByRole('button', { name: '运行' }).classList.contains('ui-btn-primary')).toBe(true)
    expect(screen.getByLabelText('环境').classList.contains('ui-input')).toBe(true)
    expect(screen.getByText('通过').classList.contains('ui-badge-success')).toBe(true)
    expect(container.querySelector('.ui-progress-fill.is-warning')).toBeTruthy()
    expect(container.querySelector('[data-slot="card"]')?.classList.contains('bg-card')).toBe(true)
    expect(screen.getByLabelText('备注').classList.contains('border-input')).toBe(true)
    expect(container.querySelector('[data-slot="skeleton"]')?.classList.contains('bg-muted')).toBe(true)
  })

  it.each(['xs', 'sm', 'icon', 'icon-sm', 'icon-xs'] as const)(
    'marks the %s button size for the coarse-pointer theme contract',
    (size) => {
      render(<Button size={size} aria-label={`${size} 操作`} />)

      const button = screen.getByRole('button', { name: `${size} 操作` })
      expect(button.classList.contains('ui-btn')).toBe(true)
      expect(button.classList.contains(`ui-btn-${size}`)).toBe(true)
      expect(button.classList.contains('touch-manipulation')).toBe(true)
    },
  )

  it('maps the strongly typed Badge compatibility variant without leaking it to the DOM', () => {
    render(
      <>
        <Badge tone="danger">兼容失败</Badge>
        <Badge tone="success" variant="destructive">优先通过</Badge>
      </>,
    )

    const compatible = screen.getByText('兼容失败')
    const preferred = screen.getByText('优先通过')
    expect(compatible.classList.contains('ui-badge-danger')).toBe(true)
    expect(compatible.hasAttribute('variant')).toBe(false)
    expect(preferred.classList.contains('ui-badge-success')).toBe(true)
  })

  it('preserves Card sizing and action slots', () => {
    const { container } = render(
      <Card size="sm">
        <CardHeader>
          <CardTitle>质量报告</CardTitle>
          <CardAction>导出</CardAction>
        </CardHeader>
        <CardContent>内容</CardContent>
      </Card>,
    )

    expect(container.querySelector('[data-slot="card"]')?.getAttribute('data-size')).toBe('sm')
    expect(container.querySelector('[data-slot="card-action"]')?.textContent).toBe('导出')
  })

  it('preserves Radix Select and Label semantics', () => {
    render(
      <>
        <Label htmlFor="environment">环境</Label>
        <Input id="environment" />
        <Select defaultValue="test">
          <SelectTrigger aria-label="运行环境">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="test">测试环境</SelectItem>
          </SelectContent>
        </Select>
      </>,
    )

    expect(screen.getByLabelText('环境').getAttribute('id')).toBe('environment')
    expect(screen.getByRole('combobox', { name: '运行环境' }).getAttribute('data-slot')).toBe('select-trigger')
  })

  it('preserves mature Textarea and Skeleton helper APIs', () => {
    const { container } = render(
      <>
        <Textarea aria-label="审核备注" aria-invalid="true" disabled />
        <SkeletonCircle />
        <SkeletonText lines={2} />
        <SkeletonCard />
        <SkeletonTable rows={1} cols={2} />
        <SkeletonPage />
      </>,
    )

    const textarea = screen.getByLabelText('审核备注')
    expect(textarea.getAttribute('data-slot')).toBe('textarea')
    expect(textarea.getAttribute('aria-invalid')).toBe('true')
    expect((textarea as HTMLTextAreaElement).disabled).toBe(true)
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(6)
    expect(container.querySelector('[data-slot="skeleton-card"]')).toBeTruthy()
  })
})
