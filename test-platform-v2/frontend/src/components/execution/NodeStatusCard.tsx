import { useEffect, useState } from 'react'
import { Link } from 'react-router'

import { fetchNodeStatus, nodeStartCommand, NODE_STATUS_POLL_MS, type NodeStatus } from '@/api/executionJobs'
import { AsyncState } from '@/components/state'
import { useApi } from '@/hooks/useApi'
import { AlertTriangle, Check, Copy, RefreshCw, Server } from '@/lib/icons'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '@/ui'

export interface NodeStatusCardProps {
  className?: string
}

/**
 * 执行节点状态卡（Batch 258 / B1-6）。
 *
 * 四态：Loading（骨架） / Error（可重试） / 离线（明确提示 + 一键启动指引） / 在线（队列与运行中）。
 * 轮询间隔 NODE_STATUS_POLL_MS，满足「节点上线后 10s 内刷新」；卸载时清理定时器。
 */
export function NodeStatusCard({ className }: NodeStatusCardProps) {
  const { data, isLoading, isRefetching, isError, error, refetch } = useApi<NodeStatus>(
    (signal) => fetchNodeStatus(signal),
    [],
  )
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const timer = window.setInterval(() => refetch(), NODE_STATUS_POLL_MS)
    return () => window.clearInterval(timer)
  }, [refetch])

  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 2000)
    return () => window.clearTimeout(timer)
  }, [copied])

  const command = nodeStartCommand()
  const copyCommand = async () => {
    try {
      await navigator.clipboard?.writeText(command)
      setCopied(true)
    } catch {
      // 剪贴板不可用（http/权限）时命令本身仍可见，用户可手动复制，不阻塞主流程
      setCopied(false)
    }
  }

  return (
    <Card size="sm" className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Server className="size-4 text-primary" />
          <span>执行节点</span>
          <span className="text-xs font-normal text-muted-foreground">
            测试执行跑在你自己机器上，平台不代跑
          </span>
          {data ? (
            <Badge variant={data.online_nodes > 0 ? 'secondary' : 'outline'} className="ml-auto">
              {data.online_nodes > 0 ? `在线 ${data.online_nodes}` : '未连接'}
            </Badge>
          ) : null}
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
          loadingText="正在检查执行节点"
          errorTitle="无法读取执行节点状态"
          errorDescription="平台暂时查不到节点状态，请稍后重试。"
        >
          {(status) => {
            // 首页是最常被打开的页面：字段缺失绝不能把整页搞崩，宁可显示"未连接"。
            const nodes = Array.isArray(status.nodes) ? status.nodes : []
            const onlineNodes = Number(status.online_nodes ?? 0)
            const queueLength = Number(status.queue_length ?? 0)
            const runningJobs = Number(status.running_jobs ?? 0)
            const stalledJobs = Number(status.stalled_jobs ?? 0)
            return onlineNodes === 0 ? (
              <div
                data-testid="node-offline"
                className="space-y-2 rounded-md border border-dashed px-3 py-3 text-xs text-muted-foreground"
              >
                <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                  <AlertTriangle className="size-4 text-destructive" />
                  本地节点未连接
                </div>
                <p>
                  现在没有可用的执行节点，任务会排队等待，直到你把节点跑起来。在你自己的机器上执行：
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <code className="rounded bg-muted px-2 py-1 font-mono text-xs text-foreground">
                    {command}
                  </code>
                  <Button size="sm" variant="outline" onClick={copyCommand}>
                    {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                    <span className="ml-1">{copied ? '已复制' : '复制'}</span>
                  </Button>
                </div>
                <p>
                  首次使用需要先 <code className="font-mono">login --username &lt;账号&gt;</code> 签发节点令牌；
                  详细说明见 <span className="font-mono">scripts/node/README.md</span>。
                </p>
                {queueLength > 0 ? (
                  <p className="text-destructive">
                    当前有 {queueLength} 个任务在排队，没有节点时不会被执行。
                  </p>
                ) : null}
              </div>
            ) : (
              <div data-testid="node-online" className="space-y-2 text-sm">
                <div className="flex flex-wrap items-center gap-3">
                  <span>
                    在线节点 <strong>{onlineNodes}</strong>
                  </span>
                  <span>
                    排队 <strong>{queueLength}</strong>
                  </span>
                  <span>
                    运行中 <strong>{runningJobs}</strong>
                  </span>
                  {isRefetching ? (
                    <RefreshCw className="size-3.5 animate-spin text-muted-foreground" />
                  ) : null}
                </div>
                {stalledJobs > 0 ? (
                  <p className="text-destructive">
                    有 {stalledJobs} 个任务心跳已超时，将在租约过期后自动回到待执行。
                  </p>
                ) : null}
                <ul className="space-y-1 text-xs text-muted-foreground">
                  {nodes.map((node) => (
                    <li key={node.node_id} className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-foreground">{node.node_id}</span>
                      <Badge variant={node.status === 'online' ? 'secondary' : 'outline'}>
                        {node.status === 'online' ? '在线' : '离线'}
                      </Badge>
                      {node.capabilities?.length ? (
                        <span>能力：{node.capabilities.join(' / ')}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
                <Button size="sm" variant="outline" onClick={refetch}>
                  <RefreshCw className="size-3.5" />
                  <span className="ml-1">刷新</span>
                </Button>
              </div>
            )
          }}
        </AsyncState>
        {data && Number(data.queue_length ?? 0) > 0 ? (
          <Link to="/report" className="text-xs text-primary hover:underline">
            查看排队中的执行任务
          </Link>
        ) : null}
      </CardContent>
    </Card>
  )
}

export default NodeStatusCard
