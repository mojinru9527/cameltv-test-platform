/**
 * 备案号 footer（广东个人备案合规展示）。
 * 仅在构建前端镜像时通过 VITE_ICP_NUMBER 注入备案号才渲染，
 * 未配置时返回 null，不影响现有页面。
 * 展示的备案号链接到工信部备案管理系统（beian.miit.gov.cn）。
 * 注意：在组件内读取 env，便于单元测试用 vi.stubEnv 覆盖。
 */
export default function IcpFooter() {
  const icpNumber = (import.meta.env.VITE_ICP_NUMBER ?? '').trim()
  if (!icpNumber) {
    return null
  }
  return (
    <footer className="border-t bg-background px-4 py-3 text-center text-xs text-muted-foreground">
      <a
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noreferrer"
        className="transition-colors hover:text-foreground"
      >
        {icpNumber}
      </a>
    </footer>
  )
}
