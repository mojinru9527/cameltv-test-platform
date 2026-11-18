import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  createImpactPlan: vi.fn(),
  createBenchmarkDataset: vi.fn(),
  addBenchmarkSample: vi.fn(),
  freezeBenchmarkDataset: vi.fn(),
  getBenchmarkRun: vi.fn(),
  runLlmBenchmark: vi.fn(),
}))

vi.mock('@/api/aiqeInsights', () => api)

const { default: ImpactPage } = await import('@/pages/aiqe/impact')
const { default: BenchmarksPage } = await import('@/pages/aiqe/benchmarks')

const renderPage = (node: ReactNode) => render(<MemoryRouter>{node}</MemoryRouter>)

describe('ImpactPage', () => {
  beforeEach(() => {
    Object.values(api).forEach((fn) => fn.mockReset())
  })

  it('renders components, mandatory cases and trace paths', async () => {
    api.createImpactPlan.mockResolvedValue({
      base_sha: 'a'.repeat(40),
      head_sha: 'b'.repeat(40),
      changed_files: [{ path: 'app/api.py', status: 'M', added: 3, removed: 1 }],
      components: ['sports:api'],
      changed_symbols: {},
      changed_routes: ['GET /sports'],
      changed_migrations: [],
      mandatory_case_ids: ['TC-P0-1'],
      candidates: [
        {
          case_id: 'TC-P2-1',
          score: 0.6,
          reason: 'AC_LINKED',
          trace_path: 'sports:api → AC-1 → TC-P2-1',
        },
      ],
    })
    renderPage(<ImpactPage />)
    const shaInputs = screen.getAllByPlaceholderText('40 位 commit SHA')
    fireEvent.change(shaInputs[0], { target: { value: 'a'.repeat(40) } })
    fireEvent.change(shaInputs[1], { target: { value: 'b'.repeat(40) } })
    fireEvent.click(screen.getByText('生成影响计划'))
    await waitFor(() => expect(api.createImpactPlan).toHaveBeenCalled())
    expect(await screen.findByText('TC-P0-1')).toBeTruthy()
    expect(screen.getByText('TC-P2-1')).toBeTruthy()
    expect(screen.getByText('sports:api → AC-1 → TC-P2-1')).toBeTruthy()
    expect(screen.getByText('sports:api')).toBeTruthy()
  })
})

describe('BenchmarksPage', () => {
  beforeEach(() => {
    Object.values(api).forEach((fn) => fn.mockReset())
  })

  it('creates dataset, adds sample and freezes with gate eligibility', async () => {
    api.createBenchmarkDataset.mockResolvedValue({ id: 'ds-1', dataset_key: 'learning', revision: 1 })
    api.addBenchmarkSample.mockResolvedValue({ id: 's-1', sample_id: 's-1' })
    api.freezeBenchmarkDataset.mockResolvedValue({
      id: 'ds-1',
      status: 'FROZEN',
      sample_count: 31,
      content_hash: 'c'.repeat(64),
      gate_eligible: true,
    })
    renderPage(<BenchmarksPage />)
    fireEvent.change(screen.getByPlaceholderText('dataset_key（如 learning-ds）'), {
      target: { value: 'learning' },
    })
    fireEvent.click(screen.getByText('创建数据集'))
    await waitFor(() => expect(api.createBenchmarkDataset).toHaveBeenCalled())
    expect(await screen.findByText(/dataset_id: ds-1/)).toBeTruthy()

    fireEvent.change(screen.getByPlaceholderText('sample_id'), { target: { value: 's-1' } })
    fireEvent.click(screen.getByText('追加样本'))
    await waitFor(() =>
      expect(api.addBenchmarkSample).toHaveBeenCalledWith(
        'ds-1',
        expect.objectContaining({ sample_id: 's-1' }),
      ),
    )

    fireEvent.click(screen.getByText('冻结数据集'))
    await waitFor(() => expect(api.freezeBenchmarkDataset).toHaveBeenCalledWith('ds-1'))
    expect(await screen.findByText('可用于门禁')).toBeTruthy()
    expect(screen.getByText('样本数：31')).toBeTruthy()
  })

  it('runs an LLM benchmark from the frozen dataset', async () => {
    api.createBenchmarkDataset.mockResolvedValue({ id: 'ds-1', dataset_key: 'learning', revision: 1 })
    api.freezeBenchmarkDataset.mockResolvedValue({
      id: 'ds-1',
      status: 'FROZEN',
      sample_count: 4,
      content_hash: 'c'.repeat(64),
      gate_eligible: false,
    })
    api.runLlmBenchmark.mockResolvedValue({
      id: 'bench-1',
      dataset_id: 'ds-1',
      agent_key: 'A6',
      status: 'COMPLETED',
      result_status: 'REFERENCE_ONLY',
      metrics: { samples: 4, precision: 1, recall: 1, f1: 1 },
      per_sample: [],
    })
    renderPage(<BenchmarksPage />)
    fireEvent.change(screen.getByPlaceholderText('dataset_key（如 learning-ds）'), {
      target: { value: 'learning' },
    })
    fireEvent.click(screen.getByText('创建数据集'))
    await waitFor(() => expect(api.createBenchmarkDataset).toHaveBeenCalled())
    fireEvent.click(screen.getByText('冻结数据集'))
    await waitFor(() => expect(api.freezeBenchmarkDataset).toHaveBeenCalled())
    fireEvent.click(screen.getByText('运行 LLM Benchmark'))
    await waitFor(() => expect(api.runLlmBenchmark).toHaveBeenCalledWith('ds-1'))
    expect(await screen.findByText('REFERENCE_ONLY')).toBeTruthy()
  })

  it('shows benchmark run metrics', async () => {
    api.getBenchmarkRun.mockResolvedValue({
      id: 'run-1',
      dataset_id: 'ds-1',
      agent_key: 'A6',
      status: 'COMPLETED',
      result_status: 'PASS_GATE',
      metrics: { precision: 0.9, recall: 0.8, f1: 0.85 },
      per_sample: [{ sample_id: 's-1' }],
    })
    renderPage(<BenchmarksPage />)
    fireEvent.change(screen.getByPlaceholderText('benchmark run id'), {
      target: { value: 'run-1' },
    })
    fireEvent.click(screen.getByText('查询'))
    await waitFor(() => expect(api.getBenchmarkRun).toHaveBeenCalledWith('run-1'))
    expect(await screen.findByText('PASS_GATE')).toBeTruthy()
    expect(screen.getByText(/precision/)).toBeTruthy()
    expect(screen.getByText('逐样本结果：1 条')).toBeTruthy()
  })
})
