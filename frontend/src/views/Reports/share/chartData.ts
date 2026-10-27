/**
 * 分享页概览图表数据派生（纯函数，可单测，不依赖 Vue 运行时）。
 *
 * 数据来源：
 * - 置信度 / 风险 / 投资建议 直接用后端公开字段（confidence_score / risk_level /
 *   decision.action / recommendation），与正文结论天然一致；
 * - 决策链 / 多空对比 复用 P4.2 的正文观点提取 `extractRoleView`，
 *   保证与各岗位结论卡观点一致。
 */
import { OVERVIEW_DEPT_KEY, type VisibleDept } from './shareConfig'
import type { SharedReport } from './types'
import { extractRoleView, type Stance } from '@/utils/reportConclusion'

/** 观点明确（看多 / 看空 / 中性）的 stance，决策链只串联这类岗位 */
export type DecidedStance = Exclude<Stance, 'unknown'>

/**
 * 置信度归一化为 0-100 的整数。后端可能给 0-1 或 0-100，
 * 统一按「≤1 视为 0-1」换算；非法值回退 0。
 */
export function normalizeConfidence(score: unknown): number {
  const value = Number(score)
  if (!Number.isFinite(value)) return 0
  const normalized = value <= 1 ? value * 100 : value
  return Math.max(0, Math.min(100, Math.round(normalized)))
}

export type RiskTone = 'low' | 'medium' | 'high' | 'unknown'

export interface RiskInfo {
  label: string
  tone: RiskTone
}

/**
 * 风险等级文案与色彩键映射，容错「低 / 中 / 中等 / 高 / 高风险」等取值。
 * 未知值兜底为「中等」文案 + 灰。
 */
export function riskLevelInfo(risk: unknown): RiskInfo {
  const text = typeof risk === 'string' ? risk.trim() : ''
  if (text.includes('低')) return { label: text, tone: 'low' }
  if (text.includes('高')) return { label: text, tone: 'high' }
  if (text.includes('中')) return { label: text, tone: 'medium' }
  return { label: text || '中等', tone: 'unknown' }
}

export interface SuggestResult {
  /** 展示文案：决策动作或一句话结论 */
  text: string
  tone: Stance
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

export interface ChainNode {
  key: string
  name: string
  tab: string
  role: string
  stance: DecidedStance
}

/**
 * 决策链：按可见部门顺序（分析部 → 研究部 → 交易部 → 风控部 → 其他），
 * 对每个岗位正文提取观点，只保留观点明确的岗位，供标签条点击跳转。
 */
export function buildDecisionChain(departments: VisibleDept[]): ChainNode[] {
  const nodes: ChainNode[] = []
  for (const dept of departments) {
    if (dept.key === OVERVIEW_DEPT_KEY) continue
    for (const role of dept.roles) {
      if (typeof role.content !== 'string') continue
      const { conclusion } = extractRoleView(role.content)
      if (conclusion.stance === 'unknown') continue
      nodes.push({
        key: role.key,
        name: role.name,
        tab: dept.key,
        role: role.key,
        stance: conclusion.stance,
      })
    }
  }
  return nodes
}

export interface BullBearSide {
  key: string
  name: string
  tab: string
  role: string
  stance: Stance
  sentence: string
}

export interface BullBear {
  bull: BullBearSide | null
  bear: BullBearSide | null
}

/**
 * 多空对比：从研究部取「多头研究员 / 空头研究员」两个岗位，
 * 展示各自观点与一句话结论；任一侧无正文时为 null。
 */
export function buildBullBear(departments: VisibleDept[]): BullBear {
  const research = departments.find((dept) => dept.key === 'research')
  const side = (key: 'bull' | 'bear'): BullBearSide | null => {
    const role = research?.roles.find((item) => item.key === key)
    if (!role || typeof role.content !== 'string') return null
    const { conclusion } = extractRoleView(role.content)
    return {
      key,
      name: role.name,
      tab: 'research',
      role: key,
      stance: conclusion.stance,
      sentence: conclusion.sentence,
    }
  }
  return { bull: side('bull'), bear: side('bear') }
}