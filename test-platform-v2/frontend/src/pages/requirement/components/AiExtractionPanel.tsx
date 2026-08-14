import { Badge } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { ChevronDown, ChevronRight } from '@/lib/icons'
import type { FeatureExtractionResult, TestModule } from '@/types'
import {
  ClientScopeBadges,
  SEVERITY_BADGE_CLASSES,
  SEVERITY_CONFIG,
  TYPE_LABELS,
  VersionMarkerBadge,
} from './AiDisplayParts'

interface Props {
  extractionModules: TestModule[]
  expandedModules: Set<string>
  selectedModules: Set<string>
  extractionResult: FeatureExtractionResult | null
  onToggleExpand: (id: string) => void
  onToggleSelect: (id: string) => void
}

export default function AiExtractionPanel({
  extractionModules,
  expandedModules,
  selectedModules,
  extractionResult,
  onToggleExpand,
  onToggleSelect,
}: Props) {
  return (
    <div className="flex-1 overflow-y-auto space-y-3 pr-1 max-h-[55vh]">
      {extractionModules.map((mod) => {
        const isExpanded = expandedModules.has(mod.id)
        const isSelected = selectedModules.has(mod.id)
        const fpCount = mod.function_points?.length || 0
        const issueCount =
          mod.function_points?.reduce((s, fp) => s + (fp.issues?.length || 0), 0) || 0

        return (
          <Card
            key={mod.id}
            className={`border transition-colors ${
              isSelected ? 'border-primary/40' : 'border-muted opacity-60'
            }`}
          >
            {/* Module header */}
            <div className="flex items-center gap-3 px-4 py-3">
              <Checkbox
                checked={isSelected}
                onCheckedChange={() => onToggleSelect(mod.id)}
              />
              <button
                className="flex-1 flex items-center gap-2 text-left hover:opacity-80"
                onClick={() => onToggleExpand(mod.id)}
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
                <Badge tone="neutral" className="font-mono text-xs">
                  {mod.id}
                </Badge>
                <span className="font-medium text-sm">{mod.name}</span>
                <Badge tone="neutral" className="text-xs">
                  {fpCount} 个功能点
                </Badge>
                {issueCount > 0 && (
                  <Badge
                    tone="neutral"
                    className="text-xs border-status-warning-border bg-status-warning-muted text-status-warning"
                  >
                    {issueCount} 个问题
                  </Badge>
                )}
              </button>
            </div>

            {/* Module description + function points */}
            {isExpanded && (
              <CardContent className="pb-3 pt-0">
                {mod.description && (
                  <p className="text-sm text-muted-foreground mb-3">{mod.description}</p>
                )}

                <div className="space-y-2">
                  {mod.function_points?.map((fp) => (
                    <div
                      key={fp.id}
                      className="border rounded-lg p-3 bg-muted/30"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Badge tone="neutral" className="font-mono text-xs">
                          {fp.id}
                        </Badge>
                        <span className="text-sm font-medium">{fp.title}</span>
                        <Badge tone="neutral" className="text-xs">
                          {TYPE_LABELS[fp.type] || fp.type}
                        </Badge>
                        <ClientScopeBadges clients={fp.client_scope} />
                        <VersionMarkerBadge
                          fp={fp as any}
                          diffStatus={extractionResult?.diff_summary ? 'update' : undefined}
                          baseVersion={extractionResult?.inherited_from_version}
                        />
                      </div>
                      {fp.description && (
                        <p className="text-xs text-muted-foreground mb-2">
                          {fp.description}
                        </p>
                      )}

                      {/* Issues */}
                      {fp.issues && fp.issues.length > 0 && (
                        <div className="space-y-1.5 mt-2">
                          {fp.issues.map((issue, i) => {
                            const sev = SEVERITY_CONFIG[issue.severity] || SEVERITY_CONFIG.low
                            return (
                              <div
                                key={i}
                                className="rounded border p-2 text-xs"
                                style={{ borderColor: sev.color }}
                              >
                                <Badge
                                  tone="neutral"
                                  className={`text-xs mr-1 ${
                                    SEVERITY_BADGE_CLASSES[issue.severity] || ''
                                  }`}
                                >
                                  {sev.label}
                                </Badge>
                                <span className="text-foreground">{issue.description}</span>
                                {issue.suggestion && (
                                  <span className="text-muted-foreground ml-1">
                                    — 建议: {issue.suggestion}
                                  </span>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            )}
          </Card>
        )
      })}
    </div>
  )
}
