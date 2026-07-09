/**
 * 断言规则编辑器 — 可视化编辑响应断言
 * 被 DebugTab 和 ApiDebugPanel 等组件复用
 *
 * 支持的断言类型:
 * - status_code: HTTP 状态码比较
 * - jsonpath: JSON Path 取值 + 运算符比较
 * - regex: 正则表达式匹配响应体
 * - response_time: 响应时间阈值
 * - header: 响应头字段取值
 * - type: JSON Path 取值的类型校验
 * - array_length: JSON Path 数组长度
 * - json_schema: JSON Schema 校验
 *
 * value 是 JSON 字符串，内部解析为 item[] 数组
 */
import { useEffect, useState } from 'react'
import { Plus, Trash2 } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

type AssertionItem = {
  type: string
  path: string
  expected: string
  operator: string
  pattern: string
  key: string
}

interface Props {
  value: string
  onChange: (v: string) => void
}

export default function AssertionEditor({ value, onChange }: Props) {
  const [items, setItems] = useState<AssertionItem[]>([])
  const [expanded, setExpanded] = useState(true)

  useEffect(() => {
    try { setItems(JSON.parse(value)) } catch { setItems([]) }
  }, [value])

  const sync = (newItems: AssertionItem[]) => {
    setItems(newItems)
    onChange(JSON.stringify(newItems, null, 2))
  }

  const addRule = () => {
    sync([...items, { type: 'status_code', path: '', expected: '200', operator: 'eq', pattern: '', key: '' }])
  }

  const removeRule = (i: number) => sync(items.filter((_, idx) => idx !== i))

  const updateRule = (i: number, field: string, val: string) => {
    const next = [...items]
    ;(next[i] as any)[field] = val
    sync(next)
  }

  return (
    <Card>
      <CardHeader
        className="flex flex-row items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <CardTitle className="text-sm">断言规则 ({items.length})</CardTitle>
        <Button
          size="icon-sm"
          variant="ghost"
          onClick={(e) => { e.stopPropagation(); addRule() }}
          title="添加断言"
        >
          <Plus className="size-4" />
        </Button>
      </CardHeader>
      {expanded && (
        <CardContent className="space-y-3">
          {items.map((rule, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2 p-2 border rounded-md">
              {/* 断言类型选择 */}
              <Select value={rule.type} onValueChange={(v) => updateRule(i, 'type', v)}>
                <SelectTrigger className="w-[140px] h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="status_code">status_code</SelectItem>
                  <SelectItem value="jsonpath">jsonpath</SelectItem>
                  <SelectItem value="regex">regex</SelectItem>
                  <SelectItem value="response_time">response_time</SelectItem>
                  <SelectItem value="header">header</SelectItem>
                  <SelectItem value="type">type</SelectItem>
                  <SelectItem value="array_length">array_length</SelectItem>
                  <SelectItem value="json_schema">json_schema</SelectItem>
                </SelectContent>
              </Select>

              {/* header 类型：需要 key */}
              {rule.type === 'header' && (
                <Input
                  className="w-[120px] h-8 text-xs"
                  placeholder="Header名"
                  value={rule.key}
                  onChange={(e) => updateRule(i, 'key', e.target.value)}
                  aria-label={`断言 ${i + 1} Header 名称`}
                />
              )}

              {/* jsonpath / type / array_length：需要 path */}
              {['jsonpath', 'type', 'array_length'].includes(rule.type) && (
                <Input
                  className="w-[140px] h-8 text-xs"
                  placeholder="$.data.code"
                  value={rule.path}
                  onChange={(e) => updateRule(i, 'path', e.target.value)}
                  aria-label={`断言 ${i + 1} JSON Path`}
                />
              )}

              {/* regex：需要 pattern */}
              {rule.type === 'regex' && (
                <Input
                  className="w-[140px] h-8 text-xs"
                  placeholder="正则表达式"
                  value={rule.pattern}
                  onChange={(e) => updateRule(i, 'pattern', e.target.value)}
                  aria-label={`断言 ${i + 1} 正则表达式`}
                />
              )}

              {/* 运算符 */}
              <Select value={rule.operator} onValueChange={(v) => updateRule(i, 'operator', v)}>
                <SelectTrigger className="w-[80px] h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="eq">=</SelectItem>
                  <SelectItem value="neq">≠</SelectItem>
                  <SelectItem value="gt">&gt;</SelectItem>
                  <SelectItem value="lt">&lt;</SelectItem>
                  <SelectItem value="gte">≥</SelectItem>
                  <SelectItem value="lte">≤</SelectItem>
                  <SelectItem value="contains">含</SelectItem>
                  <SelectItem value="exists">存在</SelectItem>
                </SelectContent>
              </Select>

              {/* 期望值 */}
              <Input
                className="flex-1 min-w-[100px] h-8 text-xs"
                placeholder="期望值"
                value={rule.expected}
                onChange={(e) => updateRule(i, 'expected', e.target.value)}
                aria-label={`断言 ${i + 1} 期望值`}
              />

              {/* 删除按钮 */}
              <Button
                size="icon-sm"
                variant="ghost"
                className="text-destructive h-8 w-8"
                onClick={() => removeRule(i)}
              >
                <Trash2 className="size-3" />
              </Button>
            </div>
          ))}
          {items.length === 0 && (
            <p className="text-xs text-muted-foreground">暂未配置断言。点击 + 添加。</p>
          )}
        </CardContent>
      )}
    </Card>
  )
}
