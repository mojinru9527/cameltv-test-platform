import { useState } from 'react'
import { Controller } from 'react-hook-form'
import AssertionEditor from '@/pages/apitest/components/AssertionEditor'
import { Button } from '@/ui'
import { Input } from '@/ui'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { SearchableSelect } from '@/components/ui/searchable-select'
import { Code2, FileText } from '@/lib/icons'
import { compareDomainGroups, groupDomainLabel } from '@/utils/domainNaming'

const CASE_TYPES = [
  { value: 'manual', label: '功能用例' },
  { value: 'api', label: '接口用例' },
  { value: 'ui', label: 'UI 用例' },
]

const PRIORITIES = [
  { value: 'P0', label: 'P0' },
  { value: 'P1', label: 'P1' },
  { value: 'P2', label: 'P2' },
  { value: 'P3', label: 'P3' },
]

const STATUSES = [
  { value: 'draft', label: '草稿' },
  { value: 'active', label: '启用' },
  { value: 'archived', label: '归档' },
]

export default function CaseForm({ register, control, errors, selType, domains, selModules, watch, setValue, datasets }: any) {
  const stepsValue = watch('steps') || ''
  const [stepsViewMode, setStepsViewMode] = useState<'formatted' | 'json'>('formatted')

  // Parse steps JSON to formatted text: "1、操作描述 — 预期结果"
  const formatSteps = (raw: string): string => {
    if (!raw || !raw.trim()) return ''
    try {
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) return raw
      return parsed.map((s: any) => {
        const stepNum = s.step || ''
        const desc = s.desc || s.action || s.description || ''
        const expected = s.expected || ''
        return expected ? `${stepNum}、${desc} — ${expected}` : `${stepNum}、${desc}`
      }).join('\n')
    } catch {
      return raw
    }
  }

  return (
    <div className="max-h-[60vh] overflow-y-auto space-y-4">
      {/* Title */}
      <div>
        <label htmlFor="case-title" className="mb-1 block text-sm font-medium">标题</label>
        <Input
          id="case-title"
          placeholder="用例标题"
          {...register('title')}
          data-invalid={!!errors.title}
          aria-invalid={!!errors.title}
          aria-describedby={errors.title ? 'case-title-error' : undefined}
        />
        {errors.title && (
          <p id="case-title-error" className="mt-1 text-xs text-destructive">{errors.title.message}</p>
        )}
      </div>

      {/* Row: Type, Priority, Status */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label htmlFor="case-type" className="mb-1 block text-sm font-medium">用例类型</label>
          <Controller
            name="case_type"
            control={control}
            render={({ field }: any) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="case-type" size="sm"><SelectValue placeholder="选择类型" /></SelectTrigger>
                <SelectContent position="popper">
                  {CASE_TYPES.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>
        <div>
          <label htmlFor="case-priority" className="mb-1 block text-sm font-medium">优先级</label>
          <Controller
            name="priority"
            control={control}
            render={({ field }: any) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="case-priority" size="sm"><SelectValue placeholder="优先级" /></SelectTrigger>
                <SelectContent position="popper">
                  {PRIORITIES.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>
        <div>
          <label htmlFor="case-status" className="mb-1 block text-sm font-medium">状态</label>
          <Controller
            name="status"
            control={control}
            render={({ field }: any) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="case-status" size="sm"><SelectValue placeholder="状态" /></SelectTrigger>
                <SelectContent position="popper">
                  {STATUSES.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>
      </div>

      {/* Row: Domain, Module */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="case-domain" className="mb-1 block text-sm font-medium">所属域 <span className="text-destructive">*</span></label>
          <Controller
            name="domain"
            control={control}
            render={({ field }: any) => (
              // Batch 178（FIX-173-P2-03）：可搜索域下拉（100+ 项扁平列表无法定位，
              // 按 用户端/运营后台/接口测试 分组 + 关键字过滤）
              // Batch 182（FIX-173-P3-04）：组名/标签统一走 domainNaming 规范——
              // 裸域补前缀展示（UGC → 用户端/UGC），选中仍提交原始 value 不污染表单。
              <SearchableSelect
                triggerId="case-domain"
                value={field.value || undefined}
                onValueChange={field.onChange}
                placeholder="选择域"
                options={[...(domains || [])]
                  .map((d: any) => {
                    const { group, label } = groupDomainLabel(d.domain)
                    return { value: d.domain, label, group }
                  })
                  .sort(
                    (a, b) => compareDomainGroups(a.group, b.group)
                      || a.label.localeCompare(b.label, 'zh-CN'),
                  )}
              />
            )}
          />
          {errors.domain && (
            <p className="mt-1 text-xs text-destructive" role="alert">{errors.domain.message}</p>
          )}
        </div>
        <div>
          <label htmlFor="case-module" className="mb-1 block text-sm font-medium">所属模块 <span className="text-destructive">*</span></label>
          <Controller
            name="module"
            control={control}
            render={({ field }: any) => (
              <Select value={field.value || undefined} onValueChange={field.onChange}>
                <SelectTrigger id="case-module" size="sm"><SelectValue placeholder="选择模块" /></SelectTrigger>
                <SelectContent position="popper">
                  {selModules.map((m: any) => (
                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
          {errors.module && (
            <p className="mt-1 text-xs text-destructive" role="alert">{errors.module.message}</p>
          )}
        </div>
      </div>

      {/* Conditional API fields */}
      {selType === 'api' && (
        <>
          <div className="grid grid-cols-[120px_1fr] gap-4">
            <div>
              <label htmlFor="case-api-method" className="mb-1 block text-sm font-medium">HTTP 方法</label>
              <Controller
                name="api_method"
                control={control}
                render={({ field }: any) => (
                  <Select value={field.value || undefined} onValueChange={field.onChange}>
                    <SelectTrigger id="case-api-method" size="sm"><SelectValue placeholder="方法" /></SelectTrigger>
                    <SelectContent position="popper">
                      {['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((v) => (
                        <SelectItem key={v} value={v}>{v}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div>
              <label htmlFor="case-api-endpoint" className="mb-1 block text-sm font-medium">接口路径</label>
              <Input id="case-api-endpoint" placeholder="/api/v1/xxx" {...register('api_endpoint')} />
            </div>
          </div>

          {/* C147-8: 数据集参数化绑定 */}
          <div className="grid grid-cols-[180px_1fr] gap-4">
            <div>
              <label htmlFor="case-dataset" className="mb-1 block text-sm font-medium">默认数据集</label>
              <Controller
                name="dataset_id"
                control={control}
                render={({ field }: any) => (
                  <Select
                    value={field.value == null ? '__none__' : String(field.value)}
                    onValueChange={(v) => field.onChange(v === '__none__' ? null : Number(v))}
                  >
                    <SelectTrigger id="case-dataset" size="sm"><SelectValue placeholder="未绑定（${列名} 替换需选数据集）" /></SelectTrigger>
                    <SelectContent position="popper">
                      <SelectItem value="__none__">未绑定</SelectItem>
                      {datasets.map((d: any) => (
                        <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="flex items-end pb-1">
              <p className="text-xs text-muted-foreground">执行时按数据集逐行替换请求中的 {'${列名}'} 变量</p>
            </div>
          </div>

          {/* 设计方法 / 正负向 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="case-design-method" className="mb-1 block text-sm font-medium">设计方法</label>
              <Controller
                name="case_design_method"
                control={control}
                render={({ field }: any) => (
                  <Select value={field.value || undefined} onValueChange={field.onChange}>
                    <SelectTrigger id="case-design-method" size="sm"><SelectValue placeholder="选择设计方法" /></SelectTrigger>
                    <SelectContent position="popper">
                      {['等价类划分', '边界值分析', '场景法', '错误推测', '组合覆盖'].map((v) => (
                        <SelectItem key={v} value={v}>{v}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div>
              <label htmlFor="case-positive-negative" className="mb-1 block text-sm font-medium">正负向/边界</label>
              <Controller
                name="positive_negative"
                control={control}
                render={({ field }: any) => (
                  <Select value={field.value || undefined} onValueChange={field.onChange}>
                    <SelectTrigger id="case-positive-negative" size="sm"><SelectValue placeholder="选择类型" /></SelectTrigger>
                    <SelectContent position="popper">
                      <SelectItem value="positive">正向</SelectItem>
                      <SelectItem value="negative">负向</SelectItem>
                      <SelectItem value="boundary">边界</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          {/* 请求参数 */}
          <div>
            <label htmlFor="case-api-body" className="mb-1 block text-sm font-medium">
              请求参数（JSON，字段完整、值贴合真实业务）
            </label>
            <Textarea
              id="case-api-body"
              rows={5}
              placeholder='{"page": 1, "size": 30, "queryList": [], "locale": "en"}'
              {...register('api_body')}
            />
          </div>

          {/* (batch-165) 断言改为结构化编辑器（与执行引擎 status_code/jsonpath/regex/response_time/header/type/array_length/json_schema 兼容） */}
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label htmlFor="case-api-assertions" className="text-sm font-medium">断言规则</label>
              <span className="text-xs text-muted-foreground">保存后执行时按规则校验响应</span>
            </div>
            <Controller
              name="api_assertions"
              control={control}
              render={({ field }: any) => (
                <AssertionEditor value={field.value || '[]'} onChange={field.onChange} />
              )}
            />
          </div>

          {/* 数据说明 */}
          <div>
            <label htmlFor="case-test-data-note" className="mb-1 block text-sm font-medium">数据说明（业务含义/来源）</label>
            <Textarea
              id="case-test-data-note"
              rows={2}
              placeholder="本用例输入数据的业务含义与来源（真实回填或按语义构造）"
              {...register('test_data_note')}
            />
          </div>
        </>
      )}

      {/* Preconditions */}
      <div>
        <label htmlFor="case-preconditions" className="mb-1 block text-sm font-medium">前置条件</label>
        <Textarea id="case-preconditions" rows={2} placeholder="执行用例前需要满足的条件" {...register('preconditions')} />
      </div>

      {/* Steps */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label htmlFor="case-steps" className="text-sm font-medium">测试步骤</label>
          <div className="flex items-center gap-1">
            <Button
              type="button"
              size="sm"
              variant={stepsViewMode === 'formatted' ? 'primary' : 'secondary'}
              className="h-7 text-xs px-2"
              onClick={() => setStepsViewMode('formatted')}
            >
              <FileText className="size-3 mr-1" />
              格式化
            </Button>
            <Button
              type="button"
              size="sm"
              variant={stepsViewMode === 'json' ? 'primary' : 'secondary'}
              className="h-7 text-xs px-2"
              onClick={() => setStepsViewMode('json')}
            >
              <Code2 className="size-3 mr-1" />
              JSON
            </Button>
          </div>
        </div>
        {stepsViewMode === 'formatted' ? (
          <Textarea
            id="case-steps"
            rows={4}
            placeholder="逐行输入测试步骤"
            value={formatSteps(stepsValue)}
            onChange={(event) => setValue('steps', event.target.value, {
              shouldDirty: true,
              shouldValidate: true,
            })}
            aria-invalid={!!errors.steps}
            aria-describedby={errors.steps ? 'case-steps-error' : undefined}
          />
        ) : (
          <Textarea
            id="case-steps"
            rows={4}
            placeholder='[{"step":1,"desc":"操作描述","expected":"预期结果"}]'
            {...register('steps')}
            aria-invalid={!!errors.steps}
            aria-describedby={errors.steps ? 'case-steps-error' : undefined}
          />
        )}
        {errors.steps && (
          <p id="case-steps-error" className="mt-1 text-xs text-destructive" role="alert">
            {errors.steps.message}
          </p>
        )}
      </div>

      {/* Expected Result */}
      <div>
        <label htmlFor="case-expected-result" className="mb-1 block text-sm font-medium">预期结果</label>
        <Textarea
          id="case-expected-result"
          rows={2}
          placeholder="整体预期结果描述"
          {...register('expected_result')}
          aria-invalid={!!errors.expected_result}
          aria-describedby={errors.expected_result ? 'case-expected-result-error' : undefined}
        />
        {errors.expected_result && (
          <p id="case-expected-result-error" className="mt-1 text-xs text-destructive" role="alert">
            {errors.expected_result.message}
          </p>
        )}
      </div>

      {/* Ref */}
    </div>
  )
}
