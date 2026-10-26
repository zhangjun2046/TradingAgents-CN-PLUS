import { describe, expect, it } from 'vitest'
import { stripTrailingDisclaimer } from '../stripDisclaimer'

const marketBody = `### 2. 风险提示

- 价格突破未持续上涨，短线回调风险；
- MACD 的 DIF 仍在零轴下方。

### 3. 关键价格区间

- 支撑位：¥9.66

免责声明：本报告基于历史技术数据进行分析，仅供参考，不构成投资建议。`

const fundamentalsBody = `### 操作建议

- 已持仓者：控制仓位。

### 重要声明

本报告基于公开数据与模型测算生成，仅供参考，不构成投资依据。

数据来源：多源数据核验｜生成时间：2026-10-23`

describe('stripTrailingDisclaimer', () => {
  it('去掉文末免责声明，保留正文里的风险提示', () => {
    const result = stripTrailingDisclaimer(marketBody)
    expect(result.includes('价格突破未持续上涨')).toBe(true)
    expect(result.includes('关键价格区间')).toBe(true)
    expect(result.includes('免责声明')).toBe(false)
    expect(result.includes('不构成投资建议')).toBe(false)
  })

  it('去掉重要声明，保留数据来源', () => {
    const result = stripTrailingDisclaimer(fundamentalsBody)
    expect(result.includes('已持仓者')).toBe(true)
    expect(result.includes('重要声明')).toBe(false)
    expect(result.includes('不构成投资依据')).toBe(false)
    expect(result.includes('数据来源：多源数据核验')).toBe(true)
  })

  it('去掉加粗、斜体和引用形式的文末声明', () => {
    const bold = '分析正文。\n\n---\n**免责声明**：本报告不构成任何买卖建议。'
    expect(stripTrailingDisclaimer(bold)).toBe('分析正文。')

    const quote = '新闻正文。\n\n> 免责声明：本分析基于公开新闻数据，不构成任何投资建议。'
    expect(stripTrailingDisclaimer(quote)).toBe('新闻正文。')

    const italic = [
      '## 八、风险提示',
      '',
      '- 估值修复不及预期。',
      '',
      '## 九、总结',
      '',
      '> 当前价格提供了安全边际。',
      '',
      '---',
      '',
      '*免责声明：本报告仅基于公开数据分析，不构成具体投资建议。投资有风险，决策需谨慎。*'
    ].join('\n')
    const stripped = stripTrailingDisclaimer(italic)
    expect(stripped.includes('八、风险提示')).toBe(true)
    expect(stripped.includes('估值修复不及预期')).toBe(true)
    expect(stripped.includes('安全边际')).toBe(true)
    expect(stripped.includes('免责声明')).toBe(false)
    expect(stripped.includes('不构成具体投资建议')).toBe(false)

    const underscore = '分析正文。\n\n_免责声明：不构成投资建议。_'
    expect(stripTrailingDisclaimer(underscore)).toBe('分析正文。')
  })

  it('没有声明时保持原文', () => {
    const plain = '### 2. 风险提示\n\n- 宏观复苏不及预期。'
    expect(stripTrailingDisclaimer(plain)).toBe(plain)
    expect(stripTrailingDisclaimer('')).toBe('')
  })
})
