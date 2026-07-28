import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeLab } from './ThemeLab'
import { ThemeProvider } from '@/components/theme-provider'
import './theme-lab.css'

ReactDOM.createRoot(document.getElementById('theme-lab-root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <ThemeLab />
    </ThemeProvider>
  </React.StrictMode>,
)
