import { Button } from '@/ui'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group'
import { Search, RotateCcw, Plus, Upload, Download } from '@/lib/icons'
import { groupDomainLabel } from '@/utils/domainNaming'

const ALL_FILTER = '__all__'

interface CaseFilterBarProps {
  taxonomy: any[]
  groupedTaxonomyDomains: { group: string; items: any[] }[]
  selModules: any[]
  selSurface: string
  setSelSurface: (v: string) => void
  selDomain: string
  setSelDomain: (v: string) => void
  selModule: string
  setSelModule: (v: string) => void
  setSelDirect: (v: boolean) => void
  caseNature: string
  setCaseNature: (v: string) => void
  priority: string
  setPriority: (v: string) => void
  keywordInput: string
  setKeywordInput: (v: string) => void
  keyword: string
  setKeyword: (v: string) => void
  setPage: (page: number) => void
  refetch: () => void
  canCreate: boolean
  importing: boolean
  importInputRef: React.RefObject<HTMLInputElement | null>
  onImportFile: (file: File | undefined) => void
  onExport: (format: 'excel' | 'xmind') => void
  onNewCase: () => void
}

export default function CaseFilterBar({
  taxonomy,
  groupedTaxonomyDomains,
  selModules,
  selSurface,
  setSelSurface,
  selDomain,
  setSelDomain,
  selModule,
  setSelModule,
  setSelDirect,
  caseNature,
  setCaseNature,
  priority,
  setPriority,
  keywordInput,
  setKeywordInput,
  keyword,
  setKeyword,
  setPage,
  refetch,
  canCreate,
  importing,
  importInputRef,
  onImportFile,
  onExport,
  onNewCase,
}: CaseFilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 shrink-0">
      <Select value={selSurface || ALL_FILTER} onValueChange={(v) => {
        setSelSurface(v === ALL_FILTER ? '' : v)
        setSelDomain('')
        setSelModule('')
        setSelDirect(false)
        setPage(1)
      }}>
        <SelectTrigger className="w-full sm:w-[120px]" size="sm" aria-label="按产品界面筛选">
          <SelectValue placeholder="全部界面" />
        </SelectTrigger>
        <SelectContent position="popper">
          <SelectItem value={ALL_FILTER}>全部界面</SelectItem>
          {taxonomy.map((item) => (
            <SelectItem key={item.surface} value={item.surface}>{item.surface} ({item.count})</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select disabled={!selSurface} value={selDomain || ALL_FILTER} onValueChange={(v) => {
        setSelDomain(v === ALL_FILTER ? '' : v)
        setSelModule('')
        setSelDirect(false)
        setPage(1)
      }}>
        <SelectTrigger className="w-full sm:w-[150px]" size="sm" aria-label="按业务模块筛选">
          <SelectValue placeholder={selSurface ? '全部业务模块' : '先选界面'} />
        </SelectTrigger>
        <SelectContent position="popper">
          <SelectItem value={ALL_FILTER}>全部业务模块</SelectItem>
          {groupedTaxonomyDomains.map(({ group, items }) => (
            <SelectGroup key={group}>
              <SelectLabel>{group}</SelectLabel>
              {items.map((d) => (
                <SelectItem key={d.domain} value={d.domain}>
                  {groupDomainLabel(d.domain).label}
                </SelectItem>
              ))}
            </SelectGroup>
          ))}
        </SelectContent>
      </Select>

      <Select disabled={!selDomain} value={selModule || ALL_FILTER} onValueChange={(v) => { setSelModule(v === ALL_FILTER ? '' : v); setSelDirect(false); setPage(1) }}>
        <SelectTrigger className="w-full sm:w-[170px]" size="sm" aria-label="按子模块筛选">
          <SelectValue placeholder={selDomain ? '全部子模块' : '先选业务模块'} />
        </SelectTrigger>
        <SelectContent position="popper">
          <SelectItem value={ALL_FILTER}>全部子模块</SelectItem>
          {selModules.map((m: any) => (
            <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={caseNature || ALL_FILTER} onValueChange={(v) => { setCaseNature(v === ALL_FILTER ? '' : v); setPage(1) }}>
        <SelectTrigger className="w-full sm:w-[110px]" size="sm" aria-label="按用例场景筛选">
          <SelectValue placeholder="全部场景" />
        </SelectTrigger>
        <SelectContent position="popper">
          <SelectItem value={ALL_FILTER}>全部场景</SelectItem>
          <SelectItem value="positive">正向</SelectItem>
          <SelectItem value="negative">负向</SelectItem>
          <SelectItem value="boundary">边界</SelectItem>
        </SelectContent>
      </Select>

      <Select value={priority || ALL_FILTER} onValueChange={(v) => { setPriority(v === ALL_FILTER ? '' : v); setPage(1) }}>
        <SelectTrigger className="w-full sm:w-[100px]" size="sm" aria-label="按用例优先级筛选">
          <SelectValue placeholder="全部优先级" />
        </SelectTrigger>
        <SelectContent position="popper">
          <SelectItem value={ALL_FILTER}>全部优先级</SelectItem>
          {['P0', 'P1', 'P2', 'P3'].map((v) => (
            <SelectItem key={v} value={v}>{v}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <InputGroup className="w-full sm:w-[240px]">
        <InputGroupAddon>
          <Search className="size-3.5" />
        </InputGroupAddon>
        <InputGroupInput
          placeholder="搜索标题/关键字"
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              const nextKeyword = keywordInput.trim()
              setPage(1)
              if (nextKeyword === keyword) refetch()
              else setKeyword(nextKeyword)
            }
          }}
        />
      </InputGroup>

      <Button size="sm" onClick={() => {
        const nextKeyword = keywordInput.trim()
        setPage(1)
        if (nextKeyword === keyword) refetch()
        else setKeyword(nextKeyword)
      }}>
        <Search className="size-3.5" data-icon="inline-start" />
        搜索
      </Button>
      <Button size="sm" variant="secondary" onClick={() => {
        setSelSurface(''); setSelDomain(''); setSelModule(''); setCaseNature(''); setPriority(''); setKeywordInput(''); setKeyword(''); setPage(1)
      }}>
        <RotateCcw className="size-3.5" data-icon="inline-start" />
        重置
      </Button>
      {(selSurface || selDomain || selModule || caseNature || priority) && (
        <p className="w-full text-xs text-muted-foreground">当前搜索在已选筛选（界面/域/模块/性质/优先级）内生效</p>
      )}
      <div className="hidden flex-1 sm:block" />
      {canCreate && (
        <>
          <input
            ref={importInputRef}
            type="file"
            accept=".xlsx,.xmind"
            className="hidden"
            aria-label="导入用例文件"
            onChange={(e) => onImportFile(e.target.files?.[0])}
          />
          <Button size="sm" variant="secondary" disabled={importing} onClick={() => importInputRef.current?.click()}>
            <Upload className="size-3.5" data-icon="inline-start" />
            {importing ? '导入中...' : '导入'}
          </Button>
        </>
      )}
      <Button size="sm" variant="ghost" onClick={() => onExport('excel')}>
        <Download className="size-3.5" data-icon="inline-start" />
        导出 Excel
      </Button>
      <Button size="sm" variant="ghost" onClick={() => onExport('xmind')}>
        <Download className="size-3.5" data-icon="inline-start" />
        导出 XMind
      </Button>
      {canCreate && (
        <Button size="sm" className="w-full sm:w-auto" onClick={onNewCase}>
          <Plus className="size-3.5" data-icon="inline-start" />
          新建用例
        </Button>
      )}
    </div>
  )
}
