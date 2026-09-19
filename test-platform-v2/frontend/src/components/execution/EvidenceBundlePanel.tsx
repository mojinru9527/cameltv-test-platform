import { verifyEvidenceBundle, type EvidenceVerification } from '@/api/executionJobs'
import { AsyncState } from '@/components/state'
import { useApi } from '@/hooks/useApi'
import { AlertTriangle, Check, ShieldCheck } from '@/lib/icons'
import { Badge, Card, CardContent, CardHeader, CardTitle } from '@/ui'

/**
 * 证据包校验面板（Batch 261 / B4-1）。
 *
 * 放行结论依赖证据，所以"证据被动过"必须一眼可见：
 * 篡改/缺失的文件用 destructive 语义显红，并单独列出**缺失的必需证据类型**
 * （回答"还缺什么"，而不是只报文件名）。
 */
export default function EvidenceBundlePanel({
  jobId,
  attempt,
}: {
  jobId: number
  attempt?: number
}) {
  const { data, isLoading, isError, error, refetch } = useApi<EvidenceVerification>(
    (signal) => verifyEvidenceBundle(jobId, attempt, signal),
    [jobId, attempt],
  )

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <ShieldCheck className="size-4 text-primary" />
          <span>证据包校验</span>
          <span className="text-xs font-normal text-muted-foreground">改一字节即判定失败</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <AsyncState
          isLoading={isLoading}
          isError={isError}
          error={error}
          data={data}
          onRetry={refetch}
          loadingVariant="skeleton"
          skeletonType="card"
          loadingRows={1}
          loadingText="正在校验证据包"
          errorTitle="证据校验失败"
        >
          {(result) => <VerificationView result={result} />}
        </AsyncState>
      </CardContent>
    </Card>
  )
}

function VerdictBanner({ result }: { result: EvidenceVerification }) {
  if (result.verdict === 'verified') {
    return (
      <div
        data-testid="verdict-verified"
        className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
      >
        <Check className="size-4 text-status-success" />
        <span>校验通过：证据未被改动，必需证据齐备</span>
      </div>
    )
  }
  if (result.verdict === 'tampered') {
    return (
      <div
        data-testid="verdict-tampered"
        className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive"
      >
        <AlertTriangle className="size-4" />
        <span>
          校验失败：{result.tampered.length} 个文件与 manifest 的 sha256 不一致，已不作为放行证据
        </span>
      </div>
    )
  }
  const missingTypes = result.completeness.missing
  return (
    <div
      data-testid={`verdict-${result.verdict}`}
      className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm text-destructive"
    >
      <AlertTriangle className="size-4" />
      <span>
        {result.reason ??
          `证据不完整：缺少必需证据 ${missingTypes.length ? missingTypes.join('、') : '（未知）'}`}
      </span>
    </div>
  )
}

function VerificationView({ result }: { result: EvidenceVerification }) {
  return (
    <div data-testid="evidence-verification" className="space-y-3">
      <VerdictBanner result={result} />

      {result.files.length > 0 ? (
        <ul className="space-y-1">
          {result.files.map((file) => {
            const bad = file.status !== 'ok'
            return (
              <li
                key={file.name}
                data-testid={`evidence-file-${file.name}`}
                className={
                  bad
                    ? 'flex flex-wrap items-center gap-2 text-xs text-destructive'
                    : 'flex flex-wrap items-center gap-2 text-xs text-muted-foreground'
                }
              >
                <Badge variant={bad ? 'destructive' : 'secondary'}>{file.status}</Badge>
                <span className="font-mono">{file.name}</span>
                {file.evidence_type ? (
                  <span className="text-muted-foreground">{file.evidence_type}</span>
                ) : null}
              </li>
            )
          })}
        </ul>
      ) : null}

      <div className="space-y-1 text-xs">
        <p className="text-muted-foreground">
          必需证据：{result.completeness.required.join('、') || '（无）'}
        </p>
        {result.completeness.complete ? (
          <p className="text-status-success">必需证据齐备</p>
        ) : (
          <p className="text-destructive">
            缺少必需证据：{result.completeness.missing.join('、') || '（见上方文件状态）'}
          </p>
        )}
        {result.extra.length > 0 ? (
          <p className="text-muted-foreground">清单外的额外文件：{result.extra.join('、')}</p>
        ) : null}
        {result.unclassified.length > 0 ? (
          <p className="text-muted-foreground">
            未识别证据类型（未参与必需证据判定）：{result.unclassified.join('、')}
          </p>
        ) : null}
      </div>
    </div>
  )
}
