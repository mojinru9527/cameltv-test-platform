import { useState } from 'react'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { FlaskConical, FileText, FolderTree, ClipboardCheck } from '@/lib/icons'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import PageHeader from '@/components/PageHeader'
import AssetTab from './components/AssetTab'
import DebugTab from './components/DebugTab'
import ApiCaseTab from './components/ApiCaseTab'
import TaskTab from './components/TaskTab'
import ImportDialog from './components/ImportDialog'
import type { ApiEndpoint } from '@/types'

export default function ApiTestPage() {
  useDocumentTitle('API 测试')
  const [activeTab, setActiveTab] = useState('quick')
  const [importOpen, setImportOpen] = useState(false)
  const [debugEndpoint, setDebugEndpoint] = useState<ApiEndpoint | null>(null)
  const [importRefreshKey, setImportRefreshKey] = useState(0)

  const handleDebugEndpoint = (ep: ApiEndpoint) => {
    setDebugEndpoint(ep)
    setActiveTab('quick')
  }

  const handleImported = () => {
    setImportRefreshKey(k => k + 1)
  }

  return (
    <div className="space-y-4">
      <PageHeader title="接口测试" description="接口资产导入、用例生成、调试执行、批量任务。">
        <ImportDialog
          open={importOpen}
          onClose={() => setImportOpen(false)}
          onImported={handleImported}
        />
      </PageHeader>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="assets">
            <FolderTree className="size-4 mr-1" />
            接口资产
          </TabsTrigger>
          <TabsTrigger value="quick">
            <FlaskConical className="size-4 mr-1" />
            快速调试
          </TabsTrigger>
          <TabsTrigger value="cases">
            <FileText className="size-4 mr-1" />
            接口用例
          </TabsTrigger>
          <TabsTrigger value="tasks">
            <ClipboardCheck className="size-4 mr-1" />
            执行任务
          </TabsTrigger>
        </TabsList>

        <TabsContent value="assets" className="mt-4">
          <AssetTab
            onDebugEndpoint={handleDebugEndpoint}
            onOpenImport={() => setImportOpen(true)}
            refreshKey={importRefreshKey}
          />
        </TabsContent>

        <TabsContent value="quick" className="mt-4">
          <DebugTab />
        </TabsContent>

        <TabsContent value="cases" className="mt-4">
          <ApiCaseTab />
        </TabsContent>

        <TabsContent value="tasks" className="mt-4">
          <TaskTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
