import { expectTypeOf, it } from 'vitest'
import type {
  ApiEnvelope,
  ApiSchema,
  DashboardStats,
  LoginOut,
  TestCaseOut,
} from '../apiContract'

it('exposes generated OpenAPI schema aliases', () => {
  expectTypeOf<LoginOut>().toMatchTypeOf<ApiSchema['LoginOut']>()
  expectTypeOf<TestCaseOut>().toMatchTypeOf<ApiSchema['TestCaseOut']>()
  expectTypeOf<DashboardStats>().toMatchTypeOf<ApiSchema['DashboardStats']>()
  expectTypeOf<ApiEnvelope<LoginOut>>().toMatchTypeOf<{
    code: number
    msg: string
    data: LoginOut
  }>()
})
