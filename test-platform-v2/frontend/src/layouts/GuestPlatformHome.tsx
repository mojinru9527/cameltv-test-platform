import { Link } from 'react-router'

import type { MenuItem } from '@/types'
import { Button } from '@/ui'
import { ArrowRight, Lock, TestTube2 } from '@/lib/icons'

interface GuestPlatformHomeProps {
  modules: MenuItem[]
  registrationEnabled: boolean
  onRequireLogin: (path: string, label: string) => void
}

function actionableItems(module: MenuItem): MenuItem[] {
  return module.children?.length ? module.children : [module]
}

export default function GuestPlatformHome({
  modules,
  registrationEnabled,
  onRequireLogin,
}: GuestPlatformHomeProps) {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 py-4 sm:py-8">
      <section className="overflow-hidden rounded-2xl border border-border/70 bg-card p-6 shadow-sm sm:p-10">
        <div className="max-w-3xl">
          <div className="mb-5 flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <TestTube2 className="size-5" aria-hidden="true" />
          </div>
          <p className="text-sm font-medium text-primary">CamelTv 测试平台</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-foreground sm:text-4xl">
            先浏览平台，再登录开始工作
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
            未登录也可以查看平台提供的模块。打开具体功能时，我们会先请你登录；新用户可以直接注册并创建自己的项目。
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button type="button" onClick={() => onRequireLogin('/workbench', '工作台')}>
              登录并开始使用
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

      <section aria-labelledby="guest-module-heading">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-primary">平台能力</p>
            <h2 id="guest-module-heading" className="mt-1 text-xl font-semibold tracking-[-0.02em]">
              浏览全部模块
            </h2>
          </div>
          <div className="hidden items-center gap-1.5 text-xs text-muted-foreground sm:flex">
            <Lock className="size-3.5" aria-hidden="true" />
            业务数据登录后可见
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {modules.map((module) => (
            <article key={module.code} className="rounded-xl border border-border/70 bg-card p-5 shadow-sm">
              <h3 className="font-semibold text-foreground">{module.name}</h3>
              <div className="mt-3 flex flex-col gap-1">
                {actionableItems(module).map((item) => (
                  <button
                    key={item.code}
                    type="button"
                    className="flex min-h-11 items-center justify-between rounded-lg px-3 text-left text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    aria-label={`打开${item.name}，需要登录`}
                    onClick={() => onRequireLogin(item.path || '/', item.name)}
                  >
                    <span>{item.name}</span>
                    <ArrowRight className="size-4" aria-hidden="true" />
                  </button>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
