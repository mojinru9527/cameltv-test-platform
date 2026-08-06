import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { register as registerApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { Button, Input } from '@/ui'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { User, Lock, Send, KeyRound, Loader2 } from '@/lib/icons'

const registerSchema = z
  .object({
    username: z.string().min(2, '用户名至少 2 位'),
    nickname: z.string().optional(),
    email: z.string().email('邮箱格式不正确').or(z.literal('')).optional(),
    password: z.string().min(6, '密码至少 6 位'),
    confirmation: z.string().min(6, '请再次输入密码'),
    invite_code: z.string().min(1, '请输入邀请码'),
  })
  .refine((data) => data.password === data.confirmation, {
    message: '两次输入的密码不一致',
    path: ['confirmation'],
  })

type RegisterForm = z.infer<typeof registerSchema>

export default function RegisterPage() {
  const navigate = useNavigate()
  const location = useLocation()
  useDocumentTitle('注册')
  const setLogin = useAuthStore((s) => s.setLogin)
  const [loading, setLoading] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const inviteParam = new URLSearchParams(location.search).get('invite') || ''

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: '',
      nickname: '',
      email: '',
      password: '',
      confirmation: '',
      invite_code: '',
    },
  })

  const onFinish = async (values: RegisterForm) => {
    setLoading(true)
    setSubmitError('')
    try {
      const data = await registerApi({
        username: values.username,
        nickname: values.nickname || '',
        email: values.email || '',
        password: values.password,
        invite_code: values.invite_code,
        project_invite_token: inviteParam,
      })
      setLogin(data)
      toast.success('注册成功，欢迎使用 CamelTv 测试平台')
      navigate('/my-projects', { replace: true })
    } catch (reason) {
      setSubmitError(reason instanceof Error ? reason.message : '注册失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-background px-4 py-8">
      <Card className="w-full max-w-[400px] border border-border/60 shadow-lg">
        <CardHeader className="text-center">
          <CardTitle role="heading" aria-level={1} className="text-2xl">
            注册 CamelTv 测试平台
          </CardTitle>
          <CardDescription>凭管理员发放的邀请码创建账号</CardDescription>
        </CardHeader>
        <CardContent>
          {inviteParam && (
            <p className="mb-4 rounded-lg border border-border/60 bg-muted/40 p-3 text-sm text-muted-foreground">
              你正被邀请加入一个项目，注册完成后将自动加入。
            </p>
          )}
          {submitError && (
            <p
              role="alert"
              className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
            >
              {submitError}
            </p>
          )}
          <form onSubmit={handleSubmit(onFinish)} className="flex flex-col gap-4" noValidate>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="username" className="text-sm font-medium">用户名</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="username"
                  className="pl-9"
                  placeholder="登录用户名"
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
              <label htmlFor="nickname" className="text-sm font-medium">昵称</label>
              <Input
                id="nickname"
                placeholder="团队中显示的名字（可选）"
                {...register('nickname')}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-sm font-medium">邮箱</label>
              <div className="relative">
                <Send className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  className="pl-9"
                  placeholder="同事邀请你时使用的邮箱（可选）"
                  autoComplete="email"
                  {...register('email')}
                  data-invalid={!!errors.email}
                  aria-invalid={!!errors.email}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                />
              </div>
              {errors.email && (
                <span id="email-error" className="text-xs text-destructive">{errors.email.message}</span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="password" className="text-sm font-medium">密码</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  className="pl-9"
                  placeholder="至少 6 位"
                  autoComplete="new-password"
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

            <div className="flex flex-col gap-1.5">
              <label htmlFor="confirmation" className="text-sm font-medium">确认密码</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="confirmation"
                  type="password"
                  className="pl-9"
                  placeholder="再次输入密码"
                  autoComplete="new-password"
                  {...register('confirmation')}
                  data-invalid={!!errors.confirmation}
                  aria-invalid={!!errors.confirmation}
                  aria-describedby={errors.confirmation ? 'confirmation-error' : undefined}
                />
              </div>
              {errors.confirmation && (
                <span id="confirmation-error" className="text-xs text-destructive">{errors.confirmation.message}</span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="invite-code" className="text-sm font-medium">邀请码</label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="invite-code"
                  className="pl-9 uppercase"
                  placeholder="管理员发放的邀请码"
                  {...register('invite_code')}
                  data-invalid={!!errors.invite_code}
                  aria-invalid={!!errors.invite_code}
                  aria-describedby={errors.invite_code ? 'invite-code-error' : undefined}
                />
              </div>
              {errors.invite_code && (
                <span id="invite-code-error" className="text-xs text-destructive">{errors.invite_code.message}</span>
              )}
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="size-4 animate-spin" data-icon="inline-start" />}
              注册并登录
            </Button>
          </form>
        </CardContent>
        <CardFooter className="justify-center">
          <p className="text-xs text-muted-foreground">
            已有账号？
            <Link to="/login" className="ml-1 text-primary hover:underline">
              去登录
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
