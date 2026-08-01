import { useEffect, useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ProjectScopeBoundary } from '../ProjectScopeBoundary'

function ProjectPage({ onMount }: { onMount: () => void }) {
  const [draft, setDraft] = useState('')

  useEffect(() => {
    onMount()
  }, [onMount])

  return (
    <input
      aria-label="项目草稿"
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
    />
  )
}

describe('ProjectScopeBoundary', () => {
  it('remounts project-scoped content and clears local state after a project switch', () => {
    const onMount = vi.fn()
    const { rerender } = render(
      <ProjectScopeBoundary projectId={1}>
        <ProjectPage onMount={onMount} />
      </ProjectScopeBoundary>,
    )

    fireEvent.change(screen.getByLabelText('项目草稿'), { target: { value: '项目 A 数据' } })
    expect(screen.getByLabelText('项目草稿')).toHaveProperty('value', '项目 A 数据')

    rerender(
      <ProjectScopeBoundary projectId={2}>
        <ProjectPage onMount={onMount} />
      </ProjectScopeBoundary>,
    )

    expect(screen.getByLabelText('项目草稿')).toHaveProperty('value', '')
    expect(onMount).toHaveBeenCalledTimes(2)
  })
})
