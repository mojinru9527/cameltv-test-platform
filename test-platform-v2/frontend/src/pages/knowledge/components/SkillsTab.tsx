import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { fetchSkills, applySkill, type SkillTemplate, type SkillParam } from '@/api/knowledge'
import {
  Loader2,
  TestTube,
  Bug,
  FileCode,
  AlertTriangle,
  FileText,
  Target,
  Zap,
  Play,
  ChevronRight,
} from '@/lib/icons'
import { toast } from 'sonner'

const ICON_MAP: Record<string, typeof TestTube> = {
  TestTube,
  Bug,
  FileCode,
  AlertTriangle,
  FileText,
  Target,
}

const CATEGORY_LABELS: Record<string, string> = {
  '生成': '生成',
  '分析': '分析',
  '提取': '提取',
  '治理': '治理',
  '总结': '总结',
  '预测': '预测',
}

export default function SkillsTab() {
  const [skills, setSkills] = useState<SkillTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<SkillTemplate | null>(null)
  const [params, setParams] = useState<Record<string, any>>({})
  const [applying, setApplying] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    fetchSkills()
      .then(setSkills)
      .catch(() => toast.error('加载 Skills 模板失败'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleApply = async (skill: SkillTemplate) => {
    setApplying(skill.name)
    setResult(null)
    try {
      const hasParams = skill.input_params.some((p) => p.required)
      const filledParams: Record<string, any> = {}
      for (const p of skill.input_params) {
        if (params[p.key] !== undefined && params[p.key] !== '') {
          filledParams[p.key] = p.type.includes('array')
            ? String(params[p.key]).split('\n').filter(Boolean)
            : params[p.key]
        }
      }

      const res = await applySkill(skill.name, hasParams ? filledParams : undefined)
      if (res.success) {
        toast.success(`"${skill.label}" 执行成功`)
        setResult(res.result || res.note || res.prompt || '执行完成，Agent 暂不可用，返回了原始分析上下文')
      } else {
        toast.error(res.error || '执行失败')
        setResult(res.error || '未知错误')
      }
    } catch (e: any) {
      toast.error(e?.message || '执行失败')
    } finally {
      setApplying(null)
    }
  }

  const renderParamInput = (param: SkillParam) => {
    const value = params[param.key] ?? param.default ?? ''

    if (param.type === 'select' && param.options) {
      return (
        <select
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
          value={String(value)}
          onChange={(e) => setParams({ ...params, [param.key]: e.target.value })}
        >
          {param.options.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      )
    }
    if (param.type === 'str_array' || param.type === 'int_array') {
      return (
        <textarea
          className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="一行一个值"
          value={Array.isArray(value) ? value.join('\n') : String(value)}
          onChange={(e) =>
            setParams({
              ...params,
              [param.key]: e.target.value.split('\n').filter(Boolean),
            })
          }
        />
      )
    }
    return (
      <Input
        value={String(value)}
        onChange={(e) =>
          setParams({
            ...params,
            [param.key]: param.type === 'int' ? Number(e.target.value) || '' : e.target.value,
          })
        }
        placeholder={param.description || `输入 ${param.label}`}
      />
    )
  }

  if (loading) {
    return (
      <div className="grid min-h-[200px] place-items-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Group by category
  const categories: Record<string, SkillTemplate[]> = {}
  for (const s of skills) {
    const cat = s.category || '其他'
    if (!categories[cat]) categories[cat] = []
    categories[cat].push(s)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Zap className="size-4" />
        <span>{skills.length} 个 AI 能力模板可用</span>
      </div>

      {Object.entries(categories).map(([cat, items]) => (
        <div key={cat} className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">
            {CATEGORY_LABELS[cat] || cat}
          </h4>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((skill) => {
              const Icon = ICON_MAP[skill.icon] || Zap
              return (
                <Card
                  key={skill.name}
                  className="cursor-pointer hover:border-primary/50 transition-colors"
                  onClick={() => { setSelected(skill); setParams({}); setResult(null) }}
                >
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Icon className="size-4 text-primary" />
                      {skill.label}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      {skill.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">
                        {skill.input_params.length} 个参数
                      </span>
                      <ChevronRight className="size-4 text-muted-foreground/50" />
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      ))}

      {/* Skill detail/apply dialog */}
      <Dialog open={!!selected} onOpenChange={(open) => { if (!open) { setSelected(null); setResult(null) } }}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  {(() => {
                    const Icon = ICON_MAP[selected.icon] || Zap
                    return <Icon className="size-5 text-primary" />
                  })()}
                  {selected.label}
                </DialogTitle>
                <DialogDescription>{selected.description}</DialogDescription>
              </DialogHeader>

              {/* Parameters */}
              {selected.input_params.length > 0 && (
                <div className="space-y-3">
                  <div className="text-xs font-medium text-muted-foreground">参数配置</div>
                  {selected.input_params.map((p) => (
                    <div key={p.key}>
                      <label className="text-xs font-medium mb-1 block">
                        {p.label}
                        {p.required && <span className="text-red-500 ml-0.5">*</span>}
                      </label>
                      {renderParamInput(p)}
                      {p.description && (
                        <p className="text-xs text-muted-foreground mt-0.5">{p.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Result */}
              {result && (
                <div className="rounded-md border bg-muted/30 p-3 max-h-60 overflow-auto">
                  <pre className="text-xs whitespace-pre-wrap break-words">{result}</pre>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => { setSelected(null); setResult(null) }}>
                  取消
                </Button>
                <Button
                  onClick={() => handleApply(selected)}
                  disabled={applying === selected.name}
                >
                  {applying === selected.name ? (
                    <>
                      <Loader2 className="size-4 mr-1 animate-spin" />
                      执行中…
                    </>
                  ) : (
                    <>
                      <Play className="size-4 mr-1" />
                      执行
                    </>
                  )}
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
