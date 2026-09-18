import api from './client'

/**
 * 本地执行节点（Batch 258 / B1-5、B1-6）。
 *
 * 平台的**控制面只做登记 · 调度 · 证据 · 知识**：接口与 Web 用例的真实执行发生在
 * 测试人员本机的 `cameltv-node` 里（ADR-0026 / 09-platform-landing-plan.md §3.1）。
 * 因此这里回答的问题是「为什么我点了没反应」——没有节点时，必须明确说出来。
 */

export interface ExecutionNode {
  node_id: string
  status: string
  capabilities: string[]
  last_health_at: string | null
}

export interface NodeStatus {
  online_nodes: number
  queue_length: number
  running_jobs: number
  stalled_jobs: number
  nodes: ExecutionNode[]
}

/**
 * 轮询间隔。backlog B1-6 的 DoD 是「节点上线后 10s 内状态刷新」，
 * 取 8s 留出网络与渲染余量；改动此值必须同步更新 __tests__ 里的断言。
 */
export const NODE_STATUS_POLL_MS = 8000

export async function fetchNodeStatus(signal?: AbortSignal): Promise<NodeStatus> {
  return api.get('/execution-jobs/node-status', { signal })
}

/** 一键启动指引：与 `scripts/node/README.md` 的命令保持一致。 */
export function nodeStartCommand(nodeId = 'my-pc'): string {
  return `cameltv-node up --node-id ${nodeId}`
}
