import { describe, expect, it } from 'vitest'
import {
  FINAL_CHAIN_KEY,
  buildDecisionChain,
  confidenceColor,
  confidenceLabel,
  confidenceLabelColor,
  formatSuggestBanner,
  normalizeConfidence,
  riskDisplayLabel,
  riskHint,
  riskLevelInfo,
  suggestAction
} from '../chartData'
import { buildVisibleDepartments } from '../shareConfig'
import type { SharedReport } from '../types'
import { normalizeConfidenceScore, resolveRiskLevel } from '@/utils/reportMetrics'

describe('normalizeConfidence', () => {
  it('0-1 归一化为 0-100', () => {
    expect(normalizeConfidence(0.65)).toBe(65)
    expect(normalizeConfidence(1)).toBe(100)
    expect(normalizeConfidence(0)).toBe(0)
  })

  it('0-100 直接取整', () => {
    expect(normalizeConfidence(65)).toBe(65)
    expect(normalizeConfidence(100)).toBe(100)
  })

  it('越界夹紧到 0-100', () => {
    expect(normalizeConfidence(150)).toBe(100)
    expect(normalizeConfidence(-5)).toBe(0)
  })

  it('非法值回退 0', () => {
    expect(normalizeConfidence(undefined)).toBe(0)
    expect(normalizeConfidence(null)).toBe(0)
    expect(normalizeConfidence('abc')).toBe(0)
  })

  it('与 PC 报告详情共用同一整数分', () => {
    for (const score of [0, 0.75, 1, 1.5, 75, 82, 100, 150, -5, undefined, null, 'abc']) {
      expect(normalizeConfidence(score)).toBe(normalizeConfidenceScore(score))
    }
  })
})

describe('confidenceLabel', () => {
  it('按与 PC 相同的分数档返回高/中/低置信度', () => {
    expect(confidenceLabel(82)).toBe('高置信度')
    expect(confidenceLabel(80)).toBe('高置信度')
    expect(confidenceLabel(60)).toBe('中置信度')
    expect(confidenceLabel(40)).toBe('中置信度')
    expect(confidenceLabel(39)).toBe('低置信度')
    expect(confidenceLabel(0)).toBe('低置信度')
  })
})

describe('confidenceColor', () => {
  it('色带与 PC 报告详情一致', () => {
    expect(confidenceColor(82)).toBe('#22A85C')
    expect(confidenceColor(75)).toBe('#409EFF')
    expect(confidenceColor(60)).toBe('#409EFF')
    expect(confidenceColor(40)).toBe('#E6A23C')
    expect(confidenceColor(39)).toBe('#F56C6C')
    expect(confidenceLabelColor(82)).toBe('#178A45')
    expect(confidenceLabelColor(75)).toBe('#1D6FD8')
  })
})

describe('riskLevelInfo', () => {
  it('五档与 PC 星级、颜色一致', () => {
    expect(riskLevelInfo('低')).toEqual({ label: '低', tone: 'low', level: 1, color: '#67C23A' })
    expect(riskLevelInfo('中低')).toEqual({
      label: '中低',
      tone: 'midLow',
      level: 2,
      color: '#95D475'
    })
    expect(riskLevelInfo('中等')).toEqual({
      label: '中等',
      tone: 'medium',
      level: 3,
      color: '#E6A23C'
    })
    expect(riskLevelInfo('中高')).toEqual({
      label: '中高',
      tone: 'midHigh',
      level: 4,
      color: '#F56C6C'
    })
    expect(riskLevelInfo('高')).toEqual({ label: '高', tone: 'high', level: 5, color: '#F56C6C' })
  })

  it('去掉「风险」后缀后再匹配，中低/中高不会被高低抢走', () => {
    expect(riskLevelInfo('高风险')).toEqual({
      label: '高',
      tone: 'high',
      level: 5,
      color: '#F56C6C'
    })
    expect(riskLevelInfo('中低风险')).toEqual({
      label: '中低',
      tone: 'midLow',
      level: 2,
      color: '#95D475'
    })
    expect(riskLevelInfo('中高风险')).toEqual({
      label: '中高',
      tone: 'midHigh',
      level: 4,
      color: '#F56C6C'
    })
  })

  it('空值按中等；无法识别的原文保留且星级颜色走默认', () => {
    const medium = { label: '中等', tone: 'medium', level: 3, color: '#E6A23C' }
    expect(riskLevelInfo('')).toEqual(medium)
    expect(riskLevelInfo(undefined)).toEqual(medium)
    expect(riskLevelInfo(null)).toEqual(medium)
    expect(riskLevelInfo('极高')).toEqual({
      label: '极高',
      tone: 'unknown',
      level: 3,
      color: '#E6A23C'
    })
  })

  it('展示等级、段数、颜色与 PC resolveRiskLevel 一致', () => {
    for (const risk of ['低', '中低', '中等', '中高', '高', '高风险', '中低风险', '中等风险', '', undefined, '极高', 123]) {
      const info = riskLevelInfo(risk)
      const pc = resolveRiskLevel(risk)
      expect(info.level).toBe(pc.level)
      expect(info.color).toBe(pc.color)
      expect(riskDisplayLabel(info)).toBe(pc.label)
    }
  })
})

describe('riskDisplayLabel / riskHint', () => {
  it('拼「等级风险」且不重复「风险」后缀', () => {
    expect(riskDisplayLabel({ label: '中等', tone: 'medium', level: 3, color: '#E6A23C' })).toBe(
      '中等风险'
    )
    expect(riskDisplayLabel({ label: '高', tone: 'high', level: 5, color: '#F56C6C' })).toBe(
      '高风险'
    )
    expect(riskDisplayLabel({ label: '低', tone: 'low', level: 1, color: '#67C23A' })).toBe(
      '低风险'
    )
    expect(riskDisplayLabel({ label: '中低', tone: 'midLow', level: 2, color: '#95D475' })).toBe(
      '中低风险'
    )
  })

  it('按 tone 返回副文案', () => {
    expect(riskHint('low')).toBe('波动相对可控')
    expect(riskHint('midLow')).toBe('波动相对可控')
    expect(riskHint('medium')).toBe('历史波动可控')
    expect(riskHint('midHigh')).toBe('波动与回撤需警惕')
    expect(riskHint('high')).toBe('波动与回撤需警惕')
    expect(riskHint('unknown')).toBe('')
  })
})

describe('suggestAction', () => {
  it('优先 decision.action，观点判定与岗位一致', () => {
    const report = {
      decision: { action: '维持买入评级' },
      recommendation: '建议持有'
    } as SharedReport
    const result = suggestAction(report)
    expect(result.text).toBe('维持买入评级')
    expect(result.tone).toBe('bullish')
  })

  it('decision.action 缺失时回退 recommendation', () => {
    const report = { recommendation: '建议减持。' } as SharedReport
    const result = suggestAction(report)
    expect(result.tone).toBe('bearish')
    expect(result.text).toBe('建议减持')
  })

  it('两者都缺失时为暂无', () => {
    expect(suggestAction({})).toEqual({ text: '暂无', tone: 'unknown' })
  })
})

describe('formatSuggestBanner', () => {
  it('拼主文案：观点 · 动作', () => {
    expect(formatSuggestBanner({ text: '买入/增持', tone: 'bullish' })).toEqual({
      title: '投资建议参考：看多 · 买入/增持'
    })
    expect(formatSuggestBanner({ text: '持有', tone: 'neutral' })).toEqual({
      title: '投资建议参考：中性 · 持有'
    })
  })
})

describe('buildDecisionChain', () => {
  const departments = buildVisibleDepartments({
    market_report: '结论：买入，目标价 20 元。',
    bull_researcher: '看多，理由充分。',
    bear_researcher: '看空，注意风险。',
    trader_investment_plan: '建议观望。'
  })

  it('无主席时按部门顺序串联，末尾追加投资决策；跳过多空与交易员', () => {
    const suggest = { text: '买入/增持', tone: 'bullish' as const }
    const chain = buildDecisionChain(departments, suggest)
    // 多头/空头/交易员有观点也不进链；本例无研究经理，故仅市场分析师 + 末节点
    expect(chain.map(node => node.role)).toEqual(['market', ''])
    expect(chain.some(node => ['bull', 'bear', 'trader'].includes(node.role))).toBe(false)
    expect(chain[0]).toMatchObject({
      name: '市场分析师',
      tab: 'analysts',
      stance: 'bullish',
      clickable: true
    })
    const last = chain[chain.length - 1]
    expect(last).toMatchObject({
      key: FINAL_CHAIN_KEY,
      name: '投资决策',
      stance: 'bullish',
      clickable: false
    })
  })

  it('只输出 showsStance=true 的正式表态岗位', () => {
    const withManager = buildVisibleDepartments({
      bull_researcher: '看多，理由充分。',
      bear_researcher: '看空，注意风险。',
      research_team_decision: '我的决定很明确：给出“卖出”建议。',
      trader_investment_plan: '建议观望。',
      risky_analyst: '激进观点：建议买入。',
      safe_analyst: '保守观点：建议卖出。',
      neutral_analyst: '中性观点：建议持有。'
    })
    const chain = buildDecisionChain(withManager, { text: '卖出', tone: 'bearish' })
    expect(chain.map(node => node.role)).toEqual(['manager', ''])
    expect(
      chain.some(node => ['bull', 'bear', 'trader', 'risky', 'safe', 'neutral'].includes(node.role))
    ).toBe(false)
    expect(chain[0]).toMatchObject({
      name: '研究经理',
      tab: 'research',
      role: 'manager',
      stance: 'bearish',
      clickable: true
    })
  })

  it('风险主席保留正文观点，末尾仍追加独立投资决策', () => {
    const withChair = buildVisibleDepartments({
      market_report: '结论：买入。',
      risk_management_decision: '最终裁决：建议持有，暂不买入或卖出。'
    })
    const chain = buildDecisionChain(withChair, { text: '卖出', tone: 'bearish' })
    expect(chain.map(node => node.role)).toEqual(['market', 'riskManager', ''])
    expect(chain[1]).toMatchObject({
      name: '风险管理委员会主席',
      role: 'riskManager',
      stance: 'neutral',
      clickable: true
    })
    expect(chain[2]).toMatchObject({
      key: FINAL_CHAIN_KEY,
      name: '投资决策',
      stance: 'bearish',
      clickable: false
    })
  })

  it('没有明确岗位时仍保留投资决策末节点', () => {
    const onlyText = buildVisibleDepartments({ market_report: '今日行情平稳，无明确建议。' })
    const chain = buildDecisionChain(onlyText, { text: '持有', tone: 'neutral' })
    expect(chain).toHaveLength(1)
    expect(chain[0].key).toBe(FINAL_CHAIN_KEY)
    expect(chain[0].stance).toBe('neutral')
  })

  it('空部门列表仍有投资决策末节点', () => {
    const chain = buildDecisionChain([])
    expect(chain).toHaveLength(1)
    expect(chain[0].key).toBe(FINAL_CHAIN_KEY)
    expect(chain[0].clickable).toBe(false)
  })
})
