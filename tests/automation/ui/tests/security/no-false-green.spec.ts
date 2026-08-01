import { expect, test } from '@playwright/test'

import {
  BlockedRunError,
  assertNetworkRequestAllowed,
  assertRequestMethodAllowed,
  parseRuntimePreconditions,
} from '../../utils/preconditions'
import { loadTestData, requireTestData } from '../../utils/test-data'

const validReadOnlyEnvironment = {
  CAMELTV_TARGET_ENV: 'test5',
  CAMELTV_BASE_URL: 'https://camelive-g3-test5.elelive.cn',
  CAMELTV_RUN_LEVEL: 'readonly',
  CAMELTV_ALLOWED_HOSTS: 'camelive-g3-test5.elelive.cn',
  CAMELTV_PRECONDITION_OWNER: 'sports-qa',
}

test.describe('Batch 61 fail-closed runtime preconditions', () => {
  test('missing target configuration blocks before any operation can start', () => {
    let operationStarted = false

    expect(() => {
      parseRuntimePreconditions({})
      operationStarted = true
    }).toThrow(BlockedRunError)

    expect(operationStarted).toBe(false)

    try {
      parseRuntimePreconditions({})
    } catch (error) {
      expect(error).toMatchObject({
        status: 'BLOCKED',
        key: 'CAMELTV_TARGET_ENV',
        owner: 'UNASSIGNED',
        code: 'B61-BLOCKED:CAMELTV_TARGET_ENV',
      })
    }
  })

  test('base URL host must be explicitly allowlisted', () => {
    expect(() =>
      parseRuntimePreconditions({
        ...validReadOnlyEnvironment,
        CAMELTV_ALLOWED_HOSTS: 'another-test5.example',
      }),
    ).toThrow(/B61-BLOCKED:CAMELTV_ALLOWED_HOSTS/)
  })

  test('production accepts GET and HEAD but rejects write methods', () => {
    const production = parseRuntimePreconditions({
      ...validReadOnlyEnvironment,
      CAMELTV_TARGET_ENV: 'production',
      CAMELTV_BASE_URL: 'https://www.camel1.tv',
      CAMELTV_ALLOWED_HOSTS: 'www.camel1.tv',
    })

    expect(() => assertRequestMethodAllowed(production, 'GET')).not.toThrow()
    expect(() => assertRequestMethodAllowed(production, 'HEAD')).not.toThrow()
    expect(() => assertRequestMethodAllowed(production, 'POST')).toThrow(
      /B61-BLOCKED:PRODUCTION_WRITE_METHOD/,
    )
  })

  test('production cannot start in write-authorized mode', () => {
    expect(() =>
      parseRuntimePreconditions({
        ...validReadOnlyEnvironment,
        CAMELTV_TARGET_ENV: 'production',
        CAMELTV_BASE_URL: 'https://www.camel1.tv',
        CAMELTV_ALLOWED_HOSTS: 'www.camel1.tv',
        CAMELTV_RUN_LEVEL: 'write-authorized',
      }),
    ).toThrow(/B61-BLOCKED:PRODUCTION_RUN_LEVEL/)
  })

  test('browser requests stay on explicit hosts and production methods stay read-only', () => {
    const production = parseRuntimePreconditions({
      ...validReadOnlyEnvironment,
      CAMELTV_TARGET_ENV: 'production',
      CAMELTV_BASE_URL: 'https://sports.example.test',
      CAMELTV_ALLOWED_HOSTS: 'sports.example.test',
    })

    expect(() =>
      assertNetworkRequestAllowed(
        production,
        'https://sports.example.test/api/home',
        'GET',
      ),
    ).not.toThrow()
    expect(() =>
      assertNetworkRequestAllowed(
        production,
        'https://cdn.sports.example.test/asset.js',
        'GET',
      ),
    ).toThrow(/B61-BLOCKED:REQUEST_HOST/)
    expect(() =>
      assertNetworkRequestAllowed(
        production,
        'https://sports.example.test/api/session',
        'POST',
      ),
    ).toThrow(/B61-BLOCKED:PRODUCTION_WRITE_METHOD/)
  })
})

test.describe('Batch 61 deterministic sports data contract', () => {
  test('missing manifest is BLOCKED and names the accountable owner', () => {
    expect(() =>
      loadTestData({ CAMELTV_DATA_OWNER: 'sports-data-owner' }),
    ).toThrow(/B61-BLOCKED:CAMELTV_TEST_DATA_JSON/)

    try {
      loadTestData({ CAMELTV_DATA_OWNER: 'sports-data-owner' })
    } catch (error) {
      expect(error).toMatchObject({
        status: 'BLOCKED',
        owner: 'sports-data-owner',
      })
    }
  })

  test('required business key must exist and cannot be selected by first/random row', () => {
    const data = loadTestData({
      CAMELTV_TEST_DATA_JSON: JSON.stringify({
        home: { recommendedAuthorKey: 'author-yield-001' },
      }),
    })

    expect(requireTestData(data, 'home.recommendedAuthorKey')).toBe(
      'author-yield-001',
    )
    expect(() => requireTestData(data, 'articles.paidLossKey')).toThrow(
      /B61-BLOCKED:DATA:articles.paidLossKey/,
    )
  })

  test('test-data manifest rejects credential-bearing fields', () => {
    expect(() =>
      loadTestData({
        CAMELTV_TEST_DATA_JSON: JSON.stringify({
          account: { password: 'must-not-enter-a-data-manifest' },
        }),
      }),
    ).toThrow(/B61-BLOCKED:TEST_DATA_SENSITIVE_FIELD/)
  })
})
