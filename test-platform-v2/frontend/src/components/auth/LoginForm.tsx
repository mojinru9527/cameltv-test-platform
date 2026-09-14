import { useState, type KeyboardEvent } from 'react'
import { Link } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'

import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { Button, Input } from '@/ui'
import { AlertCircle, Eye, EyeOff, Loader2, Lock, User } from '@/lib/icons'

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
  const [showPassword, setShowPassword] = useState(false)
  const [capsLockOn, setCapsLockOn] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  })
  const passwordRegistration = register('password')

  const syncCapsLock = (event: KeyboardEvent<HTMLInputElement>) => {
    setCapsLockOn(event.getModifierState?.('CapsLock') ?? false)
  }

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

  const passwordDescribedBy = [
    errors.password ? 'password-error' : '',
    capsLockOn ? 'caps-lock-hint' : '',
  ].filter(Boolean).join(' ') || undefined

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
            className="pl-9 pr-12"
            type={showPassword ? 'text' : 'password'}
            placeholder="密码"
            autoComplete="current-password"
            {...passwordRegistration}
            onKeyDown={syncCapsLock}
            onKeyUp={syncCapsLock}
            onBlur={(event) => {
              passwordRegistration.onBlur(event)
              setCapsLockOn(false)
            }}
            data-invalid={!!errors.password}
            aria-invalid={!!errors.password}
            aria-describedby={passwordDescribedBy}
          />
          <button
            type="button"
            className="absolute right-1 top-1/2 flex size-11 -translate-y-1/2 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={showPassword ? '隐藏密码' : '显示密码'}
            aria-pressed={showPassword}
            onClick={() => setShowPassword((visible) => !visible)}
          >
            {showPassword ? <EyeOff className="size-4" aria-hidden="true" /> : <Eye className="size-4" aria-hidden="true" />}
          </button>
        </div>
        {capsLockOn && (
          <span id="caps-lock-hint" role="status" className="flex items-center gap-1.5 text-xs text-status-warning">
            <AlertCircle className="size-3.5" aria-hidden="true" />
            Caps Lock 已开启，密码可能为大写
          </span>
        )}
        {errors.password && (
          <span id="password-error" className="text-xs text-destructive">{errors.password.message}</span>
        )}
      </div>

      {submitError && <p role="alert" className="text-sm text-destructive">{submitError}</p>}

      <Button type="submit" variant="primary" size="lg" className="w-full" disabled={loading}>
        {loading && <Loader2 className="size-4 animate-spin" data-icon="inline-start" />}
        {submitLabel}
      </Button>

      <div className="text-center">
        <Link to="/forgot-password" className="text-xs font-medium text-primary hover:underline">
          忘记密码？
        </Link>
      </div>
    </form>
  )
}
