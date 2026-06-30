import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { User, Lock, Loader2 } from '@/lib/icons'

const loginSchema = z.object({
  username: z.string().min(1, '请输入用户名'),
  password: z.string().min(1, '请输入密码'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const setLogin = useAuthStore((s) => s.setLogin)
  const [loading, setLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: 'admin', password: 'admin123' },
  })

  const onFinish = async (values: LoginForm) => {
    setLoading(true)
    try {
      const data = await login(values.username, values.password)
      setLogin(data)
      toast.success('登录成功')
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'
      navigate(from, { replace: true })
    } catch {
      // 错误已由拦截器提示
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-gradient-to-br from-blue-800 to-blue-600">
      <Card className="w-[380px] shadow-2xl">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">CamelTv 测试平台</CardTitle>
          <CardDescription>前后端分离 · 多项目测试管理</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onFinish)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  placeholder="用户名"
                  {...register('username')}
                  data-invalid={!!errors.username}
                  aria-invalid={!!errors.username}
                />
              </div>
              {errors.username && (
                <span className="text-xs text-destructive">{errors.username.message}</span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  type="password"
                  placeholder="密码"
                  {...register('password')}
                  data-invalid={!!errors.password}
                  aria-invalid={!!errors.password}
                />
              </div>
              {errors.password && (
                <span className="text-xs text-destructive">{errors.password.message}</span>
              )}
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="size-4 animate-spin" data-icon="inline-start" />}
              登录
            </Button>
          </form>
        </CardContent>
        <CardFooter className="justify-center">
          <p className="text-xs text-muted-foreground">默认账号：admin / admin123</p>
        </CardFooter>
      </Card>
    </div>
  )
}
