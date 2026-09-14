/**
 * @ui — CamelTv 语义 UI 系统入口
 *
 * 业务页面唯一导入来源。禁止从 @/components/ui 或 @radix-ui/* 直接导入。
 *
 * `components/ui` 仍是 canonical shadcn 实现；本入口负责聚合导出和少量
 * legacy API 兼容适配，避免业务页面同时依赖两套入口。
 */

// ── 主题 Provider ──
export { UiThemeProvider, useUiTheme, type UiThemeId } from './themes/UiThemeProvider'

// ── Hooks ──
export { useObsidianPage } from './hooks/useObsidianPage'

// ── 主题注册表 ──
export {
  type ThemeDefinition,
  UI_THEMES,
  getUiTheme,
  getDefaultUiTheme,
} from './themes/registry'

// ── Canonical shadcn / Radix 组件聚合入口 ──
export * from '@/components/ui/alert'
export * from '@/components/ui/alert-dialog'
export * from '@/components/ui/avatar'
export * from '@/components/ui/checkbox'
export * from '@/components/ui/collapsible'
export * from '@/components/ui/command'
export * from '@/components/ui/dialog'
export * from '@/components/ui/dropdown-menu'
export * from '@/components/ui/input-group'
export * from '@/components/ui/popover'
export * from '@/components/ui/scroll-area'
export * from '@/components/ui/searchable-select'
export * from '@/components/ui/separator'
export * from '@/components/ui/sheet'
export * from '@/components/ui/sidebar'
export * from '@/components/ui/sonner'
export * from '@/components/ui/switch'
export * from '@/components/ui/table'
export * from '@/components/ui/tabs'
export * from '@/components/ui/tooltip'

// ── 基础适配器（canonical 实现 + legacy API 兼容）──
export { Button, buttonVariants, type ButtonProps, type ButtonSize, type ButtonVariant } from './primitives/Button'
export { Input, type InputProps } from './primitives/Input'
export {
  Badge,
  badgeVariants,
  type BadgeProps,
  type BadgeTone,
  type BadgeVariant,
} from './primitives/Badge'
export { Progress, type ProgressProps, type ProgressTone } from './primitives/Progress'
export { Card, CardAction, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './primitives/Card'
export { Textarea } from './primitives/Textarea'
export { Label } from './primitives/Label'
export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectScrollDownButton,
  SelectScrollUpButton,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from './primitives/Select'
export { Skeleton, SkeletonCard, SkeletonCircle, SkeletonPage, SkeletonTable, SkeletonText } from './primitives/Skeleton'

// ── 页面模式 ──
export { ObsidianWorkbench, type ObsidianWorkbenchProps, type WorkbenchMetric } from './patterns/ObsidianWorkbench'
export { ObsidianListPage, type ObsidianListPageProps } from './patterns/ObsidianListPage'
export { Inspector, type InspectorProps } from './patterns/Inspector'

// ── 语义组件 ──
export { StatusBadge, type StatusVariant, type SeverityVariant } from './components/StatusBadge'
export { PageShell } from './components/PageShell'
export { MetricStrip } from './components/MetricStrip'
export { SpatialChain, type SpatialChainProps, type ChainNode } from './components/SpatialChain'

// ── 工具：合并 className ──
export { cn } from '@/lib/utils'
