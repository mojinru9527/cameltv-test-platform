import type { PropsWithChildren } from 'react'

type FadeContentProps = PropsWithChildren<{
  transitionKey: string
  className?: string
}>

/**
 * A deliberately restrained React Bits-style transition for product UI.
 * It communicates a context change without delaying task completion.
 */
export function FadeContent({ transitionKey, className = '', children }: FadeContentProps) {
  return (
    <div key={transitionKey} className={`fade-content ${className}`.trim()}>
      {children}
    </div>
  )
}
