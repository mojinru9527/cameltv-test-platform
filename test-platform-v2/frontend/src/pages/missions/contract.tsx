import { useState } from 'react'
import { useParams } from 'react-router'
import { toast } from 'sonner'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
  StatusBadge,
  type SeverityVariant,
} from '@/ui'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ErrorState } from '@/components/state'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  analyzeMissionAmbiguities,
  fetchMissionAmbiguities,
  resolveAmbiguity,
  AMBIGUITY_STATUS_LABELS,
  type Ambiguity,
} from '@/api/ambiguities'
import {
  generateContract,
  fetchCurrentContract,
  freezeContract,
  CONTRACT_STATUS_LABELS,
  type CurrentContract,
} from '@/api/contract'
import { Sparkles, Lock } from '@/lib/icons'
import { isConflictError } from '@/lib/conflict'
import { StaleConflictBanner } from './StaleConflictBanner'
import { ContractSnapshotView } from './ContractSnapshotView'

function toSeverity(value: string): SeverityVariant {
  return value === 'P0' || value === 'P1' || value === 'P2' ? value : 'P3'
}

export default function MissionContractPage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('契约')

  const [ambiguities, setAmbiguities] = useState<Ambiguity[]>([])
  const [contract, setContract] = useState<CurrentContract | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<Error | null>(null)
  const [reloadVersion, setReloadVersion] = useState(0)
  const [analyzing, setAnalyzing] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [freezeOpen, setFreezeOpen] = useState(false)
  const [freezing, setFreezing] = useState(false)
  const [staleConflict, setStaleConflict] = useState(false)

  const reload = () => {
    setStaleConflict(false)
    setReloadVersion((current) => current + 1)
  }

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    Promise.all([
      fetchMissionAmbiguities(missionId, signal),
      fetchCurrentContract(missionId, signal),
    ])
      .then(([ams, con]) => {
        if (signal.aborted) return
        setAmbiguities(ams)
        setContract(con)
        setLoadError(null)
      })
      .catch((err: unknown) => {
        if (signal.aborted) return
        setLoadError(err instanceof Error ? err : new Error(String(err)))
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId, reloadVersion])

  const doAnalyze = async () => {
    if (analyzing) return
    setAnalyzing(true)
    try {
      await analyzeMissionAmbiguities(missionId)
      toast.success('歧义/意图分析完成')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '分析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  const doResolve = async (ambiguity: Ambiguity, optionKey: string) => {
    try {
      await resolveAmbiguity(ambiguity.id, { selected_option_key: optionKey })
      toast.success('已记录选择')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '记录失败')
    }
  }

  const doGenerate = async () => {
    if (generating) return
    setGenerating(true)
    try {
      await generateContract(missionId, { force: true })
      toast.success('契约已生成')
      reload()
    } catch (err) {
      // V30-107：409（契约已冻结等状态冲突）→ 内联 STALE 提示，不引导原样重试
      if (isConflictError(err)) {
        setStaleConflict(true)
      } else {
        toast.error(err instanceof Error ? err.message : '生成失败')
      }
    } finally {
      setGenerating(false)
    }
  }

  const doFreeze = async () => {
    if (freezing || !contract) return
    setFreezing(true)
    try {
      await freezeContract(contract.contract_id, contract.version_no)
      toast.success('契约已冻结')
      setFreezeOpen(false)
      reload()
    } catch (err) {
      if (isConflictError(err)) {
        // 并发冻结/评审状态已变更：关闭对话框，提示刷新
        setFreezeOpen(false)
        setStaleConflict(true)
      } else {
        toast.error(err instanceof Error ? err.message : '冻结失败')
      }
    } finally {
      setFreezing(false)
    }
  }

  if (loading && !contract && ambiguities.length === 0) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
    )
  }

  if (loadError) {
    return (
      <ErrorState
        title="契约页加载失败"
        description="未能读取歧义或契约内容。"
        error={loadError}
        onRetry={reload}
      />
    )
  }

  const versionStatus = contract?.version
    ? CONTRACT_STATUS_LABELS[contract.version.status]
    : undefined

  // 空壳契约（含快照解析失败）不可冻结，否则后端 400 前用户无从得知原因
  const ruleCount = contract?.version?.snapshot?.rules.length ?? 0
  const freezeBlockedReason =
    contract && ruleCount === 0
      ? '契约快照无有效规则，请先完成 Scope 评审后重新生成'
      : ''

  return (
    <div className="space-y-4">
      {staleConflict && <StaleConflictBanner onReload={reload} />}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Contract = 标准答案。冻结前需解决全部 P0/P1 歧义并完成 Scope 评审。
        </p>
        <Button variant="secondary" disabled={analyzing} onClick={doAnalyze}>
          <Sparkles className="size-4" /> {analyzing ? '分析中…' : '分析歧义/意图'}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">歧义（Ambiguitity）</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2" aria-busy={loading}>
          {ambiguities.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              暂无歧义。点击上方「分析歧义/意图」生成。
            </p>
          ) : (
            ambiguities.map((a) => {
              const st = AMBIGUITY_STATUS_LABELS[a.status]
              return (
                <div key={a.id} className="rounded-lg border p-3">
                  <div className="flex items-center gap-2">
                    <StatusBadge variant={toSeverity(a.severity)} />
                    <p className="font-medium">{a.title}</p>
                    <Badge variant="secondary" className={st?.color}>
                      {st?.label ?? a.status}
                    </Badge>
                  </div>
                  {a.description && (
                    <p className="mt-1 text-sm text-muted-foreground">{a.description}</p>
                  )}
                  {a.status === 'OPEN' && (
                    <div className="mt-2 max-w-xs">
                      <Select onValueChange={(v) => doResolve(a, v)}>
                        <SelectTrigger>
                          <SelectValue placeholder="选择处理方式" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="allow">纳入</SelectItem>
                          <SelectItem value="deny">排除</SelectItem>
                          <SelectItem value="out">本版本不测</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Test Contract</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {contract ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-sm text-muted-foreground">
                  v{contract.version_no}
                </span>
                <Badge variant="secondary" className={versionStatus?.color}>
                  {versionStatus?.label ?? contract.version?.status}
                </Badge>
                {contract.version?.content_hash && (
                  <span className="font-mono text-xs text-muted-foreground">
                    {contract.version.content_hash.slice(0, 12)}
                  </span>
                )}
              </div>
              <ContractSnapshotView snapshot={contract.version?.snapshot} />
              <div className="flex gap-2">
                <Button variant="secondary" disabled={generating} onClick={doGenerate}>
                  <Sparkles className="size-4" /> {generating ? '生成中…' : '重新生成'}
                </Button>
                {contract.version?.status === 'DRAFT' && (
                  <span title={freezeBlockedReason || undefined}>
                    <Button disabled={!!freezeBlockedReason} onClick={() => setFreezeOpen(true)}>
                      <Lock className="size-4" /> 冻结契约
                    </Button>
                  </span>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">尚未生成 Test Contract。</p>
              <Button disabled={generating} onClick={doGenerate}>
                <Sparkles className="size-4" /> {generating ? '生成中…' : '生成契约'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={freezeOpen} onOpenChange={setFreezeOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>冻结 Contract v{contract?.version_no}</DialogTitle>
            <DialogDescription>
              冻结后：AI 不能修改业务预期；后续修改将创建 Proposal 与 v+1 版本。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setFreezeOpen(false)}>
              取消
            </Button>
            <Button disabled={freezing} onClick={doFreeze}>
              {freezing ? '冻结中…' : '确认冻结'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
