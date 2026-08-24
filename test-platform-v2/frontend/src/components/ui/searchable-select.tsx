// Batch 178（FIX-173-P2-03）：可搜索下拉选择器（基于 cmdk）。
// 用于 100+ 项的域/模块选择——原 shadcn Select 不支持搜索，大数据集下无法定位。
import * as React from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { cn } from '@/lib/utils'

export interface SearchableOption {
  value: string
  label: string
  group?: string
}

interface SearchableSelectProps {
  value?: string
  onValueChange: (value: string) => void
  options: SearchableOption[]
  placeholder?: string
  emptyText?: string
  triggerId?: string
  disabled?: boolean
}

function groupOf(option: SearchableOption, hasGroups: boolean): string {
  return hasGroups ? (option.group || '其他') : ''
}

/**
 * 可搜索下拉：输入过滤 + 按 group 分组展示。
 * 行为与 shadcn Select 对齐（onValueChange 传原始 value）。
 */
export function SearchableSelect({
  value,
  onValueChange,
  options,
  placeholder = '请选择',
  emptyText = '无匹配选项',
  triggerId,
  disabled,
}: SearchableSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')
  const hasGroups = options.some((o) => Boolean(o.group))

  const selected = options.find((o) => o.value === value)

  // 按 group 分组（保持选项原顺序）
  const groups = React.useMemo(() => {
    const map = new Map<string, SearchableOption[]>()
    for (const opt of options) {
      const g = groupOf(opt, hasGroups)
      if (!map.has(g)) map.set(g, [])
      map.get(g)!.push(opt)
    }
    return Array.from(map.entries())
  }, [options, hasGroups])

  return (
    <Popover open={open} onOpenChange={(o) => { setOpen(o); if (!o) setSearch('') }}>
      <PopoverTrigger asChild>
        <Button
          id={triggerId}
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className="w-full justify-between font-normal"
          size="sm"
        >
          <span className="truncate">{selected ? selected.label : placeholder}</span>
          <ChevronsUpDown className="size-3.5 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={`搜索${placeholder}…`}
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>{emptyText}</CommandEmpty>
            {groups.map(([group, opts]) => {
              const filtered = search
                ? opts.filter((o) => o.label.toLowerCase().includes(search.toLowerCase()))
                : opts
              if (filtered.length === 0) return null
              return (
                <CommandGroup key={group || '__root__'} heading={group || undefined}>
                  {filtered.map((opt) => (
                    <CommandItem
                      key={opt.value}
                      value={opt.value}
                      onSelect={(v) => {
                        onValueChange(v)
                        setOpen(false)
                        setSearch('')
                      }}
                      data-checked={opt.value === value}
                    >
                      <Check
                        className={cn('size-4', opt.value === value ? 'opacity-100' : 'opacity-0')}
                      />
                      {opt.label}
                    </CommandItem>
                  ))}
                </CommandGroup>
              )
            })}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
