import { useNavigate } from 'react-router'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { Button } from '@/ui'

export default function NotFound() {
  useDocumentTitle('页面不存在')
  const navigate = useNavigate()
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="text-6xl font-bold text-muted-foreground/40">404</div>
      <h2 className="mt-4 text-lg font-semibold">页面不存在</h2>
      <p className="mt-2 text-sm text-muted-foreground">您访问的页面不存在或已被移动。</p>
      <Button className="mt-6" onClick={() => navigate('/workbench')}>返回工作台</Button>
    </div>
  )
}
