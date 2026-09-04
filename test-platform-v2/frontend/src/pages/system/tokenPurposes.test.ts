import { describe, expect, it } from 'vitest'
import { buildWorkerSetup, scopesForTokenPurpose } from './tokenPurposes'

describe('token purposes', () => {
  it('maps Worker tokens to the minimum registration scope', () => {
    expect(scopesForTokenPurpose('worker')).toEqual(['workers:register'])
    expect(scopesForTokenPurpose('ci')).toEqual(['trigger'])
  })

  it('builds copyable Worker configuration without altering the token', () => {
    const setup = buildWorkerSetup('tpat_test_only', 'https://control.example/')

    expect(setup).toContain('BACKEND_URL=https://control.example/api/v2')
    expect(setup).toContain('API_TOKEN=tpat_test_only')
    expect(setup).toContain('start-worker.sh TEST HTTP,BROWSER')
  })
})
