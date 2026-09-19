import { useState } from 'react'

import { fetchExecutionJobs, type ExecutionJobList } from '@/api/executionJobs'
import EvidenceBundlePanel from './EvidenceBundlePanel'
import { AsyncState } from '@/components/state'
import { useApi } from '@/hooks/useApi'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '@/ui'

/**
 * 本地节点执行证据（Batch 261 / B4-1）。
 *
 * 挂在「结果与缺陷 → 执行记录」页：09 方案把执行记录归到入口③，因此证据校验的入口也应在这里。
 * 刻意**不逐行预取校验结果**（避免 N+1）：只列最近任务，点「校验证据」才发起一次校验请求。
 */
export default function LocalExecutionEvidenceSection() {
  const [selectedJob, setSelectedJob] = useState<number | null>(null)
  const { data, isLoading, isError, error, refetch } = useApi<ExecutionJobList>(
    (signal) => fetchExecutionJobs({ page_size: 5 }, signal),
    [],
  )

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <span>本地节点执行证据</span>
          <span className="text-xs font-normal text-muted-foreground">
            证据跑在测试人员机器上，平台只做校验与展示
          </span>
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
          loadingText="正在加载执行任务"
          errorTitle="无法加载执行任务"
        >
          {(list) =>
            list.items.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                暂无本地执行任务。执行由测试人员本机的 cameltv-node 完成，平台只登记与校验证据。
              </p>
            ) : (
              <ul className="space-y-2">
                {list.items.map((job) => (
                  <li key={job.id} className="flex flex-wrap items-center gap-2 text-xs">
                    <Badge variant="secondary">{job.kind}</Badge>
                    <span>
                      #{job.id} {job.status}
                    </span>
                    <span className="text-muted-foreground">
                      attempt {job.attempt}
                      {job.env_ref ? ` · ${job.env_ref}` : ''}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      className="ml-auto"
                      onClick={() => setSelectedJob(job.id)}
                    >
                      校验证据
                    </Button>
                  </li>
                ))}
              </ul>
            )
          }
        </AsyncState>

        {selectedJob !== null ? <EvidenceBundlePanel jobId={selectedJob} /> : null}
      </CardContent>
    </Card>
  )
}
