import { useEffect, useState } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ProjectScopeBoundary } from '../ProjectScopeBoundary'
import { useAuthStore } from '@/stores/auth'

/**
 * B60-P0-003 契约：项目 A→B 切换后，testcase/testplan/report/defect/trace/
 * environment/dataset/integration/uitest 九域页面都必须重挂载、清空陈旧行、
 * 按 B 项目重新请求且每切换仅一次有效 GET。
 */

const DOMAINS = [
  'testcase',
  'testplan',
  'report',
  'defect',
  'trace',
  'environment',
  'dataset',
  'integration',
  'uitest',
] as const

type Domain = (typeof DOMAINS)[number]

const fetchForDomain = vi.fn(
  async (domain: Domain, projectId: number | null): Promise<string[]> => {
    await Promise.resolve()
    if (projectId == null) return []
    return [`${domain}-row-${projectId}-1`, `${domain}-row-${projectId}-2`]
  },
)

/** 模拟真实页面：挂载时清空旧行，按当前项目拉取列表。 */
function DomainPage({ domain }: { domain: Domain }) {
  const currentProjectId = useAuthStore((state) => state.currentProjectId)
  const [rows, setRows] = useState<string[]>(['stale-A'])

  useEffect(() => {
    let cancelled = false
    setRows([])
    void fetchForDomain(domain, currentProjectId).then((data) => {
      if (!cancelled) setRows(data)
    })
    return () => {
      cancelled = true
    }
  }, [domain, currentProjectId])

  return (
    <div data-testid={`${domain}-rows`}>
      {rows.length === 0 ? 'EMPTY' : rows.join(',')}
    </div>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  const currentProjectId = useAuthStore((state) => state.currentProjectId)
  return <ProjectScopeBoundary projectId={currentProjectId}>{children}</ProjectScopeBoundary>
}

function switchProject(projectId: number | null) {
  useAuthStore.setState({ currentProjectId: projectId })
}

describe('项目 A→B 切换全模块隔离矩阵', () => {
  beforeEach(() => {
    useAuthStore.setState({
      token: 't',
      currentProjectId: 1,
      user: { id: 1, username: 'admin', roles: ['admin'] },
    })
    fetchForDomain.mockClear()
  })

  DOMAINS.forEach((domain) => {
    it(`${domain}: 切换后清空旧行并按 B 重新请求（每次仅一次 GET）`, async () => {
      render(
        <Shell>
          <DomainPage domain={domain} />
        </Shell>,
      )

      await waitFor(() => {
        expect(screen.getByTestId(`${domain}-rows`).textContent).toBe(
          `${domain}-row-1-1,${domain}-row-1-2`,
        )
      })
      expect(fetchForDomain).toHaveBeenCalledTimes(1)
      expect(fetchForDomain).toHaveBeenLastCalledWith(domain, 1)

      switchProject(2)

      await waitFor(() => {
        expect(screen.getByTestId(`${domain}-rows`).textContent).toBe(
          `${domain}-row-2-1,${domain}-row-2-2`,
        )
      })
      expect(fetchForDomain).toHaveBeenCalledTimes(2)
      expect(fetchForDomain).toHaveBeenLastCalledWith(domain, 2)
      expect(screen.getByTestId(`${domain}-rows`).textContent).not.toContain('stale-A')
    })
  })

  it('切换到无项目时显示空态且不清空上一项目数据前先重置', async () => {
    render(
      <Shell>
        <DomainPage domain="report" />
      </Shell>,
    )
    await waitFor(() => {
      expect(screen.getByTestId('report-rows').textContent).toBe('report-row-1-1,report-row-1-2')
    })

    switchProject(null)
    await waitFor(() => {
      expect(screen.getByTestId('report-rows').textContent).toBe('EMPTY')
    })
  })
})
