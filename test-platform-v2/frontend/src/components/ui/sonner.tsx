"use client"

import { useEffect, useState, type CSSProperties } from "react"
import { useTheme } from "@/components/theme-provider"
import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon, Loader2Icon } from "lucide-react"

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light"
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
}

const Toaster = ({ ...props }: ToasterProps) => {
  const { mode } = useTheme()
  const [systemTheme, setSystemTheme] = useState<"light" | "dark">(getSystemTheme)

  useEffect(() => {
    if (mode !== "system") return

    const media = window.matchMedia("(prefers-color-scheme: dark)")
    const updateSystemTheme = () => setSystemTheme(media.matches ? "dark" : "light")
    updateSystemTheme()
    media.addEventListener("change", updateSystemTheme)
    return () => media.removeEventListener("change", updateSystemTheme)
  }, [mode])

  const theme = mode === "system" ? systemTheme : mode

  return (
    <div aria-live="polite" aria-atomic="true" role="status">
      <Sonner
        theme={theme as ToasterProps["theme"]}
        className="toaster group"
        icons={{
        success: (
          <CircleCheckIcon className="size-4" aria-hidden="true" />
        ),
        info: (
          <InfoIcon className="size-4" aria-hidden="true" />
        ),
        warning: (
          <TriangleAlertIcon className="size-4" aria-hidden="true" />
        ),
        error: (
          <OctagonXIcon className="size-4" aria-hidden="true" />
        ),
        loading: (
          <Loader2Icon className="size-4 animate-spin" aria-hidden="true" />
        ),
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as CSSProperties
      }
      toastOptions={{
        classNames: {
          toast: "cn-toast",
        },
      }}
      {...props}
    />
    </div>
  )
}

export { Toaster }
