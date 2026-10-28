/**
 * 分享页概览图表数据派生（纯函数，可单测，不依赖 Vue 运行时）。
 *
 * 数据来源：
 * - 置信度 / 风险 / 投资建议 直接用后端公开字段（confidence_score / risk_level /
 *   decision.action / recommendation），与正文结论天然一致；
 * - 决策链复用 P4.2 的正文观点提取 `extractRoleView`，
 *   保证与各岗位结论卡观点一致。概览不展示多空对比。
 */
import { OVERVIEW_DEPT_KEY, type VisibleDept } from './shareConfig'
import type { SharedReport } from './types'
import { extractRoleView, STANCE_LABEL, type Stance } from '@/utils/reportConclusion'
import { normalizeConfidenceScore, resolveRiskLevel } from '@/utils/reportMetrics'

/** 观点明确（看多 / 看空 / 中性）的 stance，决策链岗位节点只串联这类 */
export type DecidedStance = Exclude<Stance, 'unknown'>

/** 决策链末节点固定 key，无对应岗位，不可点击跳转 */
export const FINAL_CHAIN_KEY = 'final'

/**
 * 置信度得分。与 PC 报告详情共用 `normalizeConfidenceScore`，保证两边整数分一致。
 */
export function normalizeConfidence(score: unknown): number {
  return normalizeConfidenceScore(score)
}

/** 置信度档位文案（原型：高/中/低置信度）。分档与 PC 色带对齐：80 / 60 / 40。 */
export function confidenceLabel(score: number): string {
  if (score >= 80) return '高置信度'
  if (score >= 40) return '中置信度'
  return '低置信度'
}

/**
 * 置信度环颜色，与 PC `ReportDetail.getConfidenceColor` 同一分档。
 * 高分用原型里的绿色，其余档用 PC 的蓝 / 橙 / 红。
 */
export function confidenceColor(score: number): string {
  if (score >= 80) return '#22A85C'
  if (score >= 60) return '#409EFF'
  if (score >= 40) return '#E6A23C'
  return '#F56C6C'
}

/** 环内档位字色：比环色更深，保证小字可读 */
export function confidenceLabelColor(score: number): string {
  if (score >= 80) return '#178A45'
  if (score >= 60) return '#1D6FD8'
  if (score >= 40) return '#C47E12'
  return '#D64545'
}

export type RiskTone = 'low' | 'midLow' | 'medium' | 'midHigh' | 'high' | 'unknown'

export interface RiskInfo {
  /** 等级原文，不含「风险」后缀 */
  label: string
  tone: RiskTone
  /** 1-5，与 PC `getRiskStars` 一致，从左起点亮这么多段 */
  level: number
  /** 与 PC `getRiskColor` 一致 */
  color: string
}

/** 风险条段数，对应五档：低 / 中低 / 中等 / 中高 / 高 */
export const RISK_SEGMENT_COUNT = 5

const RISK_TONE: Record<string, RiskTone> = {
  低: 'low',
  中低: 'midLow',
  中等: 'medium',
  中高: 'midHigh',
  高: 'high'
}

/**
 * 风险等级与 PC 报告详情共用 `resolveRiskLevel`。
 * 等级原文、点亮段数、颜色都从同一结果取出。
 */
export function riskLevelInfo(risk: unknown): RiskInfo {
  const resolved = resolveRiskLevel(risk)
  return {
    label: resolved.key,
    tone: RISK_TONE[resolved.key] ?? 'unknown',
    level: resolved.level,
    color: resolved.color
  }
}

/** 展示用「{等级}风险」，避免「高风险」再拼成「高风险风险」 */
export function riskDisplayLabel(info: RiskInfo): string {
  const base = info.label.replace(/风险$/, '').trim() || '中等'
  return `${base}风险`
}

/** 风险副文案（原型右侧说明） */
export function riskHint(tone: RiskTone): string {
  if (tone === 'low' || tone === 'midLow') return '波动相对可控'
  if (tone === 'medium') return '历史波动可控'
  if (tone === 'midHigh' || tone === 'high') return '波动与回撤需警惕'
  return ''
}

export interface SuggestResult {
  /** 展示文案：决策动作或一句话结论 */
  text: string
  tone: Stance
}

export interface SuggestBanner {
  title: string
}

const DEFAULT_SUGGEST: SuggestResult = { text: '暂无', tone: 'unknown' }

/**
 * 投资建议：优先 `decision.action`，缺失时回退 `recommendation` 首句，
 * 观点判定复用与岗位结论卡一致的 `extractRoleView`。
 */
export function suggestAction(report: SharedReport): SuggestResult {
  const action = report.decision?.action
  if (typeof action === 'string' && action.trim()) {
    const { conclusion } = extractRoleView(action)
    return { text: action.trim(), tone: conclusion.stance }
  }
  const recommendation = report.recommendation
  if (typeof recommendation === 'string' && recommendation.trim()) {
    const { conclusion } = extractRoleView(recommendation)
    return conclusion.stance === 'unknown'
      ? { text: recommendation.trim().slice(0, 60), tone: 'unknown' }
      : { text: conclusion.sentence || recommendation.trim().slice(0, 60), tone: conclusion.stance }
  }
  return DEFAULT_SUGGEST
}

/** 投资建议横幅主文案：投资建议参考：{观点} · {动作} */
export function formatSuggestBanner(suggest: SuggestResult): SuggestBanner {
  return {
    title: `投资建议参考：${STANCE_LABEL[suggest.tone]} · ${suggest.text}`
  }
}

export interface ChainNode {
  key: string
  name: string
  tab: string
  role: string
  stance: Stance
  /** 末节点「投资决策」不可跳转 */
  clickable: boolean
}

/**
 * 决策链只展示结论卡允许展示观点徽章的正式表态岗位。
 * 辩论席、交易员和风控分析师的 `showsStance` 均为 false，不进入链。
 */
export function buildDecisionChain(
  departments: VisibleDept[],
  suggest: SuggestResult = DEFAULT_SUGGEST
): ChainNode[] {
  const nodes: ChainNode[] = []
  for (const dept of departments) {
    if (dept.key === OVERVIEW_DEPT_KEY) continue
    for (const role of dept.roles) {
      if (!role.showsStance) continue
      if (typeof role.content !== 'string') continue
      const { conclusion } = extractRoleView(role.content)
      if (conclusion.stance === 'unknown') continue
      nodes.push({
        key: role.key,
        name: role.name,
        tab: dept.key,
        role: role.key,
        stance: conclusion.stance,
        clickable: true
      })
    }
  }
  // 风险主席代表风控正文观点；最终节点始终单独使用结构化 decision.action（suggest 优先来源）。
  nodes.push({
    key: FINAL_CHAIN_KEY,
    name: '投资决策',
    tab: '',
    role: '',
    stance: suggest.tone,
    clickable: false
  })
  return nodes
}
