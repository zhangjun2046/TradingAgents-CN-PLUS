/**
 * PC 报告详情与移动端分享概览共用的置信度得分、风险等级。
 * 两边必须走这里，避免各写一套后数字或等级对不上。
 */

export interface ReportRiskLevel {
  /** 等级原文，不含「风险」后缀 */
  key: string
  /** 展示文案，如「中等风险」 */
  label: string
  /** 1-5，与原先五颗星一致；无法识别时为 3 */
  level: number
  color: string
}

const RISK_LEVELS: Record<string, { level: number; color: string }> = {
  低: { level: 1, color: '#67C23A' },
  中低: { level: 2, color: '#95D475' },
  中等: { level: 3, color: '#E6A23C' },
  中高: { level: 4, color: '#F56C6C' },
  高: { level: 5, color: '#F56C6C' }
}

/**
 * 置信度归一化为 0-100 的整数。
 * 大于 1 视为百分制，否则视为 0-1；非法值回退 0，结果夹紧到 0-100。
 */
export function normalizeConfidenceScore(score: unknown): number {
  const value = Number(score)
  if (!Number.isFinite(value)) return 0
  const percent = value > 1 ? Math.round(value) : Math.round(value * 100)
  return Math.max(0, Math.min(100, percent))
}

/** 空值、空白、0 按「中等」；其余先去掉末尾「风险」再匹配五档。 */
export function resolveRiskLevel(risk: unknown): ReportRiskLevel {
  const raw = riskSource(risk)
  const key = raw.replace(/风险$/, '').trim() || '中等'
  const known = RISK_LEVELS[key]
  if (known) {
    return { key, label: `${key}风险`, level: known.level, color: known.color }
  }
  return { key, label: `${key}风险`, level: 3, color: '#E6A23C' }
}

function riskSource(risk: unknown): string {
  if (typeof risk === 'string') {
    return risk.trim() || '中等'
  }
  if (typeof risk === 'number' && Number.isFinite(risk) && risk !== 0) {
    return String(risk)
  }
  return '中等'
}
