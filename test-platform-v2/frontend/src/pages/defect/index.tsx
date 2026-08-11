import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth'
import { fetchDefect, fetchDefectStats, fetchDefects } from '@/api/defect'
import type { DefectItem } from '@/types'
import useApi from '@/hooks/useApi'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { PageShell } from '@/ui'
import DefectStatsCards from './DefectStatsCards'
import DefectFilterBar from './DefectFilterBar'
import DefectTable from './DefectTable'
import DefectFormDialog from './DefectFormDialog'
import DefectDetailSheet from './DefectDetailSheet'

export default function DefectPage() {
  useDocumentTitle('缺陷管理')
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const navigate = useNavigate()
  const { id: routeDefectId } = useParams()

  // ── Filters ──
  const [fSeverity, setFSeverity] = useState<string | undefined>()
  const [fStatus, setFStatus] = useState<string | undefined>()
  const [fKeyword, setFKeyword] = useState('')
  const debouncedKeyword = useDebouncedValue(fKeyword, 300)
  const [page, setPage] = useState(1)

  // ── List data ──
  const list = useApi<any>(
    () => {
      const params: any = { page, page_size: 20 }
      if (fSeverity) params.severity = fSeverity
      if (fStatus) params.status = fStatus
      if (debouncedKeyword) params.keyword = debouncedKeyword
      return fetchDefects(params)
    },
    [fSeverity, fStatus, debouncedKeyword, page],
  )

  // ── Stats (non-critical, silent errors) ──
  const { data: statsData, refetch: refetchStats } = useApi<any>(
    () => fetchDefectStats(),
    { showErrorToast: false },
  )
  const stats = statsData || { total: 0, by_severity: {} as Record<string, number>, by_status: {} as Record<string, number> }

  // ── Form dialog ──
  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<DefectItem | null>(null)

  // ── Detail sheet ──
  const [detail, setDetail] = useState<DefectItem | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  useEffect(() => {
    const defectId = Number(routeDefectId)
    if (!Number.isInteger(defectId) || defectId <= 0) return

    let cancelled = false
    fetchDefect(defectId)
      .then((item) => {
        if (cancelled) return
        setDetail(item as unknown as DefectItem)
        setDetailOpen(true)
      })
      .catch((error: unknown) => {
        if (cancelled) return
        toast.error(error instanceof Error ? error.message : '缺陷详情加载失败')
        navigate('/defect', { replace: true })
      })
    return () => { cancelled = true }
  }, [navigate, routeDefectId])

  // ── Derived helpers ──
  const refetchAll = () => { list.refetch(); refetchStats() }

  return (
    <PageShell
      title="缺陷管理"
      description="追踪、归因和闭环所有质量缺陷，支持状态流转与证据关联。"
      glass
    >
      <div className="space-y-4">
      <DefectStatsCards stats={stats} />

      <DefectFilterBar
        severity={fSeverity}
        status={fStatus}
        keyword={fKeyword}
        onSeverityChange={(v) => { setFSeverity(v); setPage(1) }}
        onStatusChange={(v) => { setFStatus(v); setPage(1) }}
        onKeywordChange={(v) => { setFKeyword(v); setPage(1) }}
        onRefresh={list.refetch}
        canCreate={hasPerm('defect:create')}
        onCreate={() => { setEditing(null); setDrawer(true) }}
      />

      <DefectTable
        data={list.data}
        isLoading={list.isLoading}
        isError={list.isError}
        error={list.error}
        onRetry={list.refetch}
        page={page}
        onPageChange={setPage}
        onDetail={(r) => { setDetail(r); setDetailOpen(true) }}
        onEdit={(r) => { setEditing(r); setDrawer(true) }}
        onDeleted={refetchAll}
        canUpdate={hasPerm('defect:update')}
        canDelete={hasPerm('defect:delete')}
      />

      <DefectFormDialog
        open={drawer}
        editing={editing}
        onClose={() => { setDrawer(false); setEditing(null) }}
        onSaved={refetchAll}
      />

      {detail && (
        <DefectDetailSheet
          detail={detail}
          open={detailOpen}
          onClose={() => {
            setDetailOpen(false)
            setDetail(null)
            if (routeDefectId) navigate('/defect')
          }}
          onTransitioned={(updated) => { setDetail(updated); refetchAll() }}
          onMutated={list.refetch}
          canSync={hasPerm('integration:sync')}
        />
      )}
    </div>
    </PageShell>
  )
}
