import { useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import PageHeader from '@/components/PageHeader'
import {
  Button,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { createMission, MISSION_TYPE_LABELS } from '@/api/missions'

const STEPS = ['基本信息', '确认信息', '完成']

export default function CreateMissionPage() {
  useDocumentTitle('新建测试任务')
  const navigate = useNavigate()

  const [step, setStep] = useState(0)
  const [title, setTitle] = useState('')
  const [missionType, setMissionType] = useState('VERSION')
  const [versionLabel, setVersionLabel] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const canNext = step === 0 ? title.trim().length > 0 : true

  const submit = async () => {
    if (submitting) return
    setSubmitting(true)
    try {
      const created = await createMission({
        title: title.trim(),
        mission_type: missionType,
        version_label: versionLabel.trim() || null,
      })
      toast.success(`已创建任务 ${created.mission_key}`)
      navigate(`/missions/${created.id}/overview`, { replace: true })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败')
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4">
      <PageHeader title="新建测试任务" description="3 步创建 Mission" />

      <div className="flex items-center gap-2">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center gap-2 text-sm">
            <span
              className={`flex size-6 items-center justify-center rounded-full text-xs ${
                i <= step ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
              }`}
            >
              {i + 1}
            </span>
            <span className={i === step ? 'font-medium' : 'text-muted-foreground'}>{label}</span>
            {i < STEPS.length - 1 && <span className="text-muted-foreground">—</span>}
          </div>
        ))}
      </div>

      {step === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
            <CardDescription>任务名称、类型与版本标签</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="mission-title">任务名称</Label>
              <Input
                id="mission-title"
                placeholder="如：会员中心 V3.6"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="mission-type">任务类型</Label>
              <Select value={missionType} onValueChange={setMissionType}>
                <SelectTrigger id="mission-type" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(MISSION_TYPE_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="mission-version">版本标签</Label>
              <Input
                id="mission-version"
                placeholder="如：v3.6"
                value={versionLabel}
                onChange={(e) => setVersionLabel(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>确认信息</CardTitle>
            <CardDescription>确认后进入任务详情</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>
              <span className="text-muted-foreground">任务名称：</span>
              {title}
            </p>
            <p>
              <span className="text-muted-foreground">任务类型：</span>
              {MISSION_TYPE_LABELS[missionType] ?? missionType}
            </p>
            <p>
              <span className="text-muted-foreground">版本标签：</span>
              {versionLabel || '—'}
            </p>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-between">
        <Button variant="ghost" disabled={step === 0} onClick={() => setStep(step - 1)}>
          上一步
        </Button>
        {step < 1 ? (
          <Button disabled={!canNext} onClick={() => setStep(step + 1)}>
            下一步
          </Button>
        ) : (
          <Button disabled={submitting} onClick={submit}>
            {submitting ? '创建中…' : '创建任务'}
          </Button>
        )}
      </div>
    </div>
  )
}
