import type { Page, Response } from '@playwright/test'

import { BlockedRunError } from './preconditions'
import { requireTestData, type SportsTestData } from './test-data'

export function requireStringTestData(
  data: SportsTestData,
  path: string,
  owner = process.env.CAMELTV_DATA_OWNER?.trim() || 'UNASSIGNED',
): string {
  const value = requireTestData(data, path, owner)
  if (typeof value !== 'string' || !value.trim()) {
    throw new BlockedRunError(
      `DATA:${path}`,
      owner,
      'required business value must be a non-empty string',
    )
  }
  return value.trim()
}

export async function observeSuccessfulApi(
  page: Page,
  rawPattern: string,
  action: () => Promise<unknown>,
): Promise<Response> {
  let pattern: RegExp
  try {
    pattern = new RegExp(rawPattern)
  } catch {
    throw new BlockedRunError(
      'DATA:apiPattern',
      process.env.CAMELTV_DATA_OWNER?.trim() || 'UNASSIGNED',
      'API response pattern is not a valid regular expression',
    )
  }

  const responsePromise = page.waitForResponse((response) => {
    pattern.lastIndex = 0
    return pattern.test(response.url()) && response.status() >= 200 && response.status() < 400
  })
  await action()
  return responsePromise
}
