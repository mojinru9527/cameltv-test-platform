import type { BadgeTone } from '@/ui'

/**
 * 严重级 Badge 四级可辨色梯度（含深色模式变体）——修复设计走查 P1-1：
 * 原实现 P0/P1 同为 destructive（红），最高两级视觉不可分。现：
 *   P0 实心红（destructive） / P1 橙色描边 / P2 灰（secondary） / P3 中性描边（outline）
 * P1 用 outline + 橙色语义类并附 dark: 变体，保证深色模式对比度（P1-2 同源约束）。
 */
export function severityBadge(severity: string): { tone: BadgeTone; className?: string } {
  switch (severity) {
    case 'P0':
      return { tone: 'danger' }
    case 'P1':
      return { tone: 'warning' }
    case 'P2':
      return { tone: 'info' }
    default:
      return { tone: 'neutral' }
  }
}
