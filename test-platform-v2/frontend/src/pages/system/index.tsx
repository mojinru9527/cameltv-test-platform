import { FileText, Users, Shield, KeyRound } from '@/lib/icons'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/PageHeader'
import AuditTab from './AuditTab'
import RolesTab from './RolesTab'
import UsersTab from './UsersTab'
import TokensTab from './TokensTab'
import InviteCodesTab from './InviteCodesTab'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { useSearchParams } from 'react-router'

export default function SystemPage() {
  useDocumentTitle('系统管理')
  const hasPerm = useAuthStore((s) => s.hasPerm)

  const showUsers = hasPerm('system:user:list')
  const showRoles = hasPerm('system:role:list')
  const showAudit = hasPerm('system:audit:list')
  const showTokens = hasPerm('token:list')
  const showInvites = hasPerm('system:invite:manage')
  const [searchParams, setSearchParams] = useSearchParams()

  const defaultTab = showUsers
    ? 'users'
    : showRoles
      ? 'roles'
      : showAudit
        ? 'audit'
        : showTokens
          ? 'tokens'
          : showInvites
            ? 'invites'
            : 'users'

  const availableTabs = [
    showUsers && 'users',
    showRoles && 'roles',
    showAudit && 'audit',
    showTokens && 'tokens',
    showInvites && 'invites',
  ].filter(Boolean) as string[]
  const requestedTab = searchParams.get('tab')
  const activeTab = requestedTab && availableTabs.includes(requestedTab)
    ? requestedTab
    : defaultTab

  function changeTab(value: string) {
    const next = new URLSearchParams(searchParams)
    next.set('tab', value)
    if (value !== 'tokens') next.delete('purpose')
    setSearchParams(next, { replace: true })
  }

  return (
    <div>
      <PageHeader title="系统管理" className="mb-4" />
      <Tabs value={activeTab} onValueChange={changeTab}>
        <TabsList className="w-full flex-wrap justify-start group-data-[orientation=horizontal]/tabs:h-auto lg:w-fit lg:flex-nowrap lg:group-data-[orientation=horizontal]/tabs:h-8">
          {showUsers && (
            <TabsTrigger value="users" className="h-11 flex-none lg:h-[calc(100%-1px)] lg:flex-1">
              <Users className="size-4" />
              用户管理
            </TabsTrigger>
          )}
          {showRoles && (
            <TabsTrigger value="roles" className="h-11 flex-none lg:h-[calc(100%-1px)] lg:flex-1">
              <Shield className="size-4" />
              角色管理
            </TabsTrigger>
          )}
          {showAudit && (
            <TabsTrigger value="audit" className="h-11 flex-none lg:h-[calc(100%-1px)] lg:flex-1">
              <FileText className="size-4" />
              审计日志
            </TabsTrigger>
          )}
          {showTokens && (
            <TabsTrigger value="tokens" className="h-11 flex-none lg:h-[calc(100%-1px)] lg:flex-1">
              <KeyRound className="size-4" />
              API Token
            </TabsTrigger>
          )}
          {showInvites && (
            <TabsTrigger value="invites" className="h-11 flex-none lg:h-[calc(100%-1px)] lg:flex-1">
              <KeyRound className="size-4" />
              邀请码
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
        {showTokens && (
          <TabsContent value="tokens">
            <TokensTab />
          </TabsContent>
        )}
        {showInvites && (
          <TabsContent value="invites">
            <InviteCodesTab />
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}
