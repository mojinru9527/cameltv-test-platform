import { useState } from 'react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/ui'
import { Button } from '@/ui'
import { toast } from 'sonner'
import { clearLanhuCookie, lanhuRelogin, updateLanhuCookie } from '@/api/lanhuEvidence'

type Mode = 'cookie' | 'login'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved?: () => void
}

export default function LanhuReloginDialog({ open, onOpenChange, onSaved }: Props) {
  const [mode, setMode] = useState<Mode>('cookie')
  const [cookie, setCookie] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  const handleSaveCookie = async () => {
    if (!cookie.trim()) {
      toast.error('请粘贴蓝湖 Cookie（浏览器 DevTools → Application → Cookies → 复制 lanhuapp.com 的 Cookie）')
      return
    }
    setBusy(true)
    try {
      await updateLanhuCookie(cookie.trim())
      toast.success('蓝湖 Cookie 已保存，重新提交蓝湖链接即可采集')
      setCookie('')
      onOpenChange(false)
      onSaved?.()
    } catch (e: any) {
      toast.error(e?.message || '保存 Cookie 失败')
    } finally {
      setBusy(false)
    }
  }

  const handleClearCookie = async () => {
    setBusy(true)
    try {
      await clearLanhuCookie()
      toast.success('已清除蓝湖 Cookie')
      onOpenChange(false)
      onSaved?.()
    } catch (e: any) {
      toast.error(e?.message || '清除失败')
    } finally {
      setBusy(false)
    }
  }

  const handleLogin = async () => {
    if (!username.trim() || !password) {
      toast.error('请填写蓝湖账号与密码')
      return
    }
    setBusy(true)
    try {
      const result = await lanhuRelogin(username.trim(), password)
      if (result.ok) {
        toast.success(result.message || '登录成功，Cookie 已保存')
        setPassword('')
        onOpenChange(false)
        onSaved?.()
      } else {
        toast.error(result.message || '自动登录失败')
      }
    } catch (e: any) {
      toast.error(e?.message || '自动登录失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent size="sm">
        <AlertDialogHeader>
          <AlertDialogTitle>蓝湖会话已失效 — 重新登录 / 更新 Cookie</AlertDialogTitle>
          <AlertDialogDescription>
            蓝湖接口返回 HTTP 418 表示会话过期或被拒。更新 Cookie 后重新提交蓝湖链接即可自动重试。
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="flex gap-2">
          <Button type="button" size="sm" variant={mode === 'cookie' ? 'primary' : 'secondary'} onClick={() => setMode('cookie')}>
            粘贴 Cookie
          </Button>
          <Button type="button" size="sm" variant={mode === 'login' ? 'primary' : 'secondary'} onClick={() => setMode('login')}>
            账号密码登录
          </Button>
        </div>

        {mode === 'cookie' ? (
          <Textarea
            placeholder="粘贴蓝湖 Cookie（形如 xxx=yyy; lanhu_session=zzz）"
            value={cookie}
            onChange={(e) => setCookie(e.target.value)}
            rows={4}
          />
        ) : (
          <div className="space-y-2">
            <Input placeholder="蓝湖账号" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" />
            <Input
              type="password"
              placeholder="蓝湖密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="off"
            />
            <p className="text-xs text-muted-foreground">
              密码仅用于本次换取 Cookie，不落库；若蓝湖有验证码，自动登录可能失败，请改用粘贴 Cookie。
            </p>
          </div>
        )}

        <AlertDialogFooter>
          {mode === 'cookie' && (
            <AlertDialogCancel disabled={busy} onClick={handleClearCookie}>清除 Cookie</AlertDialogCancel>
          )}
          <AlertDialogCancel disabled={busy}>取消</AlertDialogCancel>
          <AlertDialogAction
            disabled={busy}
            onClick={(event) => {
              event.preventDefault()
              if (mode === 'cookie') void handleSaveCookie()
              else void handleLogin()
            }}
          >
            {busy ? '处理中…' : mode === 'cookie' ? '保存 Cookie' : '登录并保存'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
