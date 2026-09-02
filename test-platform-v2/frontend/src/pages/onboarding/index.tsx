import { useState } from 'react'
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, PageShell, Textarea } from '@/ui'
import { advanceOnboarding, createOnboarding, listOnboardings, type Onboarding } from '@/api/versionTask'
import { toast } from 'sonner'

/** B15 新业务接入 4 步向导：登记 → 接基线 → 生成方案 → 跑基线（30 分钟出基线）。 */
export default function OnboardingPage() {
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [serviceKey, setServiceKey] = useState('')
  const [apiSpec, setApiSpec] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [ob, setOb] = useState<Onboarding | null>(null)
  const [items, setItems] = useState<Onboarding[]>([])

  async function refreshList() {
    try { setItems(await listOnboardings()) } catch { /* ignore */ }
  }

  const STEPS = ['登记业务', '接基线', '生成方案', '跑基线']

  async function handleCreate() {
    if (!name.trim() || !serviceKey.trim()) { toast.error('请填写业务名与服务 key'); return }
    const created = await createOnboarding({ name: name.trim(), service_key: serviceKey.trim(), api_spec_url: apiSpec.trim(), base_url: baseUrl.trim() })
    setOb(created)
    setStep(2)
    toast.success('已登记，进入接基线')
    void refreshList()
  }

  async function advance() {
    if (!ob) return
    try {
      const next = await advanceOnboarding(ob.id, step === 1 ? 2 : step + 1)
      setOb(next)
      setStep(next.step)
      if (next.step === 4) toast.success('基线已生成')
      void refreshList()
    } catch (e) {
      toast.error((e as Error).message || '推进失败')
    }
  }

  return (
    <PageShell title="新业务接入">
      <Card>
        <CardHeader>
          <CardTitle>4 步接入向导</CardTitle>
          <CardDescription>30 分钟跑出业务基线（试点 basketball-service / camel-mimo）</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {STEPS.map((s, i) => (
              <div key={s} className="flex items-center gap-2">
                <Badge variant={step === i + 1 ? 'default' : 'secondary'}>{i + 1}</Badge><span>{s}</span>
                {i < 3 && <span>→</span>}
              </div>
            ))}
          </div>

          {step === 1 && (
            <div className="space-y-2">
              <Input placeholder="业务名" value={name} onChange={(e) => setName(e.target.value)} />
              <Input placeholder="服务 key（如 basketball-service）" value={serviceKey} onChange={(e) => setServiceKey(e.target.value)} />
              <Textarea placeholder="API Spec URL" value={apiSpec} onChange={(e) => setApiSpec(e.target.value)} />
              <Textarea placeholder="Base URL" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
              <Button variant="primary" onClick={handleCreate}>登记业务</Button>
            </div>
          )}

          {step > 1 && ob && (
            <div className="space-y-2">
              <p className="text-sm">当前：<Badge variant="secondary">{ob.name}</Badge> · 步骤 {ob.step}/4 · 状态 {ob.status}</p>
              <Button variant="primary" onClick={advance}>下一步（{STEPS[ob.step - 1] || '完成'}）</Button>
              {ob.step === 4 && <p className="text-xs text-muted-foreground">基线：{ob.baseline}</p>}
            </div>
          )}

          {items.length > 0 && (
            <div className="space-y-1">
              <h3 className="text-sm font-medium">已接入业务</h3>
              {items.map((it) => (
                <div key={it.id} className="flex items-center gap-2 rounded border p-2 text-sm">
                  <Badge variant="secondary">{it.service_key}</Badge>
                  <span>{it.name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">步骤 {it.step}/4 · {it.status}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </PageShell>
  )
}
