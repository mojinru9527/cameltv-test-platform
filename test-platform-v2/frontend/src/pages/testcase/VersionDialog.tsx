/**
 * Version history dialog for test cases.
 * C4: Lists all version snapshots with changed fields.
 */
import { useState, useEffect } from 'react'
import { History, ChevronRight } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import type { TestCaseVersion, TestCaseVersionDetail } from '@/types'
import { fetchVersionDetail } from '@/api/testcase'

interface Props {
  open: boolean
  onClose: () => void
  caseData: any | null
  versions: TestCaseVersion[]
}

const FIELD_LABELS: Record<string, string> = {
  title: '标题', domain: '域', module: '模块', case_type: '用例类型',
  priority: '优先级', status: '状态', preconditions: '前置条件',
  steps: '测试步骤', expected_result: '预期结果',
  api_method: '请求方法', api_endpoint: 'API路径', tags: '标签',
}

export default function VersionDialog({ open, onClose, caseData, versions }: Props) {
  const [selectedVersion, setSelectedVersion] = useState<TestCaseVersionDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setSelectedVersion(null)
  }, [open])

  const loadDetail = async (v: TestCaseVersion) => {
    if (!caseData) return
    setLoading(true)
    try {
      const detail = await fetchVersionDetail(caseData.id, v.id)
      setSelectedVersion(detail)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-[640px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="size-5" />
            版本历史
          </DialogTitle>
          <DialogDescription>
            {caseData?.title || caseData?.case_id || '用例'} 的变更记录
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4 max-h-[400px]">
          {/* Version list */}
          <div className="border rounded-md">
            <div className="h-[360px] overflow-y-auto">
              {versions.length === 0 ? (
                <p className="text-sm text-muted-foreground p-4 text-center">暂无版本记录</p>
              ) : (
                <div className="space-y-0.5 p-2">
                  {versions.map((v) => (
                    <button
                      key={v.id}
                      onClick={() => loadDetail(v)}
                      className={`w-full text-left p-2 rounded-md text-sm hover:bg-accent transition-colors ${
                        selectedVersion?.id === v.id ? 'bg-accent' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">v{v.version_number}</span>
                        <ChevronRight className="size-3.5 text-muted-foreground" />
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {new Date(v.created_at!).toLocaleString('zh-CN')}
                      </div>
                      {v.changed_fields.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {v.changed_fields.map((f) => (
                            <Badge key={f} variant="secondary" className="text-[10px] px-1 py-0">
                              {FIELD_LABELS[f] || f}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Snapshot detail */}
          <div className="border rounded-md p-3">
            <div className="h-[360px] overflow-y-auto">
              {selectedVersion ? (
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold">
                    v{selectedVersion.version_number} 快照
                  </h4>
                  {Object.entries(selectedVersion.snapshot).map(([key, val]) => (
                    <div key={key} className="text-xs">
                      <span className="text-muted-foreground">{FIELD_LABELS[key] || key}:</span>
                      <div className="mt-0.5 text-sm break-words">
                        {typeof val === 'string' ? val || '-' : JSON.stringify(val)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                  {loading ? '加载中...' : '选择左侧版本查看快照'}
                </div>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
