import { FileText, Users, Shield } from '@/lib/icons'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/PageHeader'
import AuditTab from './AuditTab'
import RolesTab from './RolesTab'
import UsersTab from './UsersTab'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export default function SystemPage() {
  useDocumentTitle('系统管理')
  const hasPerm = useAuthStore((s) => s.hasPerm)

  const showUsers = hasPerm('system:user:list')
  const showRoles = hasPerm('system:role:list')
  const showAudit = hasPerm('system:audit:list')

  const defaultTab = showUsers ? 'users' : showRoles ? 'roles' : showAudit ? 'audit' : 'users'

  return (
    <div>
      <PageHeader title="系统管理" className="mb-4" />
      <Tabs defaultValue={defaultTab}>
        <TabsList>
          {showUsers && (
            <TabsTrigger value="users">
              <Users className="size-4" />
              用户管理
            </TabsTrigger>
          )}
          {showRoles && (
            <TabsTrigger value="roles">
              <Shield className="size-4" />
              角色管理
            </TabsTrigger>
          )}
          {showAudit && (
            <TabsTrigger value="audit">
              <FileText className="size-4" />
              审计日志
            </TabsTrigger>
          )}
        </TabsList>
        {showUsers && (
          <TabsContent value="users">
            <UsersTab />
          </TabsContent>
        )}
        {showRoles && (
          <TabsContent value="roles">
            <RolesTab />
          </TabsContent>
        )}
        {showAudit && (
          <TabsContent value="audit">
            <AuditTab />
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}
