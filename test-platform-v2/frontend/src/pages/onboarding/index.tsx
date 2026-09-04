import { useState } from 'react'
import { Link } from 'react-router'
import { Badge, Button, Input, Label, PageShell, Textarea } from '@/ui'
import {
  advanceOnboarding,
  createOnboarding,
  getOnboardingReadiness,
  listOnboardings,
  type Onboarding,
  type OnboardingReadiness,
  type OnboardingServiceReadiness,
} from '@/api/versionTask'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { AlertCircle, CheckCircle2, Loader2, RefreshCw, Settings } from '@/lib/icons'
import { toast } from 'sonner'

const STATUS_LABELS: Record<string, string> = {
  onboarding: '接入中',
  active: '已启用',
  blocked: '已阻塞',
  archived: '已归档',
}

const STEPS = ['登记业务', '导入接口基线', '生成 AI 验收方案', '运行真实基线']

type BaselineSummary = {
  status?: string
  passed?: number
  failed?: number
  skipped?: number
  blocked?: number
}

function parseBaseline(raw: string): BaselineSummary | null {
  try {
    const value = JSON.parse(raw)
    return value && typeof value === 'object' ? value as BaselineSummary : null
  } catch {
    return null
  }
}

function ReadinessRow({
  name,
  item,
  platformManaged = false,
  href,
}: {
  name: string
  item: OnboardingServiceReadiness
  platformManaged?: boolean
  href: string
}) {
  const ready = item.status === 'ready'
  const unknown = item.status === 'unknown'
  const Icon = ready ? CheckCircle2 : AlertCircle
  const statusText = ready ? '已就绪' : unknown ? '尚未验证' : '需要处理'
  const statusTone = ready ? 'success' : unknown ? 'warning' : 'danger'
  const iconClass = ready
    ? 'mt-0.5 size-4 text-status-success'
    : unknown
      ? 'mt-0.5 size-4 text-status-warning'
      : 'mt-0.5 size-4 text-destructive'

  return (
    <div className="flex min-w-0 flex-col gap-3 border-b border-border py-4 last:border-b-0 sm:flex-row sm:items-start">
      <Icon
        className={iconClass}
        aria-hidden="true"
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-foreground">{name}</span>
          <Badge tone={statusTone}>{statusText}</Badge>
        </div>
        <p className="mt-1 text-sm leading-relaxed text-muted-hc">{item.message}</p>
        {platformManaged && (
          <p className="mt-1 text-xs text-muted-foreground">由平台常驻管理，无需每次手动启动</p>
        )}
      </div>
      {!ready && (
        <Link
          to={href}
          className="inline-flex min-h-11 shrink-0 items-center gap-1.5 text-sm font-medium text-primary hover:underline"
        >
          <Settings className="size-4" aria-hidden="true" />
          查看配置
        </Link>
      )}
    </div>
  )
}

export default function OnboardingPage() {
  const [name, setName] = useState('')
  const [serviceKey, setServiceKey] = useState('')
  const [version, setVersion] = useState('')
  const [requirementText, setRequirementText] = useState('')
  const [apiSpec, setApiSpec] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [ob, setOb] = useState<Onboarding | null>(null)
  const [items, setItems] = useState<Onboarding[]>([])
  const [listError, setListError] = useState('')
  const [readiness, setReadiness] = useState<OnboardingReadiness | null>(null)
  const [readinessError, setReadinessError] = useState('')
  const [readinessLoading, setReadinessLoading] = useState(true)
  const [reloadVersion, setReloadVersion] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [advancing, setAdvancing] = useState(false)

  useAbortableEffect((signal) => {
    setReadinessLoading(true)
    Promise.allSettled([listOnboardings(signal), getOnboardingReadiness(signal)])
      .then(([listResult, readinessResult]) => {
        if (signal.aborted) return
        if (listResult.status === 'fulfilled') {
          setItems(listResult.value)
          setListError('')
        } else {
          setListError(listResult.reason instanceof Error ? listResult.reason.message : '接入记录加载失败')
        }
        if (readinessResult.status === 'fulfilled') {
          setReadiness(readinessResult.value)
          setReadinessError('')
        } else {
          setReadiness(null)
          setReadinessError(
            readinessResult.reason instanceof Error
              ? readinessResult.reason.message
              : '自动检查暂不可用',
          )
        }
        setReadinessLoading(false)
      })
  }, [reloadVersion])

  async function refreshList() {
    try {
      setItems(await listOnboardings())
      setListError('')
    } catch (error) {
      setListError((error as Error).message || '接入记录加载失败')
    }
  }

  const formComplete = [name, serviceKey, version, requirementText, apiSpec, baseUrl]
    .every((value) => value.trim().length > 0)

  async function handleCreate() {
    if (!formComplete || submitting) return
    setSubmitting(true)
    try {
      const created = await createOnboarding({
        name: name.trim(),
        service_key: serviceKey.trim(),
        version: version.trim(),
        requirement_text: requirementText.trim(),
        api_spec_url: apiSpec.trim(),
        base_url: baseUrl.trim(),
      })
      setOb(created)
      toast.success('业务信息已保存，可以导入接口基线')
      void refreshList()
    } catch (error) {
      toast.error((error as Error).message || '业务信息保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  async function advance() {
    if (!ob || ob.step >= 4 || advancing) return
    setAdvancing(true)
    try {
      const next = await advanceOnboarding(ob.id, ob.step + 1)
      setOb(next)
      if (next.step === 4) {
        toast[next.status === 'active' ? 'success' : 'error'](
          next.status === 'active' ? '真实基线已通过，业务已启用' : '真实基线存在阻塞，业务未启用',
        )
      } else {
        toast.success(next.step === 2 ? '接口基线已导入' : 'AI 验收方案已生成')
      }
      void refreshList()
    } catch (error) {
      toast.error((error as Error).message || '当前步骤执行失败')
    } finally {
      setAdvancing(false)
    }
  }

  const nextAction = ob && ob.step < 4 ? STEPS[ob.step] : ''
  const aiStepBlocked = ob?.step === 2 && readiness?.baseline_ready !== true

  return (
    <PageShell
      title="AI 全链路接入"
      description="先填写业务资料，平台会自动检查 AI 与运行服务。Temporal 和 Worker 由平台维护，无需您手动启动。"
    >
      <div className="space-y-6">
        <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.8fr)]">
          <section aria-labelledby="required-fields-title" className="min-w-0 border-b border-border pb-6 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-6">
            <div className="mb-4">
              <h2 id="required-fields-title" className="text-base font-semibold text-foreground">你需要填写</h2>
              <p className="mt-1 text-sm text-muted-hc">共 6 项。请勿在下列文本框粘贴密码、Token 或 API Key。</p>
            </div>

            {!ob ? (
              <div className="grid min-w-0 gap-4 md:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="onboarding-name">业务名称</Label>
                  <Input id="onboarding-name" placeholder="例如：体育平台" value={name} onChange={(event) => setName(event.target.value)} />
                  <p className="text-xs text-muted-foreground">用于页面和报告中的业务名称</p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="onboarding-service-key">服务标识</Label>
                  <Input id="onboarding-service-key" placeholder="例如：sports-service" value={serviceKey} onChange={(event) => setServiceKey(event.target.value)} />
                  <p className="text-xs text-muted-foreground">填写网关或 OpenAPI 中稳定的服务 key</p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="onboarding-version">本次版本</Label>
                  <Input id="onboarding-version" placeholder="例如：16.0.0" value={version} onChange={(event) => setVersion(event.target.value)} />
                  <p className="text-xs text-muted-foreground">版本号与服务标识分开记录</p>
                </div>
                <div className="space-y-1.5 md:col-span-2">
                  <Label htmlFor="onboarding-requirement">需求内容</Label>
                  <Textarea id="onboarding-requirement" rows={5} placeholder="粘贴本版本要验收的完整需求正文或摘要" value={requirementText} onChange={(event) => setRequirementText(event.target.value)} />
                  <p className="text-xs text-muted-foreground">该内容会进入 AI 验收方案上下文</p>
                </div>
                <div className="space-y-1.5 md:col-span-2">
                  <Label htmlFor="onboarding-openapi">OpenAPI 地址</Label>
                  <Input id="onboarding-openapi" type="url" placeholder="https://example.test/openapi.json" value={apiSpec} onChange={(event) => setApiSpec(event.target.value)} />
                  <p className="text-xs text-muted-foreground">必须是平台后端可访问的 JSON 或 YAML 地址</p>
                </div>
                <div className="space-y-1.5 md:col-span-2">
                  <Label htmlFor="onboarding-base-url">被测服务地址</Label>
                  <Input id="onboarding-base-url" type="url" placeholder="https://example.test" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
                  <p className="text-xs text-muted-foreground">当前接入基线要求平台可直接访问；内网和鉴权环境请先联系管理员配置</p>
                </div>
                <div className="flex flex-wrap items-center gap-3 md:col-span-2">
                  <Button variant="primary" size="lg" disabled={!formComplete} loading={submitting} onClick={handleCreate}>
                    保存并开始接入
                  </Button>
                  <Link to="/environment" className="inline-flex min-h-11 items-center text-sm font-medium text-primary hover:underline">
                    查看环境与凭据配置
                  </Link>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge variant="secondary">{ob.service_key}</Badge>
                  <span className="font-medium text-foreground">{ob.name}</span>
                  <span className="text-muted-hc">版本 {ob.version}</span>
                </div>
                <details>
                  <summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium text-primary hover:underline">
                    查看已保存需求（{ob.requirement_text.length} 字）
                  </summary>
                  <p className="max-h-56 overflow-y-auto whitespace-pre-wrap border-y border-border py-3 text-sm leading-relaxed text-muted-hc">
                    {ob.requirement_text}
                  </p>
                </details>
              </div>
            )}
          </section>

          <section aria-labelledby="readiness-title" className="min-w-0">
            <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
              <div>
                <h2 id="readiness-title" className="text-base font-semibold text-foreground">平台自动检查</h2>
                <p className="mt-1 text-sm text-muted-hc">这些项目由平台或管理员维护，不需要业务用户填写。</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                disabled={readinessLoading}
                onClick={() => setReloadVersion((value) => value + 1)}
              >
                <RefreshCw className={readinessLoading ? 'size-4 animate-spin' : 'size-4'} aria-hidden="true" />
                重新检查
              </Button>
            </div>

            {readinessLoading && !readiness ? (
              <div className="flex min-h-32 items-center gap-2 text-sm text-muted-hc" role="status">
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                正在检查平台服务…
              </div>
            ) : readinessError ? (
              <div className="py-6" role="alert">
                <div className="flex items-center gap-2 font-medium text-destructive">
                  <AlertCircle className="size-4" aria-hidden="true" />
                  自动检查失败
                </div>
                <p className="mt-2 text-sm text-muted-hc">{readinessError}</p>
              </div>
            ) : readiness ? (
              <>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge tone={readiness.baseline_ready ? 'success' : 'danger'}>
                    {readiness.baseline_ready ? '业务接入基线已就绪' : '业务接入基线尚未就绪'}
                  </Badge>
                  <Badge tone={readiness.durable_ready ? 'success' : 'warning'}>
                    {readiness.durable_ready ? '耐久执行已就绪' : '可选耐久执行尚未就绪'}
                  </Badge>
                </div>
                <div className="mt-2">
                  <ReadinessRow name="AI 提供方" item={readiness.services.ai_provider} href="/ai-config" />
                  <ReadinessRow name="Temporal" item={readiness.services.temporal} platformManaged href="/admin/workers" />
                  <ReadinessRow name="Runtime Worker" item={readiness.services.runtime_worker} platformManaged href="/admin/workers" />
                </div>
                <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                  耐久能力未就绪不影响当前业务接入和同步基线；只有可恢复的 AITDE 执行才需要 Temporal 和在线 Worker。
                </p>
              </>
            ) : null}
          </section>
        </div>

        {ob && (
          <section aria-labelledby="progress-title" className="border-t border-border pt-6">
            <h2 id="progress-title" className="text-base font-semibold text-foreground">接入进度</h2>
            <ol className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {STEPS.map((label, index) => {
                const number = index + 1
                const completed = ob.step >= number
                const current = !completed && ob.step + 1 === number
                return (
                  <li key={label} className="flex min-h-12 items-center gap-3 border-b border-border pb-3 sm:border-b-0 sm:pb-0">
                    <Badge tone={completed ? 'success' : current ? 'info' : 'neutral'}>{number}</Badge>
                    <span className={completed || current ? 'font-medium text-foreground' : 'text-muted-hc'}>{label}</span>
                  </li>
                )
              })}
            </ol>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              {nextAction && (
                <Button variant="primary" size="lg" loading={advancing} disabled={aiStepBlocked} onClick={advance}>
                  {nextAction}
                </Button>
              )}
              {aiStepBlocked && <p className="text-sm text-status-warning">请先到 AI 配置完成真实连通性验证</p>}
              {ob.step === 4 && (() => {
                const baseline = parseBaseline(ob.baseline)
                return baseline ? (
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <Badge tone={baseline.status === 'done' ? 'success' : 'danger'}>
                      {baseline.status === 'done' ? '基线通过' : '基线阻塞'}
                    </Badge>
                    <span>通过 {baseline.passed ?? 0}</span>
                    <span>失败 {baseline.failed ?? 0}</span>
                    <span>跳过 {baseline.skipped ?? 0}</span>
                    <span>阻塞 {baseline.blocked ?? 0}</span>
                  </div>
                ) : <p className="text-sm text-destructive">基线结果不可读取</p>
              })()}
            </div>
          </section>
        )}

        <section aria-labelledby="history-title" className="border-t border-border pt-6">
          <h2 id="history-title" className="text-base font-semibold text-foreground">已接入业务</h2>
          {listError ? (
            <p className="mt-3 text-sm text-destructive" role="alert">{listError}</p>
          ) : items.length === 0 ? (
            <p className="mt-3 text-sm text-muted-hc">还没有接入记录。填写上方 6 项即可开始。</p>
          ) : (
            <div className="mt-3 divide-y divide-border border-y border-border">
              {items.map((item) => (
                <div key={item.id} className="flex min-h-12 flex-wrap items-center gap-2 py-3 text-sm">
                  <Badge variant="secondary">{item.service_key}</Badge>
                  <span className="font-medium text-foreground">{item.name}</span>
                  <span className="text-muted-hc">版本 {item.version || '未记录'}</span>
                  <span className="ml-auto text-xs text-muted-foreground">步骤 {item.step}/4 · {STATUS_LABELS[item.status] || item.status}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </PageShell>
  )
}
