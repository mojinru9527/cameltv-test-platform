import { useState } from 'react'

import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { Button } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/ui'
import { Input } from '@/ui'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Loader2, CheckCircle2, XCircle, Terminal } from '@/lib/icons'
import { toast } from 'sonner'
import { compilePlayground, executePlayground } from '@/api/playground'
import type { PlaygroundCompileResult, PlaygroundExecuteResult } from '@/api/playground'

const SOURCE_TYPE_LABEL: Record<string, string> = {
  gherkin: 'Gherkin（Given/When/Then 或 当/则）',
  markdown: 'Markdown',
  plain: '纯文本',
}

export default function PlaygroundPage() {
  useDocumentTitle('Playground')
  const [caseId, setCaseId] = useState('')
  const [source, setSource] = useState('')
  const [sourceType, setSourceType] = useState('gherkin')
  const [compiling, setCompiling] = useState(false)
  const [compiled, setCompiled] = useState<PlaygroundCompileResult | null>(null)
  const [executing, setExecuting] = useState(false)
  const [execResult, setExecResult] = useState<PlaygroundExecuteResult | null>(null)

  const handleCompile = async () => {
    if (!source.trim() && !caseId.trim()) {
      toast.error('请输入步骤文本或用例编号（二选一）')
      return
    }
    setCompiling(true)
    setExecResult(null)
    try {
      const result = await compilePlayground({
        source,
        source_type: sourceType,
        case_id: caseId.trim() || undefined,
      })
      setCompiled(result)
      toast.success('编译成功')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '编译失败，请重试')
    } finally {
      setCompiling(false)
    }
  }

  const handleExecute = async () => {
    if (!compiled?.spec_code) {
      toast.error('请先编译生成 spec')
      return
    }
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
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Playground</h1>
        <p className="text-sm text-muted-foreground mt-1">
          功能用例 → Playwright 编译 / 执行（batch-74 起由 API-only 转正式 UI）
        </p>
      </div>

      <Card>
        <CardContent className="p-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label htmlFor="playground-case-id">用例编号（可选，如 TC-LIVE-001）</Label>
              <Input
                id="playground-case-id"
                placeholder="留空则使用下方步骤文本"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="playground-source-type">步骤格式</Label>
              <Select value={sourceType} onValueChange={setSourceType}>
                <SelectTrigger id="playground-source-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(SOURCE_TYPE_LABEL).map(([value, label]) => (
                    <SelectItem key={value} value={value}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="playground-source">步骤文本</Label>
            <Textarea
              id="playground-source"
              rows={8}
              placeholder={'示例：\n当 打开「http://localhost:5211/login」\n当 在「#username」输入「admin」\n当 点击「登录」\n则 看到「工作台」\n当 截图'}
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={handleCompile} disabled={compiling || executing}>
              {compiling ? <Loader2 className="size-4 mr-1 animate-spin" /> : <Terminal className="size-4 mr-1" />}
              编译
            </Button>
            <Button variant="secondary" onClick={handleExecute} disabled={!compiled || executing || compiling}>
              {executing ? <Loader2 className="size-4 mr-1 animate-spin" /> : null}
              执行
            </Button>
            {compiled && (
              <span className="text-xs text-muted-foreground">
                编译耗时 {compiled.compile_ms} ms · {compiled.spec_type}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {compiled && (
        <Card>
          <CardContent className="p-4 space-y-3">
            <h2 className="text-sm font-medium">生成 Spec（.spec.ts）</h2>
            {compiled.spec_code.includes('未识别步骤') && (
              <Badge tone="warning">存在未识别步骤（TODO），需人工补充后才能可靠执行</Badge>
            )}
            <pre className="whitespace-pre-wrap font-mono text-xs bg-muted/40 rounded-md p-3 max-h-[320px] overflow-auto">
              {compiled.spec_code}
            </pre>
          </CardContent>
        </Card>
      )}

      {execResult && (
        <Card>
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center gap-2">
              {execResult.passed ? (
                <CheckCircle2 className="size-4 text-status-success" aria-label="通过" />
              ) : (
                <XCircle className="size-4 text-status-danger" aria-label="失败" />
              )}
              <Badge tone={execResult.passed ? 'success' : 'danger'}>{execResult.passed ? '通过' : '未通过'}</Badge>
              <span className="text-xs text-muted-foreground">耗时 {execResult.duration_ms} ms</span>
            </div>
            {execResult.screenshot_base64 && (
              <img
                src={`data:image/png;base64,${execResult.screenshot_base64}`}
                alt="Playwright 执行截图"
                className="rounded-md border max-h-[360px]"
              />
            )}
            {(execResult.stdout || execResult.stderr) && (
              <pre className="whitespace-pre-wrap font-mono text-xs bg-muted/40 rounded-md p-3 max-h-[240px] overflow-auto">
                {execResult.stdout || execResult.stderr}
              </pre>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
