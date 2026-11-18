import { useCallback, useEffect, useState } from 'react'
import { Badge } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  approveAc,
  createContract,
  getContract,
  getContractCoverage,
  listCases,
  listContracts,
  reviewCase,
  transitionContract,
  type AiqeCaseSummary,
  type AiqeContractDetail,
  type AiqeContractSummary,
  type AiqeCoverageReport,
} from '@/api/aiqeContracts'
import ConsoleTabs from './ConsoleTabs'

const NEXT_ACTIONS: Record<string, Array<{ target: string; label: string }>> = {
  DRAFT: [{ target: 'REVIEW_REQUIRED', label: '提交评审' }],
  REVIEW_REQUIRED: [
    { target: 'APPROVED', label: '批准 Contract' },
    { target: 'DRAFT', label: '退回 Draft' },
  ],
  APPROVED: [
    { target: 'FROZEN', label: '冻结' },
    { target: 'SUPERSEDED', label: '作废' },
  ],
  FROZEN: [{ target: 'SUPERSEDED', label: '作废' }],
}

const COVERAGE_TONE: Record<string, 'success' | 'warning' | 'danger'> = {
  COVERED: 'success',
  PARTIAL: 'warning',
  UNCOVERED: 'danger',
}

export default function ContractsPage() {
  useDocumentTitle('需求合约')
  const [contracts, setContracts] = useState<AiqeContractSummary[]>([])
  const [selected, setSelected] = useState<AiqeContractDetail | null>(null)
  const [coverage, setCoverage] = useState<AiqeCoverageReport | null>(null)
  const [cases, setCases] = useState<AiqeCaseSummary[]>([])
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    requirement_id: '',
    title: '',
    source_ref: '',
    ac_id: 'AC-001',
    given: '',
    when: '',
    then: '',
    priority: 'P0',
    oracle_ref: '',
  })

  const loadList = useCallback(() => {
    listContracts()
      .then((rows) => setContracts(rows))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : '加载失败'))
  }, [])

  useEffect(() => {
    loadList()
  }, [loadList])

  const selectContract = useCallback(async (contractId: string) => {
    setError('')
    try {
      const [detail, report, rows] = await Promise.all([
        getContract(contractId),
        getContractCoverage(contractId),
        listCases({ contract_id: contractId }),
      ])
      setSelected(detail)
      setCoverage(report)
      setCases(rows)
    } catch (err) {
      setError(err instanceof Error ? err.message : '合同加载失败')
    }
  }, [])

  const submitCreate = useCallback(async () => {
    setError('')
    try {
      const created = await createContract({
        requirement_id: form.requirement_id,
        title: form.title,
        source_refs: form.source_ref ? [form.source_ref] : [],
        acceptance_criteria: [
          {
            ac_id: form.ac_id,
            given: form.given,
            when: form.when,
            then: form.then.split('\n').filter(Boolean),
            priority: form.priority,
            oracle_type: form.oracle_ref ? 'product_rule' : '',
            oracle_ref: form.oracle_ref,
          },
        ],
      })
      loadList()
      await selectContract(created.id)
      setForm((prev) => ({ ...prev, requirement_id: '', title: '', given: '', when: '', then: '' }))
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败')
    }
  }, [form, loadList, selectContract])

  const runTransition = useCallback(
    async (target: string) => {
      if (!selected) return
      setError('')
      try {
        const updated = await transitionContract(selected.id, target)
        setSelected(updated)
        loadList()
      } catch (err) {
        setError(err instanceof Error ? err.message : '状态迁移失败')
      }
    },
    [loadList, selected],
  )

  const approveCriterion = useCallback(
    async (acId: string) => {
      if (!selected) return
      try {
        await approveAc(selected.id, acId)
        await selectContract(selected.id)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'AC 审批失败')
      }
    },
    [selectContract, selected],
  )

  const decideCase = useCallback(
    async (caseId: string, decision: 'APPROVED' | 'REJECTED') => {
      if (!selected) return
      try {
        await reviewCase(caseId, decision)
        setCases(await listCases({ contract_id: selected.id }))
        setCoverage(await getContractCoverage(selected.id))
      } catch (err) {
        setError(err instanceof Error ? err.message : '用例审核失败')
      }
    },
    [selected],
  )

  return (
    <div className="space-y-6 p-6">
      <header className="space-y-3">
        <h1 className="text-2xl font-semibold">需求合约 / 结构化用例</h1>
        <ConsoleTabs />
      </header>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <section className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <div className="space-y-3">
          <form
            className="space-y-2 rounded-lg border p-3 text-sm"
            onSubmit={(event) => {
              event.preventDefault()
              void submitCreate()
            }}
          >
            <h2 className="font-medium">新建 Contract</h2>
            <input
              className="w-full rounded border px-2 py-1"
              placeholder="requirement_id（如 REQ-1001）"
              value={form.requirement_id}
              onChange={(event) => setForm({ ...form, requirement_id: event.target.value })}
            />
            <input
              className="w-full rounded border px-2 py-1"
              placeholder="标题"
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
            />
            <input
              className="w-full rounded border px-2 py-1"
              placeholder="来源引用（prd:spec.md#章节）"
              value={form.source_ref}
              onChange={(event) => setForm({ ...form, source_ref: event.target.value })}
            />
            <div className="grid grid-cols-[80px_1fr] gap-2">
              <input
                className="rounded border px-2 py-1"
                value={form.ac_id}
                onChange={(event) => setForm({ ...form, ac_id: event.target.value })}
              />
              <input
                className="rounded border px-2 py-1"
                placeholder="优先级"
                value={form.priority}
                onChange={(event) => setForm({ ...form, priority: event.target.value })}
              />
            </div>
            <input
              className="w-full rounded border px-2 py-1"
              placeholder="Given"
              value={form.given}
              onChange={(event) => setForm({ ...form, given: event.target.value })}
            />
            <input
              className="w-full rounded border px-2 py-1"
              placeholder="When"
              value={form.when}
              onChange={(event) => setForm({ ...form, when: event.target.value })}
            />
            <textarea
              className="w-full rounded border px-2 py-1"
              placeholder="Then（每行一条）"
              rows={3}
              value={form.then}
              onChange={(event) => setForm({ ...form, then: event.target.value })}
            />
            <input
              className="w-full rounded border px-2 py-1"
              placeholder="Oracle 引用（PRD#1；P0 必填）"
              value={form.oracle_ref}
              onChange={(event) => setForm({ ...form, oracle_ref: event.target.value })}
            />
            <button
              type="submit"
              className="w-full rounded bg-primary px-3 py-1.5 text-primary-foreground"
            >
              创建 Draft
            </button>
          </form>

          <div className="rounded-lg border">
            <ul className="divide-y text-sm">
              {contracts.length === 0 ? (
                <li className="px-3 py-4 text-muted-foreground">暂无 Contract</li>
              ) : (
                contracts.map((contract) => (
                  <li key={contract.id}>
                    <button
                      type="button"
                      className="w-full px-3 py-2 text-left hover:bg-muted/40"
                      onClick={() => void selectContract(contract.id)}
                    >
                      <span className="block font-medium">{contract.title || contract.requirement_id}</span>
                      <span className="text-xs text-muted-foreground">
                        {contract.requirement_id} · rev{contract.revision} · {contract.status}
                      </span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>

        <div className="space-y-4">
          {selected ? (
            <>
              <div className="space-y-2 rounded-lg border p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-medium">{selected.title || selected.requirement_id}</h2>
                  <Badge tone="neutral">{selected.status}</Badge>
                  <span className="font-mono text-xs text-muted-foreground">
                    {selected.revision_checksum?.slice(0, 23)}…
                  </span>
                </div>
                <p className="text-muted-foreground">
                  来源：{selected.source_refs.join('、') || '—'}
                </p>
                <div className="flex flex-wrap gap-2">
                  {(NEXT_ACTIONS[selected.status] ?? []).map((action) => (
                    <button
                      key={action.target}
                      type="button"
                      className="rounded border px-3 py-1 hover:bg-muted/40"
                      onClick={() => void runTransition(action.target)}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              </div>

              <section className="space-y-2">
                <h3 className="text-sm font-semibold">AC（{selected.acceptance_criteria.length}）</h3>
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 text-left">
                    <tr>
                      <th className="px-3 py-2">AC</th>
                      <th className="px-3 py-2">优先级</th>
                      <th className="px-3 py-2">Oracle</th>
                      <th className="px-3 py-2">审批</th>
                      <th className="px-3 py-2">覆盖</th>
                      <th className="px-3 py-2">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selected.acceptance_criteria.map((ac) => (
                      <tr key={ac.ac_id} className="border-t">
                        <td className="px-3 py-2 font-mono text-xs">{ac.ac_id}</td>
                        <td className="px-3 py-2">{ac.priority}</td>
                        <td className="px-3 py-2">{ac.oracle_ref || '—'}</td>
                        <td className="px-3 py-2">{ac.approval_status}</td>
                        <td className="px-3 py-2">
                          <Badge tone={COVERAGE_TONE[coverage?.coverage[ac.ac_id] ?? 'UNCOVERED'] ?? 'neutral'}>
                            {coverage?.coverage[ac.ac_id] ?? 'UNCOVERED'}
                          </Badge>
                        </td>
                        <td className="px-3 py-2">
                          {ac.approval_status !== 'APPROVED' ? (
                            <button
                              type="button"
                              className="text-primary hover:underline"
                              onClick={() => void approveCriterion(ac.ac_id)}
                            >
                              批准 AC
                            </button>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>

              <section className="space-y-2">
                <h3 className="text-sm font-semibold">用例（{cases.length}）</h3>
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 text-left">
                    <tr>
                      <th className="px-3 py-2">Case</th>
                      <th className="px-3 py-2">优先级</th>
                      <th className="px-3 py-2">Grade</th>
                      <th className="px-3 py-2">审核</th>
                      <th className="px-3 py-2">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cases.length === 0 ? (
                      <tr>
                        <td className="px-3 py-4 text-center text-muted-foreground" colSpan={5}>
                          暂无用例
                        </td>
                      </tr>
                    ) : (
                      cases.map((item) => (
                        <tr key={item.case_id} className="border-t">
                          <td className="px-3 py-2">
                            <span className="block">{item.title}</span>
                            <span className="font-mono text-xs text-muted-foreground">{item.case_id}</span>
                          </td>
                          <td className="px-3 py-2">{item.priority}</td>
                          <td className="px-3 py-2">{item.automation_grade}</td>
                          <td className="px-3 py-2">{item.review_status}</td>
                          <td className="space-x-2 px-3 py-2">
                            <button
                              type="button"
                              className="text-primary hover:underline"
                              onClick={() => void decideCase(item.case_id, 'APPROVED')}
                            >
                              通过
                            </button>
                            <button
                              type="button"
                              className="text-destructive hover:underline"
                              onClick={() => void decideCase(item.case_id, 'REJECTED')}
                            >
                              驳回
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </section>
            </>
          ) : (
            <p className="rounded-lg border p-6 text-sm text-muted-foreground">
              选择左侧 Contract 查看 AC、覆盖与用例。
            </p>
          )}
        </div>
      </section>
    </div>
  )
}
