import { zodResolver } from '@hookform/resolvers/zod'
import type { FieldValues, Resolver } from 'react-hook-form'
import type { z } from 'zod'

/**
 * zod v4 + react-hook-form 的类型适配层。
 *
 * zod v4 起 schema 的 input 与 output 可能不同（coerce / transform / default），
 * 而 @hookform/resolvers 的 zodResolver 泛型会把该差异带到每个表单的
 * useForm<Values> 上，产生 Resolver 泛型不兼容（本项目 15 处）。
 *
 * 这里把差异收敛到一个边界：运行时仍调用官方 zodResolver（校验行为完全不变），
 * 仅在类型层面放宽为 Resolver<T>；各表单 schema 的推导类型仍然生效。
 */
export function zodFormResolver<T extends FieldValues>(schema: z.ZodType): Resolver<T> {
  return zodResolver(schema as never) as unknown as Resolver<T>
}
