import { useState } from 'react'

import { fetchWhatToRun, type ImpactResult } from '@/api/impact'
import { AsyncState } from '@/components/state'
import { useApi } from '@/hooks/useApi'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input } from '@/ui'

/**
 * 影响面（Batch 260 / B3-3 前端视图）。
 *
 * 一个输入框回答「改了 X 要跑哪些」；每条结论都带 ref（case:/plan:/module:），
 * 保证"可以点回原始用例/执行记录"这条验收有落点，而不是只把 ID 打出来。
 */
export default function ImpactTab() {
  const [moduleName, setModuleName] = useState('')
  const [query, setQuery] = useState('')

  const { data, isLoading, isError, error, refetch } = useApi<ImpactResult>(
    (signal) => fetchWhatToRun({ module: query }, signal),
    [query],
  )

  const runQuery = () => setQuery(moduleName.trim())
  const hasQuery = query.length > 0

  return (
    <div className="space-y-4">
      <Card size="sm">
        <CardHeader>
          <CardTitle className="text-sm">改了哪些模块？</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Input
              aria-label="变更模块名"
              placeholder="例如：赛事 / 直播 / 体育"
              value={moduleName}
              onChange={(event) => setModuleName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') runQuery()
              }}
              className="h-9 sm:w-[260px]"
            />
            <Button size="sm" onClick={runQuery} disabled={!moduleName.trim()}>
              查询要跑哪些
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            结果 = 受影响模块 → 关联用例（功能/接口/UI）→ 最近一次执行结果 → 未覆盖缺口。
          </p>
        </CardContent>
      </Card>

      {!hasQuery ? (
        <div className="rounded-md border border-dashed px-3 py-6 text-center text-xs text-muted-foreground">
          输入模块名后查询。这里不会猜：没有关联就是没有关联。
        </div>
      ) : (
        <AsyncState
          isLoading={isLoading}
          isError={isError}
          error={error}
          data={data}
          onRetry={refetch}
          loadingVariant="skeleton"
          skeletonType="card"
          loadingRows={2}
          loadingText="正在查询影响面"
          errorTitle="查询失败"
        >
          {(result) => <ImpactResultView result={result} />}
        </AsyncState>
      )}
    </div>
  )
}

function ImpactResultView({ result }: { result: ImpactResult }) {
  const { counts, cases } = result
  if (counts.cases_total === 0 && counts.affected_modules === 0) {
    return (
      <div
        data-testid="impact-empty"
        className="rounded-md border border-dashed px-3 py-6 text-center text-xs text-muted-foreground"
      >
        <p className="text-sm text-foreground">没有找到与「{result.query.module}」关联的模块或用例</p>
        <p className="mt-1">
          {result.reason || '可能是模块名不匹配，或该版本的关联还没构建（可在影响面重建后重试）。'}
        </p>
      </div>
    )
  }

  return (
    <div data-testid="impact-result" className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span>
          受影响模块 <strong>{counts.affected_modules}</strong>
        </span>
        <span>
          关联用例 <strong>{counts.cases_total}</strong>
        </span>
        <span>
          缺口 <strong className={counts.gaps > 0 ? 'text-destructive' : undefined}>{counts.gaps}</strong>
        </span>
      </div>

      <section className="space-y-2">
        <h3 className="text-xs font-medium text-muted-foreground">受影响模块</h3>
        <ul className="flex flex-wrap gap-2">
          {result.affected_modules.map((name) => (
            <li key={name}>
              <Badge variant="secondary">{name}</Badge>
            </li>
          ))}
        </ul>
      </section>

      {(
        [
          ['functional', '功能用例'],
          ['api', '接口用例'],
          ['ui', 'UI 用例'],
        ] as const
      ).map(([key, label]) => (
        <section key={key} className="space-y-2">
          <h3 className="text-xs font-medium text-muted-foreground">
            {label}（{cases[key].length}）
          </h3>
          {cases[key].length === 0 ? (
            <p className="text-xs text-muted-foreground">无</p>
          ) : (
            <ul className="space-y-1">
              {cases[key].map((item) => (
                <li key={item.case_id} className="flex flex-wrap items-center gap-2 text-sm">
                  <a className="text-primary hover:underline" href={`/testcase?case=${item.case_id}`}>
                    {item.title}
                  </a>
                  <span className="font-mono text-xs text-muted-foreground">{item.ref}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}

      <section className="space-y-2">
        <h3 className="text-xs font-medium text-muted-foreground">最近一次执行</h3>
        {result.last_runs.length === 0 ? (
          <p className="text-xs text-muted-foreground">这些用例还没有执行记录</p>
        ) : (
          <ul className="space-y-1">
            {result.last_runs.map((run) => (
              <li key={`${run.case_id}-${run.plan_id}`} className="flex flex-wrap items-center gap-2 text-xs">
                <Badge variant={run.status === 'pass' ? 'secondary' : 'outline'}>{run.status}</Badge>
                <a className="text-primary hover:underline" href={`/report?plan=${run.plan_id}`}>
                  {run.ref}
                </a>
                <span className="text-muted-foreground">{run.executed_at ?? '未执行'}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {result.gaps.length > 0 ? (
        <section data-testid="impact-gaps" className="space-y-2">
          <h3 className="text-xs font-medium text-destructive">未覆盖缺口（没有关联用例）</h3>
          <ul className="flex flex-wrap gap-2">
            {result.gaps.map((name) => (
              <li key={name}>
                <Badge variant="outline">{name}</Badge>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  )
}
