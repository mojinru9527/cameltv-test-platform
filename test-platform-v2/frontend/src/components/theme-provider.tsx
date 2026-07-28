import { createContext, useCallback, useContext, useEffect, useState } from "react"
import {
  type ColorTheme,
  DEFAULT_COLOR_THEME,
  getThemeCssPreset,
  getThemeDefinition,
  normalizeColorTheme,
} from "@/lib/themes"

export type ThemeMode = "light" | "dark" | "system"

interface ThemeContextValue {
  mode: ThemeMode
  colorTheme: ColorTheme
  setMode: (mode: ThemeMode) => void
  setColorTheme: (theme: ColorTheme) => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

const STORAGE_MODE_KEY = "cameltv-theme-mode"
const STORAGE_COLOR_KEY = "cameltv-theme-color"

function getStoredMode(): ThemeMode {
  try {
    const v = localStorage.getItem(STORAGE_MODE_KEY)
    if (v === "light" || v === "dark" || v === "system") return v
  } catch { /* localStorage unavailable */ }
  return "system"
}

function getStoredColor(): ColorTheme {
  try {
    const v = localStorage.getItem(STORAGE_COLOR_KEY)
    return normalizeColorTheme(v)
  } catch { /* localStorage unavailable */ }
  return DEFAULT_COLOR_THEME
}

function resolveSupportedMode(mode: ThemeMode, colorTheme: ColorTheme): ThemeMode {
  const theme = getThemeDefinition(colorTheme)
  if (theme.supportedModes.length === 1) return theme.preferredMode
  if (mode === "system") return mode
  return (theme.supportedModes as readonly string[]).includes(mode)
    ? mode
    : theme.preferredMode
}

function applyTheme(mode: ThemeMode, colorTheme: ColorTheme) {
  const root = document.documentElement
  root.classList.remove("light", "dark", "ui-obsidian-flow")

  const supportedMode = resolveSupportedMode(mode, colorTheme)
  const resolved =
    supportedMode === "system"
      ? window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : supportedMode

  root.classList.add(resolved)

  // CSS preset drives all [data-theme="..."] selectors in globals.css
  root.dataset.theme = getThemeCssPreset(colorTheme)
  // Track the logical theme ID for components that need it
  root.dataset.themeId = colorTheme
  if (colorTheme === "obsidian-flow") root.dataset.uiTheme = "obsidian-flow"
  else delete root.dataset.uiTheme

  // Detect reduced-transparency preference
  if (window.matchMedia("(prefers-reduced-transparency: reduce)").matches) {
    root.dataset.reducedTransparency = "true"
  } else {
    delete root.dataset.reducedTransparency
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [colorTheme, setColorThemeState] = useState<ColorTheme>(getStoredColor)
  const [mode, setModeState] = useState<ThemeMode>(() =>
    resolveSupportedMode(getStoredMode(), getStoredColor()),
  )

  const setMode = useCallback((m: ThemeMode) => {
    const nextMode = resolveSupportedMode(m, colorTheme)
    setModeState(nextMode)
    try { localStorage.setItem(STORAGE_MODE_KEY, nextMode) } catch { /* noop */ }
  }, [colorTheme])

  const setColorTheme = useCallback((c: ColorTheme) => {
    setColorThemeState(c)
    setModeState((currentMode) => {
      const nextMode = resolveSupportedMode(currentMode, c)
      if (nextMode !== currentMode) {
        try { localStorage.setItem(STORAGE_MODE_KEY, nextMode) } catch { /* noop */ }
      }
      return nextMode
    })
    try { localStorage.setItem(STORAGE_COLOR_KEY, c) } catch { /* noop */ }
  }, [])

  // Apply theme on change
  useEffect(() => {
    applyTheme(mode, colorTheme)
    try {
      localStorage.setItem(STORAGE_MODE_KEY, mode)
      localStorage.setItem(STORAGE_COLOR_KEY, colorTheme)
    } catch { /* localStorage unavailable */ }

    const root = document.documentElement
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      root.classList.remove("theme-transition")
      return
    }

    root.classList.add("theme-transition")
    const transitionTimer = window.setTimeout(() => {
      root.classList.remove("theme-transition")
    }, 250)

    return () => {
      window.clearTimeout(transitionTimer)
      root.classList.remove("theme-transition")
    }
  }, [mode, colorTheme])

  // Listen for system theme changes
  useEffect(() => {
    if (mode !== "system") return
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => applyTheme("system", colorTheme)
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [mode, colorTheme])

  // Listen for reduced-transparency preference changes
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-transparency: reduce)")
    const handler = () => applyTheme(mode, colorTheme)
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [mode, colorTheme])

  return (
    <ThemeContext.Provider value={{ mode, colorTheme, setMode, setColorTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider")
  return ctx
}
