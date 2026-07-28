import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'
import { ThemeProvider } from '@/components/theme-provider'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { UiThemeProvider } from '@/ui'
import { router } from '@/router'
import './globals.css'
import './theme-lab/theme-lab.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider>
        <UiThemeProvider>
          <TooltipProvider delayDuration={300}>
            <RouterProvider router={router} />
            <Toaster richColors closeButton />
          </TooltipProvider>
        </UiThemeProvider>
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
