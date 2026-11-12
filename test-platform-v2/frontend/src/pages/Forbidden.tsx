import { Link } from 'react-router'
import { Shield } from '@/lib/icons'

/**
 * 403 页面（batch-336）：路由守卫命中但当前账号缺少菜单权限时展示。
 * 与后端 403（缺少权限：menu:*）同语义，避免用户看到空白页。
 */
export default function Forbidden() {
  return (
    <div className="grid min-h-[320px] place-items-center p-6" data-testid="forbidden-page">
      <div className="max-w-md space-y-3 text-center">
        <Shield className="mx-auto size-10 text-muted-foreground" />
        <h1 className="text-xl font-semibold">无访问权限</h1>
        <p className="text-sm text-muted-foreground">
          当前账号没有该页面的菜单权限，请联系管理员分配后重试。
        </p>
        <Link className="text-sm text-primary hover:underline" to="/workbench">
          返回工作台
        </Link>
      </div>
    </div>
  )
}
