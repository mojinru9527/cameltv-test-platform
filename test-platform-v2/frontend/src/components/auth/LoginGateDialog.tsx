import { Link } from 'react-router'

import LoginForm from './LoginForm'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface LoginGateDialogProps {
  open: boolean
  destinationLabel: string
  registrationEnabled: boolean
  onOpenChange: (open: boolean) => void
  onLoginSuccess: () => void
}

export default function LoginGateDialog({
  open,
  destinationLabel,
  registrationEnabled,
  onOpenChange,
  onLoginSuccess,
}: LoginGateDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[420px]">
        <DialogHeader>
          <DialogTitle>登录后使用{destinationLabel}</DialogTitle>
          <DialogDescription>
            平台模块可公开浏览，项目数据与具体操作需要登录后访问。
          </DialogDescription>
        </DialogHeader>
        <LoginForm onSuccess={onLoginSuccess} submitLabel={`登录并打开${destinationLabel}`} />
        {registrationEnabled && (
          <DialogFooter className="sm:justify-center">
            <p className="text-center text-xs text-muted-foreground">
              还没有账号？
              <Link to="/register" className="ml-1 font-medium text-primary hover:underline">
                免费注册
              </Link>
            </p>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
