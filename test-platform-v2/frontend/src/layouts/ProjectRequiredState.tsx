import { Button } from '@/ui'
import { CheckCircle2, Circle, FolderOpen } from '@/lib/icons'

interface ProjectRequiredStateProps {
  canCreateProject: boolean
  onOpenProjects: () => void
}

const completedStep = {
  icon: CheckCircle2,
  title: '注册并登录',
  description: '账号已经可以正常使用。',
}

export default function ProjectRequiredState({
  canCreateProject,
  onOpenProjects,
}: ProjectRequiredStateProps) {
  const heading = canCreateProject ? '先创建一个项目' : '还没有可用项目'
  return (
    <section className="mx-auto flex min-h-[60vh] w-full max-w-2xl items-center py-6">
      <div className="w-full rounded-2xl border bg-card p-6 text-center shadow-sm sm:p-10">
        <div className="mx-auto flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <FolderOpen className="size-6" aria-hidden="true" />
        </div>
        <p className="mt-5 text-sm font-medium text-primary">开始使用测试平台</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-[-0.025em]">{heading}</h1>
        <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-muted-foreground">
          {canCreateProject
            ? '测试用例、计划、报告等数据都属于项目。创建第一个项目后即可进入各功能，不会再出现缺少项目 ID 的错误。'
            : '测试数据必须属于项目。请联系管理员将你加入一个项目，再进入平台功能。'}
        </p>

        <ol className="mx-auto mt-6 grid max-w-xl gap-3 text-left sm:grid-cols-3" aria-label="开始使用步骤">
          {[
            completedStep,
            {
              icon: canCreateProject ? FolderOpen : Circle,
              title: canCreateProject ? '创建项目' : '加入项目',
              description: canCreateProject ? '填写项目名称与编码。' : '等待管理员添加成员。',
            },
            { icon: Circle, title: '进入功能', description: '选择项目后开始测试工作。' },
          ].map((step, index) => {
            const Icon = step.icon
            return (
              <li key={step.title} className="rounded-xl border bg-muted/30 p-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Icon className="size-4 text-primary" aria-hidden="true" />
                  <span>{index + 1}. {step.title}</span>
                </div>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">{step.description}</p>
              </li>
            )
          })}
        </ol>

        <Button type="button" className="mt-6 min-h-11" onClick={onOpenProjects}>
          {canCreateProject ? '创建第一个项目' : '查看我的项目'}
        </Button>
      </div>
    </section>
  )
}
