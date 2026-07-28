/**
 * useObsidianPage — 黑曜流界页面包装 Hook
 *
 * 为任何页面提供黑曜流界风格的页头包装，无需修改原有渲染逻辑。
 *
 * @example
 * ```tsx
 * export default function RequirementPage() {
 *   const { Page, pageProps } = useObsidianPage({
 *     title: '需求管理',
 *     description: '管理需求文档与版本基线',
 *   })
 *
 *   return (
 *     <Page>
 *       {/* 原有页面内容 *\/}
 *       <DataTable ... />
 *     </Page>
 *   )
 * }
 * ```
 */

import { type ReactNode } from 'react'
import { ObsidianListPage, type ObsidianListPageProps } from '../patterns/ObsidianListPage'
import { useUiTheme } from '../themes/UiThemeProvider'

interface UseObsidianPageOptions extends Omit<ObsidianListPageProps, 'children'> {
  /** 在非黑曜流界模式下的备选内容（如自定义 PageHeader） */
  fallback?: ReactNode
}

export function useObsidianPage(options: UseObsidianPageOptions) {
  const { uiTheme } = useUiTheme()
  const isObsidian = uiTheme === 'obsidian-flow'
  const { fallback, ...obsidianProps } = options

  return {
    isObsidian,
    Page: isObsidian
      ? ({ children }: { children: ReactNode }) => (
          <ObsidianListPage {...obsidianProps}>{children}</ObsidianListPage>
        )
      : ({ children }: { children: ReactNode }) => <>{fallback}{children}</>,
    pageProps: obsidianProps,
  }
}
