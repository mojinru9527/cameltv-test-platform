import { useState } from 'react'
import { Badge, Button, Input, Skeleton } from '@/ui'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchHealingProposals,
  approveHealingProposal,
  rejectHealingProposal,
  HEALING_PROPOSAL_STATUS_LABELS,
  HEALING_PROPOSAL_TYPE_LABELS,
  type HealingProposal,
} from '@/api/healingProposals'
import { HealingProposalDiff } from '@/components/browser/HealingProposalDiff'
import { OracleChangeGuardBadge } from '@/components/browser/OracleChangeGuardBadge'
import { collectOracleKeys } from '@/components/browser/CommandDiff'

function sameOracleKeys(before: string[], after: string[]): boolean {
  if (before.length !== after.length) return false
  return before.every((k, i) => k === after[i])
}

function StatusBadge({ status }: { status: string }) {
  const meta = HEALING_PROPOSAL_STATUS_LABELS[status]
  if (!meta) return <Badge variant="outline">{status}</Badge>
  return <Badge tone={status === 'APPROVED' ? 'success' : status === 'REJECTED' ? 'danger' : 'warning'}>{meta.label}</Badge>
}

/** Healing review: load real Action Healing proposals from the API. */
export default function HealingReviewPage() {
  useDocumentTitle('愈合评审')

  const [adapterInput, setAdapterInput] = useState('')
  const [adapterId, setAdapterId] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState<string | 'ALL'>('ALL')
  const [proposals, setProposals] = useState<HealingProposal[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [acting, setActing] = useState(false)

  useAbortableEffect((signal) => {
    if (adapterId === null) return
    setLoading(true)
    fetchHealingProposals(
      {
        scenario_adapter_id: adapterId,
        status: statusFilter === 'ALL' ? undefined : statusFilter,
      },
      signal,
    )
      .then((rows) => {
        setProposals(rows)
        setSelectedId((prev) => {
          if (prev && rows.some((r) => r.id === prev)) return prev
          return rows[0]?.id ?? null
        })
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载愈合提案失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [adapterId, statusFilter])

  const doLoad = () => {
    const sid = Number(adapterInput)
    if (!sid) {
      toast.error('请输入 scenario_adapter_id')
      return
    }
    setAdapterId(sid)
  }

  const selected = proposals.find((p) => p.id === selectedId) ?? null
  const oracleChanged =
    selected && selected.before_json && selected.after_json
      ? !sameOracleKeys(collectOracleKeys(selected.before_json), collectOracleKeys(selected.after_json))
      : false

  const doApprove = async () => {
    if (!selected || acting) return
    setActing(true)
    try {
      await approveHealingProposal(selected.id)
      toast.success('提案已批准')
      setProposals((rows) =>
        rows.map((r) => (r.id === selected.id ? { ...r, status: 'APPROVED', reviewed_at: new Date().toISOString() } : r)),
      )
    } catch (err) {
      toast.error((err as Error).message || '批准失败')
    } finally {
      setActing(false)
    }
  }

  const doReject = async () => {
    if (!selected || acting) return
    setActing(true)
    try {
      await rejectHealingProposal(selected.id)
      toast.success('提案已拒绝')
      setProposals((rows) =>
        rows.map((r) => (r.id === selected.id ? { ...r, status: 'REJECTED', reviewed_at: new Date().toISOString() } : r)),
      )
    } catch (err) {
      toast.error((err as Error).message || '拒绝失败')
    } finally {
      setActing(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold tracking-[-0.02em]">愈合评审 (Healing Review)</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          加载 Action Healing 提案，审阅前后 Command IR 差异与 Oracle 守护。愈合提案中的 Oracle 变更必须显式暴露给评审人。
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-2">
        <div className="w-48 space-y-1.5">
          <label htmlFor="healing-adapter" className="text-xs font-medium text-muted-foreground">scenario_adapter_id</label>
          <Input
            id="healing-adapter"
            type="number"
            value={adapterInput}
            onChange={(e) => setAdapterInput(e.target.value)}
            placeholder="场景适配器 ID"
          />
        </div>
        <div className="w-40 space-y-1.5">
          <label htmlFor="healing-status" className="text-xs font-medium text-muted-foreground">状态</label>
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v)}>
            <SelectTrigger>
              <SelectValue placeholder="全部状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">全部</SelectItem>
              <SelectItem value="OPEN">待审</SelectItem>
              <SelectItem value="APPROVED">已批准</SelectItem>
              <SelectItem value="REJECTED">已拒绝</SelectItem>
              <SelectItem value="APPLIED">已应用</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button onClick={doLoad} disabled={loading}>
          {loading ? '加载中…' : '加载提案'}
        </Button>
        <span className="text-xs text-muted-foreground">
          {proposals.length > 0 ? `共 ${proposals.length} 条提案` : '尚未加载'}
        </span>
      </div>

      {loading || adapterId === null ? (
        loading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : (
          <div className="rounded-md border border-dashed px-3 py-10 text-center text-sm text-muted-foreground">
            <OracleChangeGuardBadge changed={false} detail="占位：输入 scenario_adapter_id 以加载愈合提案。" />
          </div>
        )
      ) : proposals.length === 0 ? (
        <div className="rounded-md border border-dashed px-3 py-10 text-center text-sm text-muted-foreground">
          暂无愈合提案
        </div>
      ) : (
        <>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground">选择提案</span>
              <Select value={selectedId === null ? '' : String(selectedId)} onValueChange={(v) => setSelectedId(v ? Number(v) : null)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择提案" />
                </SelectTrigger>
                <SelectContent>
                  {proposals.map((p) => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      #{p.id} · {HEALING_PROPOSAL_TYPE_LABELS[p.proposal_type] ?? p.proposal_type} · {HEALING_PROPOSAL_STATUS_LABELS[p.status]?.label ?? p.status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end gap-2">
              {selected && (
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={selected.status} />
                  <Badge variant="outline">{HEALING_PROPOSAL_TYPE_LABELS[selected.proposal_type] ?? selected.proposal_type}</Badge>
                  <span className="text-xs text-muted-foreground">ID {selected.id}</span>
                </div>
              )}
            </div>
          </div>

          {selected && (
            <>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">原因：{selected.reason || '—'}</p>
                {selected.evidence_refs_json.length > 0 && (
                  <p className="text-xs text-muted-foreground">证据引用：{selected.evidence_refs_json.join(', ')}</p>
                )}
              </div>

              <HealingProposalDiff
                before={selected.before_json}
                after={selected.after_json}
                oracleChanged={oracleChanged}
              />

              {selected.status === 'OPEN' && (
                <div className="flex gap-2">
                  <Button onClick={doApprove} disabled={acting} variant="primary">
                    {acting ? '处理中…' : '批准'}
                  </Button>
                  <Button onClick={doReject} disabled={acting} variant="danger">
                    {acting ? '处理中…' : '拒绝'}
                  </Button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
