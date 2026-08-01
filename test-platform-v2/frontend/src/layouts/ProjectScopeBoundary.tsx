import type { ReactNode } from 'react'

interface ProjectScopeBoundaryProps {
  projectId: number | null
  children: ReactNode
}

export function ProjectScopeBoundary({ projectId, children }: ProjectScopeBoundaryProps) {
  return (
    <div
      key={projectId ?? 'no-project'}
      className="contents"
      data-project-scope={projectId ?? 'none'}
    >
      {children}
    </div>
  )
}
