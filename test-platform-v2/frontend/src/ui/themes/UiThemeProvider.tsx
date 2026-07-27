/**
 * UI 主题 Provider — 管理全局设计系统切换
 *
 * 独立于颜色主题（cyberpunk/apple/clay/xlab/liquid-glass），
 * 控制是否启用"黑曜流界"设计系统。
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

export type UiThemeId = 'default' | 'obsidian-flow'

interface UiThemeContextValue {
  uiTheme: UiThemeId
  setUiTheme: (theme: UiThemeId) => void
}

const UiThemeContext = createContext<UiThemeContextValue>({
  uiTheme: 'default',
  setUiTheme: () => {},
})

const STORAGE_KEY = 'cameltv-ui-theme'

function getStoredUiTheme(): UiThemeId {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'obsidian-flow' || stored === 'default') return stored
  } catch {
    // localStorage 不可用时回退
  }
  // 新用户默认使用黑曜流界
  return 'obsidian-flow'
}

function applyUiTheme(theme: UiThemeId) {
  const root = document.documentElement
  if (theme === 'obsidian-flow') {
    root.setAttribute('data-ui-theme', 'obsidian-flow')
    root.classList.add('ui-obsidian-flow')
  } else {
    root.removeAttribute('data-ui-theme')
    root.classList.remove('ui-obsidian-flow')
  }
}

export function UiThemeProvider({ children }: { children: ReactNode }) {
  const [uiTheme, setUiThemeState] = useState<UiThemeId>(getStoredUiTheme)

  useEffect(() => {
    applyUiTheme(uiTheme)
    try {
      localStorage.setItem(STORAGE_KEY, uiTheme)
    } catch {
      // ignore
    }
  }, [uiTheme])

  const setUiTheme = (theme: UiThemeId) => {
    setUiThemeState(theme)
  }

  return (
    <UiThemeContext.Provider value={{ uiTheme, setUiTheme }}>
      {children}
    </UiThemeContext.Provider>
  )
}

export function useUiTheme() {
  return useContext(UiThemeContext)
}
