import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ProjectAccessBoundary, { isProjectSetupPath } from '../ProjectAccessBoundary'

describe('项目访问边界', () => {
  it('无项目时不挂载项目域子页，避免子页发出缺少 Project ID 的请求', () => {
    const onMount = vi.fn()
    function BusinessPage() {
      onMount()
      return <div>业务页面</div>
    }

    render(
      <ProjectAccessBoundary
        projectId={null}
        pathname="/testcase"
        canCreateProject
        onOpenProjects={vi.fn()}
      >
        <BusinessPage />
      </ProjectAccessBoundary>,
    )

    expect(onMount).not.toHaveBeenCalled()
    expect(screen.queryByText('业务页面')).toBeNull()
    expect(screen.getByRole('heading', { name: '先创建一个项目' })).toBeTruthy()
  })

  it.each(['/my-projects', '/my-projects/1', '/organizations'])('%s 无项目也可进入起步页', (pathname) => {
    render(
      <ProjectAccessBoundary
        projectId={null}
        pathname={pathname}
        canCreateProject
        onOpenProjects={vi.fn()}
      >
        <div>起步页面</div>
      </ProjectAccessBoundary>,
    )

    expect(screen.getByText('起步页面')).toBeTruthy()
    expect(isProjectSetupPath(pathname)).toBe(true)
  })

  it('选择项目后恢复业务页', () => {
    render(
      <ProjectAccessBoundary
        projectId={7}
        pathname="/testcase"
        canCreateProject
        onOpenProjects={vi.fn()}
      >
        <div>业务页面</div>
      </ProjectAccessBoundary>,
    )

    expect(screen.getByText('业务页面')).toBeTruthy()
  })
})
