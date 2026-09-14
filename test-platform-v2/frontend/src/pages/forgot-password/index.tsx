import { useState } from 'react'
import { Link } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { fetchPublicAccess, forgotPassword } from '@/api/auth'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { AlertCircle, ArrowLeft, Loader2, User } from '@/lib/icons'
import { Button, Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle, Input } from '@/ui'

const forgotSchema = z.object({
  username: z.string().trim().min(1, '请输入用户名'),
})

type ForgotValues = z.infer<typeof forgotSchema>

export default function ForgotPasswordPage() {
  useDocumentTitle('忘记密码')
  const [emailAvailable, setEmailAvailable] = useState<boolean | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [loading, setLoading] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotValues>({
    resolver: zodResolver(forgotSchema),
    defaultValues: { username: '' },
  })

  useAbortableEffect((signal) => {
    fetchPublicAccess(signal)
      .then((access) => {
        if (!signal.aborted) setEmailAvailable(Boolean(access.password_reset_email_enabled))
      })
      .catch(() => {
        if (!signal.aborted) setEmailAvailable(null)
      })
  }, [])

  const onSubmit = async (values: ForgotValues) => {
    setLoading(true)
    setSubmitError('')
    try {
      await forgotPassword(values.username)
      setSubmitted(true)
    } catch (reason) {
      setSubmitError(reason instanceof Error ? reason.message : '提交失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-background px-4 py-8">
      <Card className="w-full max-w-[420px] border border-border/60 shadow-lg">
        <CardHeader>
          <CardTitle role="heading" aria-level={1} className="text-2xl">找回密码</CardTitle>
          <CardDescription>
            输入用户名。若账号存在且绑定了邮箱，系统会发送 30 分钟内有效的一次性重置链接。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {emailAvailable === false && (
            <div role="status" className="flex gap-3 rounded-lg border border-status-warning/40 bg-status-warning-muted p-3 text-sm text-status-warning">
              <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <p>当前部署未配置完整邮件发送链路，请联系管理员重置密码或配置 SMTP 与前端访问地址。</p>
            </div>
          )}

          {submitted ? (
            <div role="status" className="space-y-3 rounded-lg border bg-muted/40 p-4">
              <p className="font-medium">请求已提交</p>
              <p className="text-sm leading-6 text-muted-foreground">
                {emailAvailable === false
                  ? '本次请求不会自动发送邮件，请联系管理员人工协助重置。'
                  : '如果用户名存在且账号已绑定邮箱，请检查收件箱和垃圾邮件目录。为避免泄露账号信息，此页面不会显示账号是否存在。'}
              </p>
              <Button asChild variant="secondary" className="min-h-11 w-full">
                <Link to="/login">返回登录</Link>
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="forgot-username" className="text-sm font-medium">用户名</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                  <Input
                    id="forgot-username"
                    className="pl-9"
                    placeholder="请输入用户名"
                    autoComplete="username"
                    autoFocus
                    {...register('username')}
                    aria-invalid={!!errors.username}
                    aria-describedby={errors.username ? 'forgot-username-error' : undefined}
                  />
                </div>
                {errors.username && (
                  <span id="forgot-username-error" className="text-xs text-destructive">{errors.username.message}</span>
                )}
              </div>

              {submitError && <p role="alert" className="text-sm text-destructive">{submitError}</p>}

              <Button type="submit" variant="primary" size="lg" className="min-h-11 w-full" disabled={loading}>
                {loading && <Loader2 className="size-4 animate-spin" data-icon="inline-start" />}
                发送重置链接
              </Button>
            </form>
          )}
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
