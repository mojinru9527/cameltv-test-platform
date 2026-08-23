import { useMemo, useState } from 'react'
import { Badge, Button } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AsyncState } from '@/components/state'
import {
  fetchOpsDeploymentEvents,
  fetchOpsDeployments,
  publishOpsDeployment,
  rollbackOpsDeployment,
  backupOpsDeployment,
  submitOpsRelease,
  type OpsDeployment,
  type OpsActionResult,
} from '@/api/opsReleases'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { AlertTriangle, Clock, RefreshCw, Upload, RotateCcw, Save, Plus, Loader2, ShieldCheck } from '@/lib/icons'
import { isReleaseControlUnavailable } from './releaseAvailability'
import { toast } from 'sonner'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'

const STATE_LABEL: Record<string, string> = {
  DRAFT: '草稿',
  VALIDATED: '已校验',
  TEST_DEPLOYING: '测试部署中',
  TEST_VERIFYING: '测试验证中',
  TEST_VERIFIED: '测试已验证',
  TEST_FAILED: '测试失败',
  TEST_ROLLING_BACK: '测试回滚中',
  TEST_ROLLED_BACK: '测试已回滚',
  PROD_DEPLOYING: '生产部署中',
  PROD_OBSERVING: '生产观察中',
  PRODUCTION_VERIFIED: '生产已验证',
  PROD_FAILED: '生产失败',
  PROD_ROLLING_BACK: '生产回滚中',
  PROD_ROLLED_BACK: '生产已回滚',
  CANCELLED: '已取消',
}

function stateVariant(state: string): 'secondary' | 'outline' | 'destructive' {
  if (state.endsWith('_FAILED')) return 'destructive'
  if (state.endsWith('_VERIFIED') || state.endsWith('_ROLLED_BACK')) return 'outline'
  if (state === 'PROD_DEPLOYING' || state === 'PROD_OBSERVING') return 'secondary'
  return 'secondary'
}

function DeploymentRow({ deployment, selected, onSelect }: {
  deployment: OpsDeployment
  selected: boolean
  onSelect: (deployment: OpsDeployment) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(deployment)}
      aria-label={'查看发布记录 ' + deployment.release_id}
      className={'min-h-11 w-full rounded-md border p-3 text-left transition-colors ' +
        (selected ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/60')}
    >
      <div className='flex flex-wrap items-center gap-2'>
        <span className='font-medium'>{deployment.release_id}</span>
        <Badge variant={stateVariant(deployment.state)}>{STATE_LABEL[deployment.state] ?? deployment.state}</Badge>
        <span className='text-xs text-muted-foreground'>{deployment.environment}</span>
      </div>
      <p className='mt-1 truncate font-mono text-[11px] text-muted-foreground' title={deployment.manifest_sha256}>
        Manifest {deployment.manifest_sha256}
      </p>
    </button>
  )
}

function fmtManifest(body: { releaseId: string; gitSha: string; frontendDigest: string; backendDigest: string }) {
  const manifest = {
    schema_version: '1.0',
    release_id: body.releaseId,
    git_sha: body.gitSha,
    frontend: {
      image: 'cameltv-tp-frontend',
      digest: 'sha256:' + body.frontendDigest,
      sbom_sha256: '0'.repeat(64),
    },
    backend: {
      image: 'cameltv-tp-backend',
      digest: 'sha256:' + body.backendDigest,
      sbom_sha256: '0'.repeat(64),
      openapi_sha256: '0'.repeat(64),
    },
    database: {
      alembic_heads: ['see-verified-head'],
      target_revision: 'see-verified-head',
      rollback_mode: 'application-rollback-or-forward-fix',
    },
    config_schema: 'platform-runtime/v1',
    secret_refs: ['secret://production/cameltv/platform@v1'],
    qa_evidence: ['artifact://release-platform/qa-e2e'],
  }
  return JSON.stringify(manifest)
}

function Field({ label, value, onChange, placeholder }: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <label className='block'>
      <span className='mb-1 block text-sm font-medium'>{label}</span>
      <input
        className='h-8 w-full rounded-md border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring'
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </label>
  )
}

function SubmitDialog({ open, onClose, onSubmitted }: {
  open: boolean
  onClose: () => void
  onSubmitted: () => void
}) {
  const [releaseId, setReleaseId] = useState('')
  const [gitSha, setGitSha] = useState('')
  const [frontendDigest, setFrontendDigest] = useState('')
  const [backendDigest, setBackendDigest] = useState('')
  const [imageTag, setImageTag] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!open) return null

  const submit = async () => {
    if (!releaseId || !gitSha || !frontendDigest || !backendDigest || !imageTag) {
      toast.error('请填写全部字段')
      return
    }
    setSubmitting(true)
    try {
      const manifestJson = fmtManifest({ releaseId, gitSha, frontendDigest, backendDigest })
      const result = await submitOpsRelease({
        release_id: releaseId,
        environment: 'production',
        image_tag: imageTag,
        manifest_json: manifestJson,
      })
      toast.success('发布登记成功: ' + result.summary)
      onSubmitted()
      onClose()
    } catch (err) {
      toast.error('提交失败: ' + (err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className='sm:max-w-lg'>
        <DialogHeader>
          <DialogTitle>提交发布登记</DialogTitle>
        </DialogHeader>
        <div className='space-y-3'>
          <Field label='Release ID' value={releaseId} onChange={setReleaseId} placeholder='rel-20260823-0001' />
          <Field label='Git SHA' value={gitSha} onChange={setGitSha} placeholder='40 位 commit sha' />
          <Field label='前端镜像 Digest' value={frontendDigest} onChange={setFrontendDigest} placeholder='64 位 sha256 hex' />
          <Field label='后端镜像 Digest' value={backendDigest} onChange={setBackendDigest} placeholder='64 位 sha256 hex' />
          <Field label='镜像 Tag' value={imageTag} onChange={setImageTag} placeholder='release-20260823-0001' />
        </div>
        <div className='mt-5 flex justify-end gap-2'>
          <Button variant='ghost' onClick={onClose} disabled={submitting}>取消</Button>
          <Button onClick={submit} disabled={submitting}>
            {submitting && <Loader2 className='mr-1 size-4 animate-spin' />}
            提交登记
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function ActionButton({ label, icon, onRun, disabled, variant }: {
  label: string
  icon: React.ReactNode
  onRun: () => void
  disabled?: boolean
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
}) {
  return (
    <Button variant={variant ?? 'secondary'} size='sm' onClick={onRun} disabled={disabled}>
      {icon}
      {label}
    </Button>
  )
}

export default function OperationsReleasePage() {
  useDocumentTitle('运维发布控制')
  const [selected, setSelected] = useState<OpsDeployment | null>(null)
  const [showSubmit, setShowSubmit] = useState(false)
  const [runningAction, setRunningAction] = useState<string>('')
  const deployments = useApi(
    (signal) => fetchOpsDeployments(signal),
    { deps: [], showErrorToast: false },
  )
  const events = useApi(
    (signal) => selected ? fetchOpsDeploymentEvents(selected.id, signal) : Promise.resolve([]),
    { deps: [selected?.id], initialData: [], showErrorToast: false },
  )
  const releaseControlUnavailable = isReleaseControlUnavailable(deployments.error)

  const choose = (deployment: OpsDeployment) => setSelected(deployment)

  const refresh = () => {
    deployments.refetch()
    if (selected) setSelected(null)
  }

  const runAction = async (action: string, fn: () => Promise<OpsActionResult>) => {
    setRunningAction(action)
    try {
      const result = await fn()
      if (result.ok) {
        toast.success(result.action + ' 成功: ' + result.summary)
      } else {
        toast.error(result.action + ' 完成但需确认: ' + result.summary)
      }
      refresh()
    } catch (err) {
      toast.error(action + ' 失败: ' + (err as Error).message)
    } finally {
      setRunningAction('')
    }
  }

  const canPublish = useMemo(() => !!selected && ['VALIDATED', 'TEST_VERIFIED'].includes(selected.state), [selected])
  const canRollback = useMemo(() => !!selected && ['PROD_OBSERVING', 'PRODUCTION_VERIFIED', 'PROD_DEPLOYING'].includes(selected.state), [selected])
  const canBackup = useMemo(() => !!selected && ['PROD_DEPLOYING', 'PROD_OBSERVING', 'PRODUCTION_VERIFIED'].includes(selected.state), [selected])

  return (
    <div className='space-y-4'>
      <PageHeader
        title='运维发布控制'
        icon={ShieldCheck}
        description='腾讯云发布平台：提交登记 → 构建 → 发布 → 回滚 → 备份。发布记录经 release-control 持久化与审计。'
      >
        <Button variant='secondary' size='sm' onClick={() => setShowSubmit(true)}>
          <Plus className='mr-1 size-4' />
          提交发布登记
        </Button>
        <Button variant='secondary' size='sm' onClick={deployments.refetch} disabled={deployments.isLoading || deployments.isRefetching}>
          <RefreshCw className={'mr-1 size-4 ' + (deployments.isRefetching ? 'animate-spin' : '')} />
          刷新记录
        </Button>
      </PageHeader>

      {releaseControlUnavailable && (
        <Card className='border-status-warning-border bg-status-warning-muted'>
          <CardContent className='flex gap-2 p-3 text-sm text-status-warning' role='alert'>
            <AlertTriangle className='mt-0.5 size-4 shrink-0' aria-hidden />
            <p>当前环境未启用发布控制数据源。配置 RELEASE_CONTROL_DATABASE_PATH 与 TENCENT_EXECUTOR_* 环境变量后，发布/回滚/备份操作可用。</p>
          </CardContent>
        </Card>
      )}

      <div className='grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]'>
        <Card>
          <CardHeader className='pb-3'><CardTitle className='text-base'>发布记录</CardTitle></CardHeader>
          <CardContent>
            <AsyncState
              isLoading={deployments.isLoading}
              isError={deployments.isError && !releaseControlUnavailable}
              error={deployments.error}
              data={releaseControlUnavailable ? [] : deployments.data}
              onRetry={deployments.refetch}
              emptyTitle={releaseControlUnavailable ? '当前环境未启用发布控制数据源' : '暂无已持久化发布记录'}
              emptyDescription={releaseControlUnavailable
                ? '配置完成后使用“刷新记录”重新检测；未配置不代表服务异常。'
                : '点击“提交发布登记”创建第一条发布记录。'}
            >
              {(items) => <div className='space-y-2'>{items.map((item) => <DeploymentRow key={item.id} deployment={item} selected={item.id === selected?.id} onSelect={choose} />)}</div>}
            </AsyncState>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className='pb-3'><CardTitle className='text-base'>事件时间线</CardTitle></CardHeader>
          <CardContent>
            {!selected ? (
              <p className='text-sm text-muted-foreground'>选择一条发布记录以查看审计事件与操作入口。</p>
            ) : (
              <>
                <div className='mb-4 flex flex-wrap gap-2'>
                  <ActionButton
                    label='发布到生产'
                    icon={runningAction === 'publish' ? <Loader2 className='mr-1 size-3.5 animate-spin' /> : <Upload className='mr-1 size-3.5' />}
                    onRun={() => runAction('publish', () => publishOpsDeployment(selected.id, { image_tag: 'rel-preview' }))}
                    disabled={!canPublish || !!runningAction}
                  />
                  <ActionButton
                    label='回滚'
                    icon={runningAction === 'rollback' ? <Loader2 className='mr-1 size-3.5 animate-spin' /> : <RotateCcw className='mr-1 size-3.5' />}
                    onRun={() => runAction('rollback', () => rollbackOpsDeployment(selected.id, { image_tag: 'rel-prev' }))}
                    disabled={!canRollback || !!runningAction}
                    variant='danger'
                  />
                  <ActionButton
                    label='备份'
                    icon={runningAction === 'backup' ? <Loader2 className='mr-1 size-3.5 animate-spin' /> : <Save className='mr-1 size-3.5' />}
                    onRun={() => runAction('backup', () => backupOpsDeployment(selected.id))}
                    disabled={!canBackup || !!runningAction}
                  />
                </div>
                <AsyncState
                  isLoading={events.isLoading}
                  isError={events.isError}
                  error={events.error}
                  data={events.data}
                  onRetry={events.refetch}
                  emptyTitle='暂无审计事件'
                  emptyDescription='该记录尚未写入可展示的发布状态变化。'
                >
                  {(items) => <ol className='space-y-3'>{items.map((event) => <li key={event.sequence} className='border-l-2 border-primary/40 pl-3'><div className='flex items-center gap-2'><Badge variant='secondary'>#{event.sequence}</Badge><span className='text-sm font-medium'>{STATE_LABEL[event.to_state] ?? event.to_state}</span></div><p className='mt-1 text-sm text-muted-foreground'>{event.reason}</p><p className='mt-1 flex items-center gap-1 text-[11px] text-muted-foreground'><Clock className='size-3' aria-hidden />{event.phase} · {event.actor} · {new Date(event.created_at).toLocaleString('zh-CN')}</p></li>)}</ol>}
                </AsyncState>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <SubmitDialog open={showSubmit} onClose={() => setShowSubmit(false)} onSubmitted={deployments.refetch} />
    </div>
  )
}