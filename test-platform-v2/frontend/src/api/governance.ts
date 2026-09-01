import { aitdeV2 } from './missions'

/** AITDE V4.0 Enterprise governance API (V40-009..020). */
export const governanceApi = {
  readiness: (metrics: Record<string, number>) =>
    aitdeV2.post('/governance/readiness', metrics).then((r) => r.data.data),
  encryption: () => aitdeV2.get('/governance/encryption').then((r) => r.data.data),
  backup: () => aitdeV2.get('/governance/backup').then((r) => r.data.data),
  sso: () => aitdeV2.get('/governance/sso').then((r) => r.data.data),
  cost: () => aitdeV2.get('/governance/cost').then((r) => r.data.data),
  dr: () => aitdeV2.get('/governance/dr').then((r) => r.data.data),
}
