import { useEffect, useMemo, useState } from 'react'

import { Button, Badge, Input } from '@/ui'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Loader2, CheckCircle2, XCircle, Terminal, Play, FileText,
} from '@/lib/icons'
import { toast } from 'sonner'
import {
  compilePlayground, executePlayground,
  compilePlaygroundBatch, runPlaygroundBatch,
} from '@/api/playground'
import { fetchDomains, fetchTestCases } from '@/api/testcase'
import type { PlaygroundCompileResult, PlaygroundExecuteResult, PlaygroundCaseRunResult } from '@/api/playground'

interface DomainOption { id?: number; domain: string; modules: { id?: number; module: string; count: number }[] }

export default function PlaygroundPanel() {
  // （P2b）作为用例服务的「Playground」Tab 嵌入，不再是独立页面

  // ── 批量功能用例模式 ──
  const [domains, setDomains] = useState<DomainOption[]>([])
  const [domain, setDomain] = useState('')
  const [module, setModule] = useState('')
  const [positiveNegative, setPositiveNegative] = useState('')
  const [keyword, setKeyword] = useState('')
  const [cases, setCases] = useState<any[]>([])
  const [loadingCases, setLoadingCases] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [batchCompiling, setBatchCompiling] = useState(false)
  const [batchRunning, setBatchRunning] = useState(false)
  const [compiledItems, setCompiledItems] = useState<any[]>([])
  const [runResults, setRunResults] = useState<PlaygroundCaseRunResult[]>([])
  const [writeBack, setWriteBack] = useState(true)

  const moduleOptions = useMemo(() => {
    if (!domain) return []
    return domains.find((d) => d.domain === domain)?.modules ?? []
  }, [domain, domains])

  useEffect(() => {
    const controller = new AbortController()
    fetchDomains(controller.signal).then(setDomains).catch(() => {})
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setLoadingCases(true)
    fetchTestCases({
      case_type: 'manual',
      domain: domain || undefined,
      module: module || undefined,
      positive_negative: positiveNegative || undefined,
      keyword: keyword || undefined,
      page: 1,
      page_size: 100,
    }, controller.signal)
      .then((data: any) => setCases(data?.items ?? []))
      .catch(() => {})
      .finally(() => { if (!controller.signal.aborted) setLoadingCases(false) })
    return () => controller.abort()
  }, [domain, module, positiveNegative, keyword])

  const toggleCase = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const handleBatchCompile = async () => {
    if (selectedIds.size === 0) { toast.error('请先勾选功能用例'); return }
    setBatchCompiling(true)
    setRunResults([])
    try {
      const result = await compilePlaygroundBatch({ case_ids: [...selectedIds] })
      setCompiledItems(result.items)
      toast.success(`已编译 ${result.total} 条用例`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '批量编译失败')
    } finally {
      setBatchCompiling(false)
    }
  }

  const handleBatchRun = async () => {
    if (selectedIds.size === 0) { toast.error('请先勾选功能用例'); return }
    setBatchRunning(true)
    setRunResults([])
    try {
      const result = await runPlaygroundBatch({
        case_ids: [...selectedIds],
        write_back_to_ui: writeBack,
        timeout_ms: 60000,
      })
      setRunResults(result.results)
      const todoMsg = result.todo_blocked ? `，${result.todo_blocked} 条 TODO 拦截` : ''
      toast.success(`执行完成：${result.passed} 通过 / ${result.failed} 失败${todoMsg}`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '批量执行失败')
    } finally {
      setBatchRunning(false)
    }
  }

  // ── 手动输入模式（保留原能力）──
  const [caseId, setCaseId] = useState('')
  const [source, setSource] = useState('')
  const [sourceType, setSourceType] = useState('gherkin')
  const [compiling, setCompiling] = useState(false)
  const [compileError, setCompileError] = useState('')
  const [compiled, setCompiled] = useState<PlaygroundCompileResult | null>(null)
  const [executing, setExecuting] = useState(false)
  const [execResult, setExecResult] = useState<PlaygroundExecuteResult | null>(null)

  const handleCompile = async () => {
    if (!source.trim() && !caseId.trim()) { toast.error('请输入步骤文本或用例编号'); return }
    setCompiling(true)
    setExecResult(null)
    setCompileError('')
    try {
      const result = await compilePlayground({
        source,
        source_type: sourceType,
        case_id: caseId.trim() || undefined,
      })
      setCompiled(result)
      toast.success('编译成功')
    } catch (error) {
      const msg = error instanceof Error ? error.message : '编译失败，请重试'
      setCompileError(msg)
      toast.error(msg)
    } finally {
      setCompiling(false)
    }
  }

  const handleExecute = async () => {
    if (!compiled?.spec_code) { toast.error('请先编译生成 spec'); return }
    setExecuting(true)
    setExecResult(null)
    try {
      const result = await executePlayground({ spec_code: compiled.spec_code, timeout_ms: 60000 })
      setExecResult(result)
      toast.success(result.passed ? '执行通过' : '执行未通过')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '执行失败，请重试')
    } finally {
      setExecuting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Playground</h2>
        <p className="text-sm text-muted-foreground mt-1">
          功能用例库批量编译 → Playwright 执行 / 截图 / 回写 UI 任务
        </p>
      </div>

      <Card>
        <CardContent className="p-4 space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <Label>业务域</Label>
              <Select value={domain} onValueChange={(v) => { setDomain(v); setModule('') }}>
                <SelectTrigger className="w-[180px]"><SelectValue placeholder="全部域" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">全部域</SelectItem>
                  {domains.map((d) => (
                    <SelectItem key={d.domain} value={d.domain}>{d.domain}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>模块</Label>
              <Select value={module} onValueChange={setModule}>
                <SelectTrigger className="w-[180px]"><SelectValue placeholder="全部模块" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">全部模块</SelectItem>
                  {moduleOptions.map((m) => (
                    <SelectItem key={m.module} value={m.module}>{m.module}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>正负向</Label>
              <Select value={positiveNegative} onValueChange={setPositiveNegative}>
                <SelectTrigger className="w-[130px]"><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">全部</SelectItem>
                  <SelectItem value="正向">正向</SelectItem>
                  <SelectItem value="负向">负向</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>关键字</Label>
              <Input className="w-[220px]" value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="标题/模块/路径" />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox checked={writeBack} onCheckedChange={(v) => setWriteBack(v === true)} aria-label="回写 UI 任务" />
              回写 UI 任务
            </label>
          </div>

          <div className="rounded-lg border max-h-[360px] overflow-auto">
            {loadingCases ? (
              <div className="p-6 text-center text-muted-foreground">加载用例中…</div>
            ) : cases.length === 0 ? (
              <div className="p-6 text-center text-muted-foreground">当前筛选无功能用例</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-muted text-left">
                  <tr>
                    <th className="p-2 w-10">选择</th>
                    <th className="p-2">标题</th>
                    <th className="p-2 w-28">模块</th>
                    <th className="p-2 w-20">正负向</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {cases.map((c: any) => (
                    <tr key={c.id} className="hover:bg-muted/50">
                      <td className="p-2">
                        <Checkbox checked={selectedIds.has(c.id)} onCheckedChange={() => toggleCase(c.id)} aria-label={`选择用例 ${c.title}`} />
                      </td>
                      <td className="p-2">
                        <div className="font-medium">{c.title}</div>
                        <div className="text-xs text-muted-foreground">{c.case_id_code || c.case_id}</div>
                      </td>
                      <td className="p-2 text-xs text-muted-foreground">{c.module || '-'}</td>
                      <td className="p-2 text-xs">{c.positive_negative || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={handleBatchCompile} disabled={batchCompiling || batchRunning || selectedIds.size === 0}>
              {batchCompiling ? <Loader2 className="size-4 mr-1 animate-spin" /> : <Terminal className="size-4 mr-1" />}
              批量编译 ({selectedIds.size})
            </Button>
            <Button variant="primary" onClick={handleBatchRun} disabled={batchCompiling || batchRunning || selectedIds.size === 0}>
              {batchRunning ? <Loader2 className="size-4 mr-1 animate-spin" /> : <Play className="size-4 mr-1" />}
              批量执行 ({selectedIds.size})
            </Button>
          </div>
        </CardContent>
      </Card>

      {compiledItems.length > 0 && (
        <Card>
          <CardContent className="p-4 space-y-3">
            <h2 className="text-sm font-medium">批量编译结果（{compiledItems.length}）</h2>
            <div className="max-h-[420px] overflow-auto space-y-3">
              {compiledItems.map((item: any) => (
                <div key={item.case_id} className="rounded-md border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-sm">{item.case_title}</span>
                    {item.has_todo ? <Badge tone="warning">存在 TODO</Badge> : <Badge tone="success">可执行</Badge>}
                  </div>
                  <pre className="whitespace-pre-wrap font-mono text-xs bg-muted/40 rounded-md p-2 mt-2 max-h-[180px] overflow-auto">{item.spec_code}</pre>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {runResults.length > 0 && (
        <Card>
          <CardContent className="p-4 space-y-3">
            <h2 className="text-sm font-medium">批量执行结果（{runResults.length}）</h2>
            <div className="grid gap-3">
              {runResults.map((r) => (
                <div key={r.case_id} className="rounded-md border p-3">
                  <div className="flex items-center gap-2">
                    {r.todo_blocked ? (
                      <>
                        <XCircle className="size-4 text-status-warning" />
                        <span className="font-medium text-sm">{r.case_title}</span>
                        <Badge tone="warning">TODO 拦截（未执行）</Badge>
                      </>
                    ) : (
                      <>
                        {r.passed ? <CheckCircle2 className="size-4 text-status-success" /> : <XCircle className="size-4 text-status-danger" />}
                        <span className="font-medium text-sm">{r.case_title}</span>
                        <Badge tone={r.passed ? 'success' : 'danger'}>{r.passed ? '通过' : '失败'}</Badge>
                      </>
                    )}
                    {r.ui_job_id ? <Badge tone="neutral">UI 任务 #{r.ui_job_id}</Badge> : null}
                    <span className="text-xs text-muted-foreground">{r.duration_ms} ms</span>
                  </div>
                  {r.screenshot_base64 && (
                    <img src={`data:image/png;base64,${r.screenshot_base64}`} alt={`${r.case_title} 截图`} className="rounded-md border mt-2 max-h-[240px]" />
                  )}
                  {(r.stdout || r.stderr) && (
                    <pre className="whitespace-pre-wrap font-mono text-xs bg-muted/40 rounded-md p-2 mt-2 max-h-[160px] overflow-auto">{r.stdout || r.stderr}</pre>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-4 space-y-4">
          <h2 className="text-sm font-medium">手动输入（单条草稿）</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label htmlFor="playground-case-id">用例编号（可选）</Label>
              <Input id="playground-case-id" placeholder="留空则使用下方步骤文本" value={caseId} onChange={(e) => setCaseId(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="playground-source-type">步骤格式</Label>
              <Select value={sourceType} onValueChange={setSourceType}>
                <SelectTrigger id="playground-source-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="gherkin">Gherkin（Given/When/Then 或 当/则）</SelectItem>
                  <SelectItem value="markdown">Markdown</SelectItem>
                  <SelectItem value="plain">纯文本</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1">
            <Label htmlFor="playground-source">步骤文本</Label>
            <Textarea id="playground-source" rows={6} placeholder={'示例：\n当 打开「http://localhost:5211/login」\n当 在「#username」输入「admin」\n当 点击「登录」\n则 看到「工作台」\n当 截图'} value={source} onChange={(e) => setSource(e.target.value)} />
          </div>
          <div className="flex items-center gap-2">
            {compileError && <p role="alert" className="text-sm text-destructive">{compileError}</p>}
            <Button onClick={handleCompile} disabled={compiling || executing}>
              {compiling ? <Loader2 className="size-4 mr-1 animate-spin" /> : <FileText className="size-4 mr-1" />}
              编译
            </Button>
            <Button variant="secondary" onClick={handleExecute} disabled={!compiled || executing || compiling}>
              {executing ? <Loader2 className="size-4 mr-1 animate-spin" /> : null}
              执行
            </Button>
          </div>
          {compiled && (
            <pre className="whitespace-pre-wrap font-mono text-xs bg-muted/40 rounded-md p-3 max-h-[280px] overflow-auto">
              {compiled.spec_code}
            </pre>
          )}
          {execResult && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                {execResult.passed ? <CheckCircle2 className="size-4 text-status-success" /> : <XCircle className="size-4 text-status-danger" />}
                <Badge tone={execResult.passed ? 'success' : 'danger'}>{execResult.passed ? '通过' : '未通过'}</Badge>
                <span className="text-xs text-muted-foreground">耗时 {execResult.duration_ms} ms</span>
              </div>
              {execResult.screenshot_base64 && <img src={`data:image/png;base64,${execResult.screenshot_base64}`} alt="执行截图" className="rounded-md border max-h-[360px]" />}
              {(execResult.stdout || execResult.stderr) && (
                <pre className="whitespace-pre-wrap font-mono text-xs bg-muted/40 rounded-md p-3 max-h-[200px] overflow-auto">{execResult.stdout || execResult.stderr}</pre>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
