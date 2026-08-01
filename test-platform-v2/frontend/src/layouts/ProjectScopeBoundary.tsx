import { Fragment, type ReactNode } from 'react'

interface ProjectScopeBoundaryProps {
  projectId: number | null
  children: ReactNode
}

export function ProjectScopeBoundary({ projectId, children }: ProjectScopeBoundaryProps) {
  return <Fragment key={projectId ?? 'no-project'}>{children}</Fragment>
}
