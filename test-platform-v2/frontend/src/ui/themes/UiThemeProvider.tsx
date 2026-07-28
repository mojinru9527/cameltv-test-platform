/**
 * UI 主题兼容适配器
 *
 * 主题状态由 ThemeProvider 统一管理。此模块只保留旧消费者所需的
 * useUiTheme API，不再拥有独立状态、存储或 DOM 属性。
 */

import { type ReactNode } from 'react'
import { useTheme } from '@/components/theme-provider'
import type { ColorTheme } from '@/lib/themes'

export type UiThemeId = ColorTheme

export function UiThemeProvider({ children }: { children: ReactNode }) {
  return <>{children}</>
}

export function useUiTheme() {
  const { colorTheme, setColorTheme } = useTheme()

  return {
    uiTheme: colorTheme,
    setUiTheme: (theme: UiThemeId) => {
      setColorTheme(theme)
    },
  } satisfies {
    uiTheme: UiThemeId
    setUiTheme: (theme: UiThemeId) => void
  }
}
