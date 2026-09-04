export type TokenPurpose = 'ci' | 'worker'

export const TOKEN_PURPOSES: Array<{
  value: TokenPurpose
  label: string
  description: string
}> = [
  {
    value: 'ci',
    label: 'CI/CD 计划执行',
    description: '用于持续集成触发测试计划。',
  },
  {
    value: 'worker',
    label: 'Worker 执行节点',
    description: '仅用于 Worker 注册和持续心跳。',
  },
]

export function normalizeTokenPurpose(value: string | null): TokenPurpose {
  return value === 'worker' ? 'worker' : 'ci'
}

export function scopesForTokenPurpose(purpose: TokenPurpose): string[] {
  return purpose === 'worker' ? ['workers:register'] : ['trigger']
}

export function buildWorkerSetup(token: string, origin: string): string {
  const backendUrl = `${origin.replace(/\/+$/, '')}/api/v2`
  return [
    `export BACKEND_URL=${backendUrl}`,
    `export API_TOKEN=${token}`,
    'bash test-platform-v2/deploy/aitde-runtime/scripts/start-worker.sh TEST HTTP,BROWSER',
  ].join('\n')
}
