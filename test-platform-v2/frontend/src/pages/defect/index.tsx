import { useState } from 'react'
import { useAuthStore } from '@/stores/auth'
import { fetchDefectStats, fetchDefects } from '@/api/defect'
import type { DefectItem } from '@/types'
import PageHeader from '@/components/PageHeader'
import useApi from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import DefectStatsCards from './DefectStatsCards'
import DefectFilterBar from './DefectFilterBar'
import DefectTable from './DefectTable'
import DefectFormDialog from './DefectFormDialog'
import DefectDetailSheet from './DefectDetailSheet'

export default function DefectPage() {
  useDocumentTitle('缺陷管理')
  const hasPerm = useAuthStore((s) => s.hasPerm)

  // ── Filters ──
  const [fSeverity, setFSeverity] = useState<string | undefined>()
  const [fStatus, setFStatus] = useState<string | undefined>()
  const [fKeyword, setFKeyword] = useState('')
  const [page, setPage] = useState(1)

  // ── List data ──
  const list = useApi<any>(
    () => {
      const params: any = { page, page_size: 20 }
      if (fSeverity) params.severity = fSeverity
      if (fStatus) params.status = fStatus
      if (fKeyword) params.keyword = fKeyword
      return fetchDefects(params)
    },
    [fSeverity, fStatus, fKeyword, page],
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

  // ── Derived helpers ──
  const refetchAll = () => { list.refetch(); refetchStats() }

  return (
    <div className="space-y-4">
      <PageHeader title="缺陷管理" />

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
          onClose={() => { setDetailOpen(false); setDetail(null) }}
          onTransitioned={(updated) => { setDetail(updated); refetchAll() }}
          onMutated={list.refetch}
          canSync={hasPerm('integration:sync')}
        />
      )}
    </div>
  )
}
