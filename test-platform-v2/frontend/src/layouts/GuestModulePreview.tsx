import { Link } from 'react-router'

import type { GuestModuleDefinition } from './guestModuleCatalog'
import { Button } from '@/ui'
import { ArrowLeft, ArrowRight, CheckCircle2, Lock } from '@/lib/icons'

interface GuestModulePreviewProps {
  module: GuestModuleDefinition
  path: string
  registrationEnabled: boolean
  onRequireLogin: (path: string, label: string) => void
}

export default function GuestModulePreview({
  module,
  path,
  registrationEnabled,
  onRequireLogin,
}: GuestModulePreviewProps) {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 py-2 sm:py-6">
      <Link
        to="/"
        className="inline-flex min-h-11 w-fit items-center gap-2 rounded-lg px-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        返回平台能力目录
      </Link>

      <section className="overflow-hidden rounded-2xl border border-border/70 bg-card p-6 shadow-sm sm:p-8">
        <div className="flex max-w-3xl flex-col gap-4">
          <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <CheckCircle2 className="size-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-medium text-primary">平台功能说明</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-[-0.03em] text-foreground">
              {module.title}
            </h1>
            <p className="mt-3 text-sm leading-6 text-muted-foreground sm:text-base">
              {module.description}
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              type="button"
              className="min-h-11"
              aria-label={`登录后使用${module.title}`}
              onClick={() => onRequireLogin(path, module.title)}
            >
              登录后使用
              <ArrowRight className="size-4" aria-hidden="true" />
            </Button>
            {registrationEnabled && (
              <Link
                to="/register"
                className="inline-flex min-h-11 items-center justify-center rounded-lg bg-secondary px-4 text-sm font-medium text-secondary-foreground transition-colors hover:bg-secondary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                免费注册
              </Link>
            )}
          </div>
        </div>
      </section>

      <section aria-labelledby="guest-capability-heading">
        <h2 id="guest-capability-heading" className="text-xl font-semibold tracking-[-0.02em]">
          主要能力
        </h2>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {module.capabilities.map((capability) => (
            <article key={capability.title} className="min-h-[120px] rounded-xl border bg-card p-4">
              <h3 className="font-semibold text-foreground">{capability.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {capability.description}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="flex gap-3 rounded-xl border bg-muted/40 p-4" aria-label="登录与项目边界">
        <Lock className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
        <div>
          <h2 className="text-sm font-semibold">浏览公开，业务数据受保护</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            当前页面只展示模块能力。登录并选择项目后，平台才会读取项目数据；新建、执行、修改和导出仍按角色权限校验。
          </p>
        </div>
      </section>
    </div>
  )
}
