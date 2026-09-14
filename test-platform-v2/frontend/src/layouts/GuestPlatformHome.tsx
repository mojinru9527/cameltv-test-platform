import { useState } from 'react'
import { Link } from 'react-router'

import type { MenuItem } from '@/types'
import { Button } from '@/ui'
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  ChevronDown,
  Code2,
  FileText,
  Lock,
  Monitor,
  TestTube2,
} from '@/lib/icons'

interface GuestPlatformHomeProps {
  modules: MenuItem[]
  registrationEnabled: boolean
  onNavigate: (path: string) => void
  onRequireLogin: (path: string, label: string) => void
}

const TASK_ENTRIES = [
  {
    title: '开始需求测试',
    description: '从需求文档、功能点和评审开始组织测试。',
    path: '/requirement',
    icon: FileText,
  },
  {
    title: '做接口回归',
    description: '导入契约、维护接口用例并批量执行回归。',
    path: '/apitest',
    icon: Code2,
  },
  {
    title: '创建 UI 自动化',
    description: '编写浏览器自动化脚本并查看执行证据。',
    path: '/uitest',
    icon: Monitor,
  },
  {
    title: '查看测试报告',
    description: '汇总执行结果、缺陷和质量结论。',
    path: '/report',
    icon: BarChart3,
  },
] as const

function actionableItems(module: MenuItem): MenuItem[] {
  return module.children?.length ? module.children : [module]
}

export default function GuestPlatformHome({
  modules,
  registrationEnabled,
  onNavigate,
  onRequireLogin,
}: GuestPlatformHomeProps) {
  const [showModules, setShowModules] = useState(false)

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 py-4 sm:py-8">
      <section className="overflow-hidden rounded-2xl border border-border/70 bg-card p-6 shadow-sm sm:p-10">
        <div className="max-w-3xl">
          <div className="mb-5 flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <TestTube2 className="size-5" aria-hidden="true" />
          </div>
          <p className="text-sm font-medium text-primary">CamelTv 测试平台</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-foreground sm:text-4xl">
            从测试任务开始，而不是先找模块
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
            选择你现在要完成的任务。平台会在需要时引导登录，项目数据和执行操作始终受权限保护。
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button
              type="button"
              variant="primary"
              className="min-h-11"
              onClick={() => onRequireLogin('/workbench', '工作台')}
            >
              登录并开始工作
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

      <section aria-labelledby="guest-task-heading">
        <div className="mb-4">
          <p className="text-sm font-medium text-primary">常用任务</p>
          <h2 id="guest-task-heading" className="mt-1 text-xl font-semibold tracking-[-0.02em]">
            你要做什么？
          </h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {TASK_ENTRIES.map((task) => {
            const Icon = task.icon
            return (
              <button
                key={task.path}
                type="button"
                className="group flex min-h-36 flex-col rounded-xl border border-border/70 bg-card p-5 text-left shadow-sm transition-colors hover:border-primary/40 hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={`登录后${task.title}`}
                onClick={() => onRequireLogin(task.path, task.title)}
              >
                <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="size-5" aria-hidden="true" />
                </span>
                <span className="mt-4 font-semibold text-foreground">{task.title}</span>
                <span className="mt-1 text-sm leading-6 text-muted-foreground">{task.description}</span>
                <ArrowRight
                  className="mt-auto size-4 self-end text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary"
                  aria-hidden="true"
                />
              </button>
            )
          })}
        </div>
      </section>

      <section aria-labelledby="guest-module-heading">
        <div className="flex flex-col gap-3 rounded-xl border border-border/70 bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 id="guest-module-heading" className="text-base font-semibold">
              浏览全部模块
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              先了解完整能力目录；业务数据与操作仍需登录后访问。
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-1.5 text-xs text-muted-foreground sm:flex">
              <Lock className="size-3.5" aria-hidden="true" />
              受权限保护
            </span>
            <Button
              type="button"
              variant="secondary"
              className="min-h-11"
              aria-expanded={showModules}
              aria-controls="guest-module-catalog"
              onClick={() => setShowModules((visible) => !visible)}
            >
              <BookOpen className="size-4" data-icon="inline-start" aria-hidden="true" />
              {showModules ? '收起模块' : '展开模块'}
              <ChevronDown
                className={`size-4 transition-transform ${showModules ? 'rotate-180' : ''}`}
                aria-hidden="true"
              />
            </Button>
          </div>
        </div>

        {showModules && (
          <div id="guest-module-catalog" className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {modules.length === 0 ? (
              <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">
                暂无可浏览模块，请稍后重试或直接登录。
              </p>
            ) : (
              modules.map((module) => (
                <article key={module.code} className="rounded-xl border border-border/70 bg-card p-5 shadow-sm">
                  <h3 className="font-semibold text-foreground">{module.name}</h3>
                  <div className="mt-3 flex flex-col gap-1">
                    {actionableItems(module).map((item) => (
                      <button
                        key={item.code}
                        type="button"
                        className="flex min-h-11 items-center justify-between rounded-lg px-3 text-left text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        aria-label={`查看${item.name}功能`}
                        onClick={() => onNavigate(item.path || '/')}
                      >
                        <span>{item.name}</span>
                        <ArrowRight className="size-4" aria-hidden="true" />
                      </button>
                    ))}
                  </div>
                </article>
              ))
            )}
          </div>
        )}
      </section>
    </div>
  )
}
