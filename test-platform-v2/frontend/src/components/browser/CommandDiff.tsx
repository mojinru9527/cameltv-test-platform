import { Badge } from '@/ui'
import { cn } from '@/lib/utils'
import { COMMAND_DRIVER_LABELS, type CommandIR, type CommandIRCommand } from '@/api/actionPlans'
import { formatValue, JsonBlock, isRecord } from './JsonView'

export interface CommandDiffProps {
  before: CommandIR | null
  after: CommandIR | null
}

function commandContent(cmd: CommandIRCommand): string {
  const { id: _id, ...rest } = cmd
  try {
    return JSON.stringify(rest)
  } catch {
    return String(rest)
  }
}

function commandsById(ir: CommandIR | null): Map<string, CommandIRCommand> {
  const map = new Map<string, CommandIRCommand>()
  if (ir) {
    for (const cmd of ir.commands ?? []) {
      if (cmd?.id) map.set(cmd.id, cmd)
    }
  }
  return map
}

export function collectOracleKeys(ir: CommandIR | null): string[] {
  const keys = new Set<string>()
  for (const cmd of ir?.commands ?? []) {
    if (cmd.driver === 'assertion' && isRecord(cmd.input)) {
      const oracleKey = cmd.input.oracle_key ?? cmd.input['oracle_key']
      if (typeof oracleKey === 'string') keys.add(oracleKey)
    }
  }
  return [...keys].sort()
}

function CommandContentView({ cmd }: { cmd: CommandIRCommand }) {
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground/80">
          {cmd.action}
        </span>
        {cmd.observation_ref && (
          <span className="font-mono text-[11px] text-muted-foreground">
            obs:{cmd.observation_ref}
          </span>
        )}
      </div>
      {cmd.input && (
        <div className="flex flex-wrap gap-1">
          {Object.entries(cmd.input).map(([k, v]) => (
            <span key={k} className="rounded border px-1.5 py-0.5 font-mono text-[11px]">
              <span className="text-muted-foreground">{k}=</span>
              {formatValue(v)}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

/** Add a tiny delta badge for a changed field/full command. */
function DeltaBadge({ kind }: { kind: 'added' | 'removed' | 'changed' }) {
  const label = kind === 'added' ? '新增' : kind === 'removed' ? '删除' : '变更'
  const tone = kind === 'added' ? 'success' : kind === 'removed' ? 'danger' : 'warning'
  return <Badge tone={tone}>{label}</Badge>
}

/**
 * Semantic diff of two Command IR revisions, keyed by command id.
 * Added commands are green, removed red, changed yellow; unchanged muted.
 * Never collapses important info — every command body is shown verbatim.
 */
export function CommandDiff({ before, after }: CommandDiffProps) {
  const beforeMap = commandsById(before)
  const afterMap = commandsById(after)
  const beforeKeys = collectOracleKeys(before)
  const afterKeys = collectOracleKeys(after)

  const ids: string[] = []
  const seen = new Set<string>()
  for (const id of afterMap.keys()) {
    ids.push(id)
    seen.add(id)
  }
  for (const id of beforeMap.keys()) {
    if (!seen.has(id)) ids.push(id)
  }

  const noData = !before && !after

  return (
    <div className="space-y-3">
      {before?.schema_version && after?.schema_version && before.schema_version !== after.schema_version && (
        <div className="rounded-md border bg-muted/50 px-3 py-1.5 text-xs text-muted-foreground">
          schema_version: <span className="font-mono">{before.schema_version}</span> →{' '}
          <span className="font-mono">{after.schema_version}</span>
        </div>
      )}

      {noData ? (
        <div className="rounded-md border border-dashed px-3 py-3 text-center text-xs text-muted-foreground">
          暂无对比数据，请选择基准与候选版本。
        </div>
      ) : ids.length === 0 ? (
        <div className="rounded-md border border-dashed px-3 py-3 text-center text-xs text-muted-foreground">
          两个版本均无命令。
        </div>
      ) : (
        <ol className="space-y-2">
          {ids.map((id) => {
            const prev = beforeMap.get(id)
            const next = afterMap.get(id)
            const kind = !prev ? 'added' : !next ? 'removed' : commandContent(prev) !== commandContent(next) ? 'changed' : 'same'
            return (
              <li
                key={id}
                className={cn(
                  'rounded-md border px-3 py-2',
                  kind === 'added' && 'border-status-success/40 bg-status-success-muted/30',
                  kind === 'removed' && 'border-status-danger/40 bg-status-danger-muted/30',
                  kind === 'changed' && 'border-status-warning/40 bg-status-warning-muted/30',
                  kind === 'same' && 'border-border',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-muted-foreground">{id}</span>
                    <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
                      {COMMAND_DRIVER_LABELS[prev?.driver ?? next?.driver ?? ''] ?? (prev?.driver ?? next?.driver)}
                    </span>
                    {kind !== 'same' && <DeltaBadge kind={kind} />}
                  </div>
                </div>

                {kind === 'changed' && prev && next ? (
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div className="space-y-1">
                      <p className="text-[11px] text-muted-foreground">基准</p>
                      <CommandContentView cmd={prev} />
                    </div>
                    <div className="space-y-1">
                      <p className="text-[11px] text-muted-foreground">候选</p>
                      <CommandContentView cmd={next} />
                    </div>
                  </div>
                ) : (
                  <div className="mt-2">
                    <CommandContentView cmd={next ?? prev!} />
                  </div>
                )}
              </li>
            )
          })}
        </ol>
      )}

      <div className="space-y-2">
        {(!noData) && (
          <>
            {beforeKeys.length > 0 || afterKeys.length > 0 ? (
              <JsonBlock
                label="断言 Oracle Key 集合"
                data={{
                  基准: beforeKeys.length ? beforeKeys.join(', ') : '（无）',
                  候选: afterKeys.length ? afterKeys.join(', ') : '（无）',
                }}
              />
            ) : (
              <p className="text-xs text-muted-foreground">两个版本均未包含 assertion 命令，未检测到 Oracle Key。</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
