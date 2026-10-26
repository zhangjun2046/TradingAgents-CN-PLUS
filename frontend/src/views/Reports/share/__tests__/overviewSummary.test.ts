import { describe, expect, it } from 'vitest'
import { formatOverviewSummary } from '../overviewSummary'

const truncatedSummary = `风险管理委员会主席裁决书

股票代码：000001（平安银行股份有限公司）

---

一、辩论核心论点提炼与评估

激进派最强论点（采纳度：高）

| 论点 | 证据强度 | 委员会评估 |
|------|----------|-----------|
| 自由流通市值仅33.3% | ★★★★★ | 采纳。这是本次辩...`

const fullDecision = `# 风险管理委员会主席裁决书

## 一、辩论核心论点提炼与评估

| 论点 | 委员会评估 |
|------|-----------|
| 流动性结构脆弱 | **采纳**。这是结构性风险 |

**激进派弱点**：将卖出等同于赛道切换，超出委员会授权范围。

后续还有很长的第二句，不应该出现在摘要里。`

describe('formatOverviewSummary', () => {
  it('表格中间被截断的摘要不产出半行表格', () => {
    const result = formatOverviewSummary(truncatedSummary)
    expect(result.includes('|')).toBe(false)
    expect(result.includes('这是本次辩')).toBe(false)
    expect(result).toBe('')
  })

  it('完整裁决书取出表格之后的第一句', () => {
    expect(formatOverviewSummary(fullDecision)).toBe(
      '激进派弱点：将卖出等同于赛道切换，超出委员会授权范围。'
    )
  })

  it('只取第一句，不带上后面的句子', () => {
    const longSentence = `${'甲'.repeat(40)}。${'乙'.repeat(80)}。`
    expect(formatOverviewSummary(longSentence)).toBe(`${'甲'.repeat(40)}。`)
  })

  it('第一句超过 100 字且上限内没有句号时返回空字符串', () => {
    expect(formatOverviewSummary(`${'甲'.repeat(120)}。`)).toBe('')
  })

  it('上限内没有完整句子时返回空字符串', () => {
    expect(formatOverviewSummary('只有标题没有句号')).toBe('')
    expect(formatOverviewSummary('# 标题\n\n| a | b |\n|---|---|\n')).toBe('')
    expect(formatOverviewSummary(null)).toBe('')
  })
})
