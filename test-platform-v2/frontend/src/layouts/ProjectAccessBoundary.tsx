import type { ReactNode } from 'react'

import { ProjectScopeBoundary } from './ProjectScopeBoundary'
import ProjectRequiredState from './ProjectRequiredState'

const PROJECT_SETUP_PATHS = ['/my-projects'] as const

export function isProjectSetupPath(pathname: string): boolean {
  return PROJECT_SETUP_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  )
}

interface ProjectAccessBoundaryProps {
  projectId: number | null
  pathname: string
  canCreateProject: boolean
  onOpenProjects: () => void
  children: ReactNode
}

export default function ProjectAccessBoundary({
  projectId,
  pathname,
  canCreateProject,
  onOpenProjects,
  children,
}: ProjectAccessBoundaryProps) {
  if (projectId == null && !isProjectSetupPath(pathname)) {
    return (
      <ProjectRequiredState
        canCreateProject={canCreateProject}
        onOpenProjects={onOpenProjects}
      />
    )
  }

  return <ProjectScopeBoundary projectId={projectId}>{children}</ProjectScopeBoundary>
}
