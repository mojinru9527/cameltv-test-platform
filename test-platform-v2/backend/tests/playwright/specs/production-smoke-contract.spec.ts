import { expect, test } from '@playwright/test'

import {
  BlockedSmokeError,
  assertApiAssetsObserved,
  assertAuthenticatedSession,
  assertProductionRequestAllowed,
  readAuthorizedLogin,
  readProductionSmokeRuntime,
} from '../support/production-smoke-contract'

test.describe('Batch 61 production smoke truth contract', () => {
  test('missing explicit base URL blocks before navigation', () => {
    expect(() => readProductionSmokeRuntime({})).toThrow(BlockedSmokeError)
    expect(() => readProductionSmokeRuntime({})).toThrow(
      /B61-BLOCKED:BASE_URL/,
    )
  })

  test('missing business fixture cannot produce a green smoke result', () => {
    expect(() =>
      readProductionSmokeRuntime({
        BASE_URL: 'https://www.camel1.tv',
        PROD_ALLOWED_HOSTS: 'www.camel1.tv',
      }),
    ).toThrow(/B61-BLOCKED:PROD_EXPECTED_BUSINESS_TEXT/)
  })

  test('login requires explicit authorization and both credentials', () => {
    expect(() => readAuthorizedLogin({})).toThrow(
      /B61-BLOCKED:PROD_LOGIN_AUTHORIZED/,
    )
    expect(() =>
      readAuthorizedLogin({ PROD_LOGIN_AUTHORIZED: 'true' }),
    ).toThrow(/B61-BLOCKED:PROD_PHONE/)
    expect(() =>
      readAuthorizedLogin({
        PROD_LOGIN_AUTHORIZED: 'true',
        PROD_PHONE: 'authorized-user',
      }),
    ).toThrow(/B61-BLOCKED:PROD_PASSWORD/)
  })

  test('zero API assets fails instead of satisfying a tautology', () => {
    expect(() => assertApiAssetsObserved([])).toThrow(
      /no successful core API asset/i,
    )
    expect(() =>
      assertApiAssetsObserved([
        { url: 'https://api.cameltv.live/api/home', status: 200 },
      ]),
    ).not.toThrow()
    expect(() =>
      assertApiAssetsObserved([
        { url: 'https://api.cameltv.live/api/home', status: 302 },
      ]),
    ).toThrow(/no successful core API asset/i)
  })

  test('production subrequests require an explicit host and read-only method', () => {
    const runtime = readProductionSmokeRuntime({
      BASE_URL: 'https://www.camel1.tv',
      PROD_ALLOWED_HOSTS: 'www.camel1.tv,api.camel1.tv',
      PROD_EXPECTED_BUSINESS_TEXT: 'Camel Live',
    })

    expect(() =>
      assertProductionRequestAllowed(
        runtime,
        'https://api.camel1.tv/api/home',
        'GET',
      ),
    ).not.toThrow()
    expect(() =>
      assertProductionRequestAllowed(
        runtime,
        'https://cdn.camel1.tv/app.js',
        'GET',
      ),
    ).toThrow(/B61-BLOCKED:PROD_REQUEST_HOST/)
    expect(() =>
      assertProductionRequestAllowed(
        runtime,
        'https://api.camel1.tv/api/order',
        'POST',
      ),
    ).toThrow(/B61-BLOCKED:PROD_WRITE_METHOD/)
  })

  test('login rejection and absent authenticated marker fail', () => {
    expect(() => assertAuthenticatedSession(false, 'invalid credentials')).toThrow(
      /login rejected/i,
    )
    expect(() => assertAuthenticatedSession(false, '')).toThrow(
      /authenticated session marker/i,
    )
    expect(() => assertAuthenticatedSession(true, '')).not.toThrow()
  })
})
