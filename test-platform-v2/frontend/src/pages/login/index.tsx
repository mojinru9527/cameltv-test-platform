import { Link, useLocation, useNavigate } from 'react-router'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import LoginForm from '@/components/auth/LoginForm'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  useDocumentTitle('登录')
  const onSuccess = () => {
    const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'
    navigate(from, { replace: true })
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-background px-4 py-8">
      <Card className="w-full max-w-[380px] border border-border/60 shadow-lg">
        <CardHeader className="text-center">
          <CardTitle role="heading" aria-level={1} className="text-2xl">
            测试平台
          </CardTitle>
          <CardDescription>前后端分离 · 多项目测试管理</CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm onSuccess={onSuccess} />
        </CardContent>
        <CardFooter className="justify-center">
          <div className="flex flex-col items-center gap-1">
            <p className="text-xs text-muted-foreground">
              还没有账号？
              <Link to="/register" className="ml-1 text-primary hover:underline">
                免费注册
              </Link>
            </p>
            <Link to="/" className="text-xs text-muted-foreground hover:text-foreground">
              先浏览平台模块
            </Link>
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
