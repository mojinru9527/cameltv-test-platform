/**
 * @ui — CamelTv 语义 UI 系统入口
 *
 * 业务页面唯一导入来源。禁止从 @/components/ui 或 @radix-ui/* 直接导入。
 *
 * @example
 * ```tsx
 * import { PageShell, DataTable, StatusBadge, Inspector, ui } from '@/ui'
 * ```
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

// ── 基础适配器（会逐步替换 @/components/ui/*） ──
// 当前阶段：通过 re-export 提供过渡兼容
export { Button } from './primitives/Button'
export { Input } from './primitives/Input'
export { Badge, type BadgeTone } from './primitives/Badge'
export { Progress } from './primitives/Progress'
export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './primitives/Card'
export { Textarea } from './primitives/Textarea'
export { Label } from './primitives/Label'
export { Select } from './primitives/Select'
export { Skeleton } from './primitives/Skeleton'

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
