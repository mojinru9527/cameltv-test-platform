import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CategoryManagerDialog from '../CategoryManagerDialog'
import type { TestCaseDomainCategory } from '@/api/testcase'

vi.mock('@/api/testcase', () => ({
  createDomain: vi.fn(),
  createModule: vi.fn(),
  deleteDomain: vi.fn(),
  deleteModule: vi.fn(),
}))

import { createDomain, createModule, deleteDomain, deleteModule } from '@/api/testcase'

const DOMAINS: TestCaseDomainCategory[] = [
  {
    id: 1,
    domain: '接口域',
    count: 3,
    modules: [
      { id: 10, module: '订单模块', count: 2 },
      { id: 11, module: '支付模块', count: 1 },
    ],
  },
  {
    id: 2,
    domain: '功能域',
    count: 0,
    modules: [],
  },
]

function renderDialog(overrides?: Partial<React.ComponentProps<typeof CategoryManagerDialog>>) {
  return render(
    <CategoryManagerDialog
      open
      domains={DOMAINS}
      onClose={vi.fn()}
      onChanged={vi.fn()}
      {...overrides}
    />,
  )
}

describe('CategoryManagerDialog（TPv2-B19-C1）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染域与模块及其用例数量', () => {
    renderDialog()
    expect(screen.getAllByText('接口域').length).toBeGreaterThan(0)
    fireEvent.click(screen.getAllByRole('button', { name: /接口域/ })[0])
    expect(screen.getByText('订单模块')).toBeTruthy()
    expect(screen.getByText('功能域')).toBeTruthy()
  })

  it('新增域调用 createDomain 并刷新', async () => {
    vi.mocked(createDomain).mockResolvedValue({} as never)
    const onChanged = vi.fn()
    renderDialog({ onChanged })

    fireEvent.change(screen.getByLabelText('新增域'), { target: { value: '新域' } })
    fireEvent.click(screen.getAllByRole('button', { name: '新增' })[0])

    await waitFor(() => expect(createDomain).toHaveBeenCalledWith('新域'))
    expect(onChanged).toHaveBeenCalled()
  })

  it('新增模块需要先选择所属域', async () => {
    renderDialog({ domains: [] })
    fireEvent.click(screen.getAllByRole('button', { name: '新增' })[1])

    await waitFor(() => expect(createModule).not.toHaveBeenCalled())
  })

  it('新增模块选中域后调用 createModule', async () => {
    vi.mocked(createModule).mockResolvedValue({} as never)
    renderDialog()

    fireEvent.change(screen.getByLabelText('新增模块'), { target: { value: '新模块' } })
    fireEvent.click(screen.getAllByRole('button', { name: '新增' })[1])

    await waitFor(() => expect(createModule).toHaveBeenCalledWith(1, '新模块'))
  })

  it('删除域需确认后调用 deleteDomain 并刷新', async () => {
    vi.mocked(deleteDomain).mockResolvedValue({} as never)
    const onChanged = vi.fn()
    renderDialog({ onChanged })

    fireEvent.click(screen.getByRole('button', { name: '删除域 接口域' }))
    await screen.findByText('确认删除域？')
    fireEvent.click(screen.getByRole('button', { name: '确认删除' }))

    await waitFor(() => expect(deleteDomain).toHaveBeenCalledWith(1))
    expect(onChanged).toHaveBeenCalled()
  })

  it('删除模块需确认后调用 deleteModule', async () => {
    vi.mocked(deleteModule).mockResolvedValue({} as never)
    renderDialog()

    fireEvent.click(screen.getAllByRole('button', { name: /接口域/ })[0])
    fireEvent.click(screen.getByRole('button', { name: '删除模块 订单模块' }))
    await screen.findByText('确认删除模块？')
    fireEvent.click(screen.getByRole('button', { name: '确认删除' }))

    await waitFor(() => expect(deleteModule).toHaveBeenCalledWith(1, 10))
  })

  it('分类缺少 ID 时提示并禁用删除（不产生 API 调用）', () => {
    renderDialog({
      domains: [
        { id: undefined as never, domain: '旧域', count: 1, modules: [] },
      ],
    })

    expect(screen.getByText(/分类接口尚未更新/)).toBeTruthy()
    expect(
      screen.getByRole('button', { name: '分类接口尚未更新，暂不能删除域' }),
    ).toHaveProperty('disabled', true)
  })
})
