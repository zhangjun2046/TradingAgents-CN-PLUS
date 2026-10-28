import { describe, expect, it } from 'vitest'
import { normalizeConfidenceScore, resolveRiskLevel } from '../reportMetrics'

describe('normalizeConfidenceScore', () => {
  it('0-1 与 0-100 都得到同一整数分', () => {
    expect(normalizeConfidenceScore(0.85)).toBe(85)
    expect(normalizeConfidenceScore(85)).toBe(85)
    expect(normalizeConfidenceScore(1)).toBe(100)
    expect(normalizeConfidenceScore(100)).toBe(100)
    expect(normalizeConfidenceScore(0)).toBe(0)
  })

  it('越界夹紧，非法值回退 0', () => {
    expect(normalizeConfidenceScore(150)).toBe(100)
    expect(normalizeConfidenceScore(-5)).toBe(0)
    expect(normalizeConfidenceScore(undefined)).toBe(0)
    expect(normalizeConfidenceScore(null)).toBe(0)
    expect(normalizeConfidenceScore('abc')).toBe(0)
  })
})

describe('resolveRiskLevel', () => {
  it('五档等级与星级、颜色固定', () => {
    expect(resolveRiskLevel('低')).toEqual({ key: '低', label: '低风险', level: 1, color: '#67C23A' })
    expect(resolveRiskLevel('中低')).toEqual({
      key: '中低',
      label: '中低风险',
      level: 2,
      color: '#95D475'
    })
    expect(resolveRiskLevel('中等')).toEqual({
      key: '中等',
      label: '中等风险',
      level: 3,
      color: '#E6A23C'
    })
    expect(resolveRiskLevel('中高')).toEqual({
      key: '中高',
      label: '中高风险',
      level: 4,
      color: '#F56C6C'
    })
    expect(resolveRiskLevel('高')).toEqual({ key: '高', label: '高风险', level: 5, color: '#F56C6C' })
  })

  it('带「风险」后缀时等级与不带后缀相同，不会再拼一次', () => {
    expect(resolveRiskLevel('高风险')).toEqual(resolveRiskLevel('高'))
    expect(resolveRiskLevel('中低风险')).toEqual(resolveRiskLevel('中低'))
    expect(resolveRiskLevel('中高风险')).toEqual(resolveRiskLevel('中高'))
    expect(resolveRiskLevel('中等风险').label).toBe('中等风险')
  })

  it('空值是中等；无法识别的原文保留且星级颜色走中等默认', () => {
    expect(resolveRiskLevel('')).toEqual(resolveRiskLevel('中等'))
    expect(resolveRiskLevel(undefined)).toEqual(resolveRiskLevel('中等'))
    expect(resolveRiskLevel(null)).toEqual(resolveRiskLevel('中等'))
    expect(resolveRiskLevel('极高')).toEqual({
      key: '极高',
      label: '极高风险',
      level: 3,
      color: '#E6A23C'
    })
  })
})
