import { useEffect, useState } from 'react'
import { governanceApi } from '@/api/governance'
import { AITDE_V3_ENABLED } from '@/config/aitde'
import { Loader2 } from '@/lib/icons'

interface Posture {
  [key: string]: unknown
}

const DEFAULT_METRICS = JSON.stringify(
  {
    p0_false_pass_rate: 0.005,
    false_fail_rate: 0.01,
    evidence_completeness: 0.995,
    replay_audit_consistency: 0.995,
    fixture_cleanup_success: 0.995,
    prod_unauthorized_write: 0,
    secret_leakage: 0,
    pii_leakage: 0,
    contract_unauthorized_mutation: 0,
    mission_workflow_adoption: 0.85,
  },
  null,
  2,
)

function PostureCard({ title, ok, detail }: { title: string; ok: boolean | null; detail: string }) {
  return (
    <div className="rounded-xl border bg-card p-4 text-card-foreground">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">{title}</h3>
        {ok === null ? (
          <span className="text-xs text-muted-foreground">…</span>
        ) : ok ? (
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">PASS</span>
        ) : (
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">需关注</span>
        )}
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{detail}</p>
    </div>
  )
}

export default function GovernancePage() {
  const [encryption, setEncryption] = useState<Posture | null>(null)
  const [backup, setBackup] = useState<Posture | null>(null)
  const [sso, setSso] = useState<Posture | null>(null)
  const [cost, setCost] = useState<Posture | null>(null)
  const [dr, setDr] = useState<unknown[]>([])
  const [metricsInput, setMetricsInput] = useState(DEFAULT_METRICS)
  const [readiness, setReadiness] = useState<Posture | null>(null)
  const [readinessError, setReadinessError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const [enc, bak, ssoCfg, costUsg, drRuns] = await Promise.all([
          governanceApi.encryption(),
          governanceApi.backup(),
          governanceApi.sso(),
          governanceApi.cost(),
          governanceApi.dr(),
        ])
        if (!cancelled) {
          setEncryption(enc)
          setBackup(bak)
          setSso(ssoCfg)
          setCost(costUsg)
          setDr(Array.isArray(drRuns) ? drRuns : [])
        }
      } catch {
        if (!cancelled) {
          setEncryption(null)
          setBackup(null)
          setSso(null)
          setCost(null)
          setDr([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  const evaluateReadiness = async () => {
    setReadinessError(null)
    try {
      const metrics = JSON.parse(metricsInput) as Record<string, number>
      const res = await governanceApi.readiness(metrics)
      setReadiness(res as unknown as Posture)
    } catch (e) {
      setReadiness(null)
      setReadinessError(e instanceof Error ? e.message : String(e))
    }
  }

  if (!AITDE_V3_ENABLED) {
    return (
      <div className="rounded-xl border bg-card p-6 text-card-foreground">
        <h2 className="text-base font-semibold">AITDE V4.0 治理</h2>
        <p className="mt-2 text-sm text-muted-foreground">需启用 AITDE V3 功能开关后开放。</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="grid min-h-[280px] place-items-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const encPass = Boolean(encryption && (encryption as { pass?: boolean }).pass)
  const bakPass = Boolean(backup && (backup as { pass?: boolean }).pass)
  const ssoConfigured = Boolean(sso && (sso as { configured?: boolean }).configured)
  const costTotal = (cost as { total_cost?: number } | null)?.total_cost ?? 0

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-lg font-semibold tracking-[-0.02em]">AITDE 治理控制台</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          企业治理（V40-009..020）：加密、备份/DR、SSO、成本、平台就绪。真实 IdP / 恢复演练为外部项，此处展示配置与记录。
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <PostureCard title="加密与传输" ok={encPass} detail="at-rest / transport 配置校验" />
        <PostureCard title="HA / Backup" ok={bakPass} detail="备份 / 对象存储 / Temporal 就绪清单" />
        <PostureCard title="SSO" ok={ssoConfigured} detail={`OIDC/SAML ${ssoConfigured ? '已配置' : '未配置'}（真实 IdP 外部）`} />
        <PostureCard title="成本记账" ok={null} detail={`累计模型成本 ≈ ${costTotal.toFixed(2)}`} />
        <PostureCard title="DR 演练" ok={dr.length > 0} detail={`已记录 ${dr.length} 次 drill`} />
      </div>

      <div className="rounded-xl border bg-card p-4 text-card-foreground">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Platform Readiness Gate</h3>
          <button
            type="button"
            onClick={() => void evaluateReadiness()}
            className="rounded-md bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90"
          >
            运行评估
          </button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          按 V40-018 阈值评估（P0 False Pass &lt;1%、False Fail &lt;3%、Evidence Completeness &gt;99%、Prod Unauthorized Write=0 等）。指标由真实运行采集后填入；这里供校验器评估，不假定通过。
        </p>
        <textarea
          aria-label="readiness metrics json"
          value={metricsInput}
          onChange={(e) => setMetricsInput(e.target.value)}
          rows={8}
          className="mt-3 w-full rounded-md border bg-background p-2 font-mono text-xs"
        />
        {readinessError && <p className="mt-2 text-xs text-destructive">{readinessError}</p>}
        {readiness && (
          <div className="mt-3">
            <span
              className={
                (readiness as { pass?: boolean }).pass
                  ? 'rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary'
                  : 'rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-destructive'
              }
            >
              {readiness.pass ? 'PASS' : 'FAIL'}
            </span>
            <span className="ml-2 text-xs text-muted-foreground">
              failed: {((readiness as { failed?: string[] }).failed ?? []).join(', ') || '无'}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
