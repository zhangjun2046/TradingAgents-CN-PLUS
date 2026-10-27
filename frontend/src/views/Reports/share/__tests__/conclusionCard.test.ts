import { describe, expect, it } from 'vitest'
import {
  barWidthFor,
  maxAbsValue,
  roleInitial,
  shouldShowChartTitle,
} from '../conclusionCard'

describe('roleInitial', () => {
  it('取角色名首字', () => {
    expect(roleInitial('市场分析师')).toBe('市')
    expect(roleInitial('风险管理委员会主席')).toBe('风')
  })

  it('空串 / 纯空白回退「岗」', () => {
    expect(roleInitial('')).toBe('岗')
    expect(roleInitial('   ')).toBe('岗')
  })

  it('带首尾空白不影响取首字', () => {
    expect(roleInitial('  交易员')).toBe('交')
    expect(roleInitial('研究经理  ')).toBe('研')
  })
})

describe('shouldShowChartTitle', () => {
  it('有标题且不同于表格标题时显示', () => {
    expect(shouldShowChartTitle('估值对比', '投资建议')).toBe(true)
    expect(shouldShowChartTitle('估值对比', null)).toBe(true)
    expect(shouldShowChartTitle('估值对比', undefined)).toBe(true)
  })

  it('标题为空不显示', () => {
    expect(shouldShowChartTitle('', '估值对比')).toBe(false)
    expect(shouldShowChartTitle('', null)).toBe(false)
  })

  it('标题与表格标题相同时不显示，避免重复', () => {
    expect(shouldShowChartTitle('估值对比', '估值对比')).toBe(false)
  })
})

describe('maxAbsValue', () => {
  it('取所有序列样本绝对值最大者', () => {
    expect(maxAbsValue([{ values: [0.52, -0.65] }])).toBe(0.65)
    expect(maxAbsValue([{ values: [4.1, 6.0] }, { values: [-8, 2] }])).toBe(8)
  })

  it('空 / 缺省返回 0', () => {
    expect(maxAbsValue(undefined)).toBe(0)
    expect(maxAbsValue([])).toBe(0)
  })
})

describe('barWidthFor', () => {
  it('按占比返回百分比宽度', () => {
    expect(barWidthFor(0.52, 0.65)).toBe('80%')
    expect(barWidthFor(6, 6)).toBe('100%')
    expect(barWidthFor(-4, 8)).toBe('50%')
  })

  it('绝对值超过基准时封顶 100%', () => {
    expect(barWidthFor(1.5, 1)).toBe('100%')
  })

  it('基准非正时回退 0%', () => {
    expect(barWidthFor(1, 0)).toBe('0%')
    expect(barWidthFor(1, -1)).toBe('0%')
  })
})