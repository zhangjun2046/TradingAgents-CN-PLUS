/**
 * 岗位结论卡展示辅助纯函数（可单测，不依赖 Vue 运行时）。
 *
 * 从 RoleConclusionCard.vue 抽离，保证头像首字、图表标题去重、
 * 条形宽度这些展示规则集中且可验证。
 */

/** 头像首字：空角色名回退「岗」 */
export function roleInitial(roleName: string): string {
  return roleName.trim().charAt(0) || '岗'
}

/**
 * 图表标题是否显示：只在有值、且与表格标题不同时显示，
 * 避免同一信息在卡上出现两次。
 */
export function shouldShowChartTitle(title: string, tableCaption?: string | null): boolean {
  if (!title) return false
  return title !== (tableCaption ?? '')
}

/** 所有序列样本里绝对值最大的值，用作条形宽度基准 */
export function maxAbsValue(items?: Array<{ values: number[] }>): number {
  return (items ?? [])
    .flatMap((item) => item.values)
    .reduce((max, value) => Math.max(max, Math.abs(value)), 0)
}

/** 数值相对最大值的条形宽度（百分比）；基准非正时回退 0% */
export function barWidthFor(value: number, maxValue: number): string {
  if (maxValue <= 0) return '0%'
  const ratio = Math.min(1, Math.abs(value) / maxValue)
  return `${ratio * 100}%`
}