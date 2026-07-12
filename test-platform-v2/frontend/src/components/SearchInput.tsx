import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search, XCircle } from '@/lib/icons'
import { cn } from '@/lib/utils'

interface SearchInputProps {
  value: string
  onChange: (value: string) => void
  onSearch?: () => void
  placeholder?: string
  showButton?: boolean
  buttonText?: string
  inputClassName?: string
  clearable?: boolean
}

export default function SearchInput({
  value,
  onChange,
  onSearch,
  placeholder = '搜索...',
  showButton = true,
  buttonText = '搜索',
  inputClassName,
  clearable,
}: SearchInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && onSearch) onSearch()
  }

  return (
    <div className="flex items-center gap-1">
      <div className="relative">
        <Input
          aria-label="搜索"
          placeholder={placeholder}
          className={cn(inputClassName)}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        {clearable && value && (
          <button
            type="button"
            aria-label="清除搜索"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            onClick={() => onChange('')}
          >
            <XCircle className="size-4" />
          </button>
        )}
      </div>
      {showButton && (
        <Button variant="outline" size="sm" onClick={onSearch} data-icon="inline-start">
          <Search />
          {buttonText}
        </Button>
      )}
    </div>
  )
}
