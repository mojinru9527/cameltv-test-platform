import { useState } from 'react'
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useAuthStore } from '@/stores/auth'
import { toast } from 'sonner'
import {
  buildTemplate,
  extractEntityGraph,
  materializeTemplate,
  validateTemplate,
  type BuildTemplateResult,
  type EntityGraphResult,
  type MaterializeTemplateResult,
  type ValidateTemplateResult,
} from '@/api/production'
import { ProdReadOnlyBanner } from './components/ProdReadOnlyBanner'
import { EntityGraphViewer } from './components/EntityGraphViewer'
import { TemplatePreview } from './components/TemplatePreview'
import { MaskPreviewTable, type MaskEntry } from './components/MaskPreviewTable'
import { GitBranch, FileCheck, ShieldCheck, RefreshCw } from '@/lib/icons'

/**
 * /production/templates — entity graph extraction + template build / validate /
 * materialize with mask preview.
 */
export default function ProductionTemplatesPage() {
  const currentProjectId = useAuthStore((s) => s.currentProjectId)

  // Extract graph
  const [rootEntityType, setRootEntityType] = useState('')
  const [rootRefHash, setRootRefHash] = useState('')
  const [sourceEnvId, setSourceEnvId] = useState('')
  const [graph, setGraph] = useState<EntityGraphResult | null>(null)
  const [extracting, setExtracting] = useState(false)

  // Build template
  const [templateName, setTemplateName] = useState('')
  const [maskingProfileId, setMaskingProfileId] = useState('')
  const [template, setTemplate] = useState<BuildTemplateResult | null>(null)
  const [building, setBuilding] = useState(false)

  // Validate / materialize
  const [validation, setValidation] = useState<ValidateTemplateResult | null>(null)
  const [validating, setValidating] = useState(false)
  const [targetEnvId, setTargetEnvId] = useState('')
  const [materialization, setMaterialization] = useState<MaterializeTemplateResult | null>(null)
  const [materializing, setMaterializing] = useState(false)

  const doExtract = async () => {
    if (!currentProjectId) return toast.error('缺少项目上下文')
    if (!rootEntityType.trim() || !rootRefHash.trim()) {
      return toast.error('请填写 root_entity_type 与 root_ref_hash')
    }
    const source_environment_id = Number(sourceEnvId)
    if (!Number.isFinite(source_environment_id) || source_environment_id <= 0) {
      return toast.error('请填写 source_environment_id')
    }
    setExtracting(true)
    try {
      const result = await extractEntityGraph({
        project_id: currentProjectId,
        root_entity_type: rootEntityType.trim(),
        root_ref_hash: rootRefHash.trim(),
        source_environment_id,
      })
      setGraph(result)
      toast.success('实体图谱已提取')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '提取失败')
    } finally {
      setExtracting(false)
    }
  }

  const doBuild = async () => {
    if (!currentProjectId) return toast.error('缺少项目上下文')
    if (!graph) return toast.error('请先提取实体图谱')
    if (!templateName.trim()) return toast.error('请填写模板名称')
    setBuilding(true)
    try {
      const result = await buildTemplate({
        project_id: currentProjectId,
        name: templateName.trim(),
        entity_graph_snapshot_id: graph.id,
        masking_profile_id: maskingProfileId ? Number(maskingProfileId) : null,
      })
      setTemplate(result)
      setValidation(null)
      setMaterialization(null)
      toast.success('模板已构建')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '构建失败')
    } finally {
      setBuilding(false)
    }
  }

  const doValidate = async () => {
    if (!currentProjectId || !template) return toast.error('请先构建模板')
    setValidating(true)
    try {
      const result = await validateTemplate(template.id, {
        project_id: currentProjectId,
        template_id: template.id,
      })
      setValidation(result)
      toast.success('校验完成')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '校验失败')
    } finally {
      setValidating(false)
    }
  }

  const doMaterialize = async () => {
    if (!currentProjectId || !template) return toast.error('请先构建模板')
    const target_environment_id = Number(targetEnvId)
    if (!Number.isFinite(target_environment_id) || target_environment_id <= 0) {
      return toast.error('请填写 target_environment_id')
    }
    setMaterializing(true)
    try {
      const result = await materializeTemplate(template.id, {
        project_id: currentProjectId,
        template_id: template.id,
        target_environment_id,
      })
      setMaterialization(result)
      toast.success('模板已物化')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '物化失败')
    } finally {
      setMaterializing(false)
    }
  }

  const masks: MaskEntry[] = (graph?.nodes ?? []).map((node) => ({
    entity: node.entity_type ?? node.label ?? String(node.id),
    field: node.ref_hash ?? String(node.id),
    classification: node.entity_type ?? 'ENTITY',
    strategy: 'REDACT',
  }))

  return (
    <div className="space-y-4">
      <ProdReadOnlyBanner />
      <PageHeader title="生产模板" description="实体图谱提取 · 模板构建 / 校验 / 物化（V36-013/014）" />
      {currentProjectId == null && (
        <p className="text-sm text-muted-foreground">未选择项目，无法构建模板。</p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="size-4" /> 1. 提取实体图谱
          </CardTitle>
          <CardDescription>从真实状态数据中抽取实体关系图，作为模板快照。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
            <div className="space-y-1.5">
              <Label>根实体类型</Label>
              <Input value={rootEntityType} onChange={(e) => setRootEntityType(e.target.value)} placeholder="root_entity_type" />
            </div>
            <div className="space-y-1.5">
              <Label>根引用哈希</Label>
              <Input value={rootRefHash} onChange={(e) => setRootRefHash(e.target.value)} placeholder="root_ref_hash" />
            </div>
            <div className="space-y-1.5">
              <Label>来源环境 ID</Label>
              <Input value={sourceEnvId} onChange={(e) => setSourceEnvId(e.target.value)} placeholder="source_environment_id" inputMode="numeric" />
            </div>
            <div className="flex items-end">
              <Button variant="primary" size="sm" onClick={() => void doExtract()} disabled={extracting}>
                <RefreshCw className="size-3.5" /> {extracting ? '提取中…' : '提取'}
              </Button>
            </div>
          </div>
          <EntityGraphViewer graph={graph} loading={extracting} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileCheck className="size-4" /> 2. 构建模板
          </CardTitle>
          <CardDescription>以实体图谱快照为底构建生产数据模板。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
            <div className="space-y-1.5">
              <Label>模板名称</Label>
              <Input value={templateName} onChange={(e) => setTemplateName(e.target.value)} placeholder="name" />
            </div>
            <div className="space-y-1.5">
              <Label>脱敏配置 ID（可选）</Label>
              <Input value={maskingProfileId} onChange={(e) => setMaskingProfileId(e.target.value)} placeholder="masking_profile_id" inputMode="numeric" />
            </div>
            <div className="flex items-end">
              <Button variant="primary" size="sm" onClick={() => void doBuild()} disabled={building || !graph}>
                <RefreshCw className="size-3.5" /> {building ? '构建中…' : '构建'}
              </Button>
            </div>
          </div>
          <TemplatePreview template={template} materialization={materialization} loading={building} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="size-4" /> 3. 校验 & 物化
          </CardTitle>
          <CardDescription>校验模板是否泄漏敏感字段，并在目标环境物化。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" size="sm" onClick={() => void doValidate()} disabled={validating || !template}>
              <RefreshCw className="size-3.5" /> {validating ? '校验中…' : '校验模板'}
            </Button>
            <div className="flex items-center gap-2">
              <Label className="text-xs text-muted-foreground mr-1">目标环境</Label>
              <Input
                value={targetEnvId}
                onChange={(e) => setTargetEnvId(e.target.value)}
                placeholder="target_environment_id"
                inputMode="numeric"
                className="w-40"
              />
            </div>
            <Button variant="primary" size="sm" onClick={() => void doMaterialize()} disabled={materializing || !template}>
              <RefreshCw className="size-3.5" /> {materializing ? '物化中…' : '物化模板'}
            </Button>
          </div>
          {validation && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <Badge tone="neutral" className={validation.validation_status !== 'VALID' && validation.validation_status !== 'OK' ? 'bg-status-danger-muted text-status-danger' : 'bg-status-success-muted text-status-success'}>
                  {validation.validation_status}
                </Badge>
                <span className="text-muted-foreground">泄漏 {validation.leaks.length} 项</span>
              </div>
              {validation.leaks.length > 0 && (
                <pre className="max-h-48 overflow-auto rounded-md border bg-muted/30 p-2 font-mono text-xs whitespace-pre-wrap break-all">
                  {JSON.stringify(validation.leaks, null, 2)}
                </pre>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="size-4" /> 脱敏预览
          </CardTitle>
          <CardDescription>基于当前图谱快照推导的掩码节点一览。</CardDescription>
        </CardHeader>
        <CardContent>
          <MaskPreviewTable masks={masks} loading={extracting} />
        </CardContent>
      </Card>
    </div>
  )
}
