/**
 * UI 主题兼容适配器
 *
 * 主题状态由 ThemeProvider 统一管理。此模块只保留旧消费者所需的
 * useUiTheme API，不再拥有独立状态、存储或 DOM 属性。
 */

import { type ReactNode } from 'react'
import { useTheme } from '@/components/theme-provider'

export type UiThemeId = 'default' | 'obsidian-flow'

export function UiThemeProvider({ children }: { children: ReactNode }) {
  return <>{children}</>
}

export function useUiTheme() {
  const { colorTheme, setColorTheme } = useTheme()

  return {
    uiTheme: colorTheme === 'obsidian-flow' ? 'obsidian-flow' : 'default',
    setUiTheme: (theme: UiThemeId) => {
      setColorTheme(theme === 'obsidian-flow' ? 'obsidian-flow' : 'cyberpunk')
    },
  } satisfies {
    uiTheme: UiThemeId
    setUiTheme: (theme: UiThemeId) => void
  }
}
