import { useCallback, useState } from 'react'
import { Badge } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { createImpactPlan, type ImpactPlan } from '@/api/aiqeInsights'
import ConsoleTabs from './ConsoleTabs'

export default function ImpactPage() {
  useDocumentTitle('变更影响')
  const [form, setForm] = useState({ base: '', head: '', failed: '', contracts: '' })
  const [plan, setPlan] = useState<ImpactPlan | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = useCallback(async () => {
    setError('')
    setLoading(true)
    try {
      const created = await createImpactPlan({
        base_sha: form.base.trim(),
        head_sha: form.head.trim(),
        failed_case_ids: form.failed.split(',').map((item) => item.trim()).filter(Boolean),
        changed_contract_ids: form.contracts
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
      })
      setPlan(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : '影响分析失败')
    } finally {
      setLoading(false)
    }
  }, [form])

  return (
    <div className="space-y-6 p-6">
      <header className="space-y-3">
        <h1 className="text-2xl font-semibold">变更影响（AUD-017）</h1>
        <ConsoleTabs />
      </header>

      <form
        className="grid gap-3 rounded-lg border p-4 text-sm md:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault()
          void submit()
        }}
      >
        <label className="space-y-1">
          <span className="text-muted-foreground">base SHA</span>
          <input
            className="w-full rounded border px-2 py-1 font-mono"
            value={form.base}
            onChange={(event) => setForm({ ...form, base: event.target.value })}
            placeholder="40 位 commit SHA"
          />
        </label>
        <label className="space-y-1">
          <span className="text-muted-foreground">head SHA</span>
          <input
            className="w-full rounded border px-2 py-1 font-mono"
            value={form.head}
            onChange={(event) => setForm({ ...form, head: event.target.value })}
            placeholder="40 位 commit SHA"
          />
        </label>
        <label className="space-y-1">
          <span className="text-muted-foreground">失败 Case（逗号分隔）</span>
          <input
            className="w-full rounded border px-2 py-1"
            value={form.failed}
            onChange={(event) => setForm({ ...form, failed: event.target.value })}
            placeholder="TC-001,TC-002"
          />
        </label>
        <label className="space-y-1">
          <span className="text-muted-foreground">变更合约（逗号分隔）</span>
          <input
            className="w-full rounded border px-2 py-1"
            value={form.contracts}
            onChange={(event) => setForm({ ...form, contracts: event.target.value })}
            placeholder="contract-id"
          />
        </label>
        <div className="md:col-span-2">
          <button
            type="submit"
            className="rounded bg-primary px-4 py-1.5 text-primary-foreground"
            disabled={loading}
          >
            {loading ? '分析中…' : '生成影响计划'}
          </button>
        </div>
      </form>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {plan ? (
        <div className="space-y-4">
          <section className="space-y-2">
            <h2 className="text-lg font-semibold">变更组件（{plan.components.length}）</h2>
            <div className="flex flex-wrap gap-2">
              {plan.components.map((component) => (
                <Badge key={component} tone="neutral">
                  {component}
                </Badge>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              {plan.changed_files.length} 个文件 · {plan.changed_routes.length} 个路由 ·{' '}
              {plan.changed_migrations.length} 个迁移
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold">
              强制回归（{plan.mandatory_case_ids.length}，AI 不可删除）
            </h2>
            <ul className="rounded-lg border p-3 text-sm">
              {plan.mandatory_case_ids.length === 0 ? (
                <li className="text-muted-foreground">无强制 Case</li>
              ) : (
                plan.mandatory_case_ids.map((caseId) => (
                  <li key={caseId} className="font-mono text-xs">
                    {caseId}
                  </li>
                ))
              )}
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold">候选 Case（{plan.candidates.length}）</h2>
            <div className="overflow-hidden rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-left">
                  <tr>
                    <th className="px-3 py-2">Case</th>
                    <th className="px-3 py-2">分数</th>
                    <th className="px-3 py-2">原因</th>
                    <th className="px-3 py-2">追踪路径</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.candidates.length === 0 ? (
                    <tr>
                      <td className="px-3 py-6 text-center text-muted-foreground" colSpan={4}>
                        暂无候选
                      </td>
                    </tr>
                  ) : (
                    plan.candidates.map((item) => (
                      <tr key={item.case_id} className="border-t">
                        <td className="px-3 py-2 font-mono text-xs">{item.case_id}</td>
                        <td className="px-3 py-2">{item.score}</td>
                        <td className="px-3 py-2">{item.reason}</td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">{item.trace_path}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  )
}
