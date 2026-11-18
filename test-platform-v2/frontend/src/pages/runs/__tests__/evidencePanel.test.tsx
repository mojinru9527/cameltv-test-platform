import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  fetchArtifactBlob: vi.fn(),
}))

vi.mock('@/api/aiqeArtifacts', () => ({
  fetchArtifactBlob: api.fetchArtifactBlob,
}))

const { default: EvidencePanel, viewerKind } = await import('@/pages/runs/EvidencePanel')

const artifact = (overrides: Record<string, unknown> = {}) => ({
  id: 'a-1',
  artifact_type: 'SCREENSHOT',
  sha256: 'a'.repeat(64),
  size_bytes: 1234,
  mime_type: 'image/png',
  redaction_status: 'sanitized',
  created_at: new Date().toISOString(),
  upload_status: 'AVAILABLE',
  ...overrides,
})

describe('EvidencePanel', () => {
  beforeEach(() => {
    api.fetchArtifactBlob.mockReset()
    URL.createObjectURL = vi.fn(() => 'blob:mock')
    URL.revokeObjectURL = vi.fn()
  })

  it('maps artifact types to the right viewer', () => {
    expect(viewerKind('SCREENSHOT')).toBe('image')
    expect(viewerKind('VIDEO')).toBe('video')
    expect(viewerKind('HAR')).toBe('har')
    expect(viewerKind('DOM_SNAPSHOT')).toBe('json')
    expect(viewerKind('CONSOLE_LOG')).toBe('text')
    expect(viewerKind('PLAYWRIGHT_TRACE')).toBe('download')
    expect(viewerKind('UNKNOWN_TYPE')).toBe('download')
  })

  it('renders upload status and opens an image viewer', async () => {
    api.fetchArtifactBlob.mockResolvedValue(new Blob(['png'], { type: 'image/png' }))
    render(<EvidencePanel runId="run-1" artifacts={[artifact() as never]} />)

    expect(screen.getByText('证据（1）')).toBeTruthy()
    expect(screen.getByText('可用')).toBeTruthy()

    fireEvent.click(screen.getByText('查看'))
    await waitFor(() => expect(screen.getByTestId('evidence-viewer')).toBeTruthy())
    const image = screen.getByAltText('证据 SCREENSHOT') as HTMLImageElement
    expect(image.getAttribute('src')).toBe('blob:mock')
    expect(api.fetchArtifactBlob).toHaveBeenCalledWith('a-1')
  })

  it('renders HAR request rows', async () => {
    const har = {
      log: {
        entries: [
          { request: { method: 'GET', url: 'https://api.test/matches' }, response: { status: 200 } },
        ],
      },
    }
    api.fetchArtifactBlob.mockResolvedValue(
      new Blob([JSON.stringify(har)], { type: 'application/json' }),
    )
    render(<EvidencePanel runId="run-1" artifacts={[artifact({ artifact_type: 'HAR' }) as never]} />)
    fireEvent.click(screen.getByText('查看'))
    await waitFor(() => expect(screen.getByText('https://api.test/matches')).toBeTruthy())
    expect(screen.getByText('GET')).toBeTruthy()
  })

  it('renders log text truncated into pre', async () => {
    api.fetchArtifactBlob.mockResolvedValue(new Blob(['line-1\nline-2'], { type: 'text/plain' }))
    render(
      <EvidencePanel
        runId="run-1"
        artifacts={[artifact({ artifact_type: 'CONSOLE_LOG' }) as never]}
      />,
    )
    fireEvent.click(screen.getByText('查看'))
    await waitFor(() => expect(screen.getByText(/line-1/)).toBeTruthy())
  })

  it('shows an inline error when loading fails', async () => {
    api.fetchArtifactBlob.mockRejectedValue(new Error('artifact 上传未完成'))
    render(<EvidencePanel runId="run-1" artifacts={[artifact() as never]} />)
    fireEvent.click(screen.getByText('查看'))
    await waitFor(() => expect(screen.getByText('artifact 上传未完成')).toBeTruthy())
  })

  it('marks pending upload artifacts without opening a viewer', () => {
    render(
      <EvidencePanel
        runId="run-1"
        artifacts={[artifact({ upload_status: 'PENDING_UPLOAD' }) as never]}
      />,
    )
    expect(screen.getByText('上传中')).toBeTruthy()
    expect(screen.queryByTestId('evidence-viewer')).toBeNull()
  })
})
