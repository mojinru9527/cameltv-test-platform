import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'

import { resetPassword } from '@/api/auth'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { AlertCircle, ArrowLeft, Eye, EyeOff, Loader2, Lock } from '@/lib/icons'
import { Button, Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle, Input } from '@/ui'

const resetSchema = z.object({
  password: z.string().min(6, '密码至少 6 位'),
  confirmation: z.string().min(6, '请再次输入密码'),
}).refine((values) => values.password === values.confirmation, {
  message: '两次输入的密码不一致',
  path: ['confirmation'],
})

type ResetValues = z.infer<typeof resetSchema>

export default function ResetPasswordPage() {
  useDocumentTitle('重置密码')
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')?.trim() || ''
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: { password: '', confirmation: '' },
  })

  const onSubmit = async (values: ResetValues) => {
    setLoading(true)
    setSubmitError('')
    try {
      await resetPassword(token, values.password)
      toast.success('密码已重置，请使用新密码登录')
      navigate('/login', { replace: true })
    } catch (reason) {
      setSubmitError(reason instanceof Error ? reason.message : '密码重置失败，请重新申请')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-background px-4 py-8">
        <Card className="w-full max-w-[420px] border border-border/60 shadow-lg">
          <CardHeader>
            <CardTitle role="heading" aria-level={1} className="text-2xl">链接无效</CardTitle>
            <CardDescription>重置链接缺少 token，请重新申请密码重置邮件。</CardDescription>
          </CardHeader>
          <CardFooter className="justify-center">
            <Button asChild variant="primary" className="min-h-11">
              <Link to="/forgot-password">重新申请</Link>
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-background px-4 py-8">
      <Card className="w-full max-w-[420px] border border-border/60 shadow-lg">
        <CardHeader>
          <CardTitle role="heading" aria-level={1} className="text-2xl">设置新密码</CardTitle>
          <CardDescription>重置链接只能使用一次，成功后请立即使用新密码登录。</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="reset-password" className="text-sm font-medium">新密码</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                <Input
                  id="reset-password"
                  className="pl-9 pr-12"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="至少 6 位"
                  {...register('password')}
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? 'reset-password-error' : undefined}
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
              {errors.password && (
                <span id="reset-password-error" className="text-xs text-destructive">{errors.password.message}</span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="reset-confirmation" className="text-sm font-medium">确认新密码</label>
              <Input
                id="reset-confirmation"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                placeholder="再次输入新密码"
                {...register('confirmation')}
                aria-invalid={!!errors.confirmation}
                aria-describedby={errors.confirmation ? 'reset-confirmation-error' : undefined}
              />
              {errors.confirmation && (
                <span id="reset-confirmation-error" className="text-xs text-destructive">{errors.confirmation.message}</span>
              )}
            </div>

            {submitError && (
              <div role="alert" className="flex gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <span>{submitError}</span>
              </div>
            )}

            <Button type="submit" variant="primary" size="lg" className="min-h-11 w-full" disabled={loading}>
              {loading && <Loader2 className="size-4 animate-spin" data-icon="inline-start" />}
              重置密码
            </Button>
          </form>
        </CardContent>
        <CardFooter className="justify-center">
          <Link to="/login" className="inline-flex min-h-11 items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            返回登录
          </Link>
        </CardFooter>
      </Card>
    </div>
  )
}
