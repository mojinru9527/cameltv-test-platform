import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'

import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { Button, Input } from '@/ui'
import { Loader2, Lock, User } from '@/lib/icons'

const loginSchema = z.object({
  username: z.string().min(1, '请输入用户名'),
  password: z.string().min(1, '请输入密码'),
})

type LoginValues = z.infer<typeof loginSchema>

interface LoginFormProps {
  onSuccess: () => void
  submitLabel?: string
}

export default function LoginForm({ onSuccess, submitLabel = '登录' }: LoginFormProps) {
  const setLogin = useAuthStore((state) => state.setLogin)
  const [loading, setLoading] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  })

  const onSubmit = async (values: LoginValues) => {
    setLoading(true)
    setSubmitError('')
    try {
      const data = await login(values.username, values.password)
      setLogin(data)
      toast.success('登录成功')
      onSuccess()
    } catch (reason) {
      setSubmitError(reason instanceof Error ? reason.message : '登录失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="username" className="text-sm font-medium">用户名</label>
        <div className="relative">
          <User className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            id="username"
            className="pl-9"
            placeholder="用户名"
            autoComplete="username"
            {...register('username')}
            data-invalid={!!errors.username}
            aria-invalid={!!errors.username}
            aria-describedby={errors.username ? 'username-error' : undefined}
          />
        </div>
        {errors.username && (
          <span id="username-error" className="text-xs text-destructive">{errors.username.message}</span>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="password" className="text-sm font-medium">密码</label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            id="password"
            className="pl-9"
            type="password"
            placeholder="密码"
            autoComplete="current-password"
            {...register('password')}
            data-invalid={!!errors.password}
            aria-invalid={!!errors.password}
            aria-describedby={errors.password ? 'password-error' : undefined}
          />
        </div>
        {errors.password && (
          <span id="password-error" className="text-xs text-destructive">{errors.password.message}</span>
        )}
      </div>

      {submitError && <p role="alert" className="text-sm text-destructive">{submitError}</p>}

      <Button type="submit" className="w-full" disabled={loading}>
        {loading && <Loader2 className="size-4 animate-spin" data-icon="inline-start" />}
        {submitLabel}
      </Button>
    </form>
  )
}
