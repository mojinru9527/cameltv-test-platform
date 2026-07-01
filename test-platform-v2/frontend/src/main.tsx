import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'
import { ThemeProvider } from '@/components/theme-provider'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { router } from '@/router'
import './globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider>
        <TooltipProvider delayDuration={300}>
          <RouterProvider router={router} />
          <Toaster richColors closeButton />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
