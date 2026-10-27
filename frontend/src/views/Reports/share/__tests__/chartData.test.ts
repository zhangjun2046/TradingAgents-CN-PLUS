import { describe, expect, it } from 'vitest'
import {
  buildBullBear,
  buildDecisionChain,
  normalizeConfidence,
  riskLevelInfo,
  suggestAction,
} from '../chartData'
import { buildVisibleDepartments } from '../shareConfig'
import type { SharedReport } from '../types'

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
})

describe('riskLevelInfo', () => {
  it('低 / 中 / 高 映射正确', () => {
    expect(riskLevelInfo('低')).toEqual({ label: '低', tone: 'low' })
    expect(riskLevelInfo('中等')).toEqual({ label: '中等', tone: 'medium' })
    expect(riskLevelInfo('高')).toEqual({ label: '高', tone: 'high' })
  })

  it('容错高风险 / 高风险等级等取值', () => {
    expect(riskLevelInfo('高风险')).toEqual({ label: '高风险', tone: 'high' })
    expect(riskLevelInfo('中风险')).toEqual({ label: '中风险', tone: 'medium' })
  })

  it('未知值兜底为中等文案 + 灰色', () => {
    expect(riskLevelInfo('')).toEqual({ label: '中等', tone: 'unknown' })
    expect(riskLevelInfo(undefined)).toEqual({ label: '中等', tone: 'unknown' })
    expect(riskLevelInfo(123)).toEqual({ label: '中等', tone: 'unknown' })
  })
})

describe('suggestAction', () => {
  it('优先 decision.action，观点判定与岗位一致', () => {
    const report = { decision: { action: '维持买入评级' }, recommendation: '建议持有' } as SharedReport
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

describe('buildDecisionChain', () => {
  const departments = buildVisibleDepartments({
    market_report: '结论：买入，目标价 20 元。',
    bull_researcher: '看多，理由充分。',
    bear_researcher: '看空，注意风险。',
    trader_investment_plan: '建议观望。',
  })

  it('按部门顺序串联观点明确的岗位，跳过概览与未识别岗位', () => {
    const chain = buildDecisionChain(departments)
    expect(chain.map((node) => node.role)).toEqual(['market', 'bull', 'bear', 'trader'])
    expect(chain[0]).toMatchObject({ name: '市场分析师', tab: 'analysts', stance: 'bullish' })
  })

  it('跳过没有明确观点的岗位', () => {
    const onlyText = buildVisibleDepartments({ market_report: '今日行情平稳，无明确建议。' })
    expect(buildDecisionChain(onlyText)).toEqual([])
  })

  it('空部门列表返回空数组', () => {
    expect(buildDecisionChain([])).toEqual([])
  })
})

describe('buildBullBear', () => {
  it('从研究部取多空两侧观点与一句话', () => {
    const departments = buildVisibleDepartments({
      bull_researcher: '结论：买入。',
      bear_researcher: '结论：卖出。',
    })
    const { bull, bear } = buildBullBear(departments)
    expect(bull?.stance).toBe('bullish')
    expect(bear?.stance).toBe('bearish')
    expect(bull?.role).toBe('bull')
    expect(bear?.role).toBe('bear')
  })

  it('任一侧无正文时为 null', () => {
    const onlyBull = buildVisibleDepartments({ bull_researcher: '结论：买入。' })
    expect(buildBullBear(onlyBull).bear).toBeNull()
    expect(buildBullBear(onlyBull).bull).not.toBeNull()
  })

  it('研究部缺失时两侧都为 null', () => {
    expect(buildBullBear(buildVisibleDepartments({ market_report: 'a' }))).toEqual({
      bull: null,
      bear: null,
    })
  })
})