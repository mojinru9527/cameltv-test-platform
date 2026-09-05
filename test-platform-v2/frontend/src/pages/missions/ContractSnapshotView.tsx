import DataTable, { type DataTableColumn } from '@/components/DataTable'
import { Badge, StatusBadge, type SeverityVariant } from '@/ui'
import {
  CONTRACT_RULE_KIND_LABEL,
  CONTRACT_SOURCE_TYPE_LABEL,
  type ContractRule,
  type ContractSnapshot,
} from '@/api/contract'

/**
 * 契约快照的可读渲染（DEF-20260905-001）。
 *
 * 此前后端不回传 snapshot，契约页只有一个版本号 + 状态徽标，用户无法判断
 * 「标准答案」里到底有什么；空壳契约因此不可自证。
 */

function toSeverity(value?: string | null): SeverityVariant {
  return value === 'P0' || value === 'P1' || value === 'P2' ? value : 'P3'
}

const RULE_COLUMNS: DataTableColumn<ContractRule>[] = [
  {
    key: 'title',
    header: '规则',
    width: '28%',
    render: (r) => (
      <div className="min-w-0">
        <p className="truncate text-sm font-medium" title={r.title ?? r.rule_key}>
          {r.title || r.rule_key}
        </p>
        <p className="truncate font-mono text-[11px] text-muted-foreground" title={r.rule_key}>
          {r.rule_key}
        </p>
      </div>
    ),
  },
  {
    key: 'kind',
    header: '类型',
    render: (r) => <Badge tone="neutral">{CONTRACT_RULE_KIND_LABEL[r.kind] ?? r.kind}</Badge>,
  },
  {
    key: 'risk_level',
    header: '风险',
    render: (r) => <StatusBadge variant={toSeverity(r.risk_level)} />,
  },
  {
    key: 'source_type',
    header: '来源',
    render: (r) => (
      <span className="text-xs text-muted-foreground">
        {CONTRACT_SOURCE_TYPE_LABEL[r.source_type ?? ''] ?? r.source_type ?? '—'}
      </span>
    ),
  },
  {
    key: 'statement',
    header: '陈述',
    className: 'hidden md:table-cell',
    headerClassName: 'hidden md:table-cell',
    render: (r) => <span className="text-sm">{r.statement || '—'}</span>,
  },
]

export function ContractSnapshotView({ snapshot }: { snapshot?: ContractSnapshot | null }) {
  if (!snapshot) {
    return (
      <p className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
        契约快照解析失败或为空，请重新生成。
      </p>
    )
  }

  if (snapshot.rules.length === 0) {
    return (
      <p className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
        快照无有效规则：请确认 Scope 已批准，或配置可用 AI 提供方后重新生成。
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <DataTable<ContractRule>
        columns={RULE_COLUMNS}
        data={snapshot.rules}
        rowKey={(r) => r.rule_key}
        loadingRows={0}
        ariaLabel="契约规则"
      />

      {snapshot.required_outcomes.length > 0 && (
        <div className="space-y-1">
          <h3 className="text-xs font-medium text-muted-foreground">必需产出</h3>
          {snapshot.required_outcomes.map((o) => (
            <div key={o.outcome_key} className="flex items-baseline gap-2 text-sm">
              <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
                {o.outcome_key}
              </span>
              <span>{o.statement || '—'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ContractSnapshotView
