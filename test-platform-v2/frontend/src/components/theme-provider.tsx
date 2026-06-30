import { createContext, useCallback, useContext, useEffect, useState } from "react"

export type ThemeMode = "light" | "dark" | "system"
export type ColorTheme = "blue" | "green" | "purple" | "orange" | "rose" | "cyan" | "amber" | "indigo"

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
  } catch {}
  return "system"
}

function getStoredColor(): ColorTheme {
  try {
    const v = localStorage.getItem(STORAGE_COLOR_KEY)
    if (["blue", "green", "purple", "orange", "rose", "cyan", "amber", "indigo"].includes(v ?? "")) return v as ColorTheme
  } catch {}
  return "blue"
}

function applyTheme(mode: ThemeMode, colorTheme: ColorTheme) {
  const root = document.documentElement
  root.classList.remove("light", "dark")

  const resolved =
    mode === "system"
      ? window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : mode

  root.classList.add(resolved)
  root.dataset.theme = colorTheme
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(getStoredMode)
  const [colorTheme, setColorThemeState] = useState<ColorTheme>(getStoredColor)

  const setMode = useCallback((m: ThemeMode) => {
    setModeState(m)
    try { localStorage.setItem(STORAGE_MODE_KEY, m) } catch {}
  }, [])

  const setColorTheme = useCallback((c: ColorTheme) => {
    setColorThemeState(c)
    try { localStorage.setItem(STORAGE_COLOR_KEY, c) } catch {}
  }, [])

  // Apply theme on change
  useEffect(() => {
    applyTheme(mode, colorTheme)
  }, [mode, colorTheme])

  // Listen for system theme changes
  useEffect(() => {
    if (mode !== "system") return
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => applyTheme("system", colorTheme)
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
