import { describe, expect, it } from 'vitest'
import { extractRoleView, plainText, plainTextLength } from '../reportConclusion'

describe('extractRoleView 观点与原句', () => {
  it('结论段从后往前取含观点的原句，句末关键词决定标签', () => {
    const markdown = ['## 投资建议', '行业景气仍在，此前看多。', '综合估值后建议卖出。'].join('\n')
    const view = extractRoleView(markdown)
    expect(view.conclusion).toEqual({
      stance: 'bearish',
      sentence: '综合估值后建议卖出'
    })
    expect(plainText(markdown)).toContain(view.conclusion.sentence)
  })

  it('同一句里取最后出现的关键词', () => {
    const markdown = '## 结论\n先看多，最终建议卖出。'
    expect(extractRoleView(markdown).conclusion).toEqual({
      stance: 'bearish',
      sentence: '先看多，最终建议卖出'
    })
  })

  it('看多、看空、中性分别识别买入、减持和观望', () => {
    expect(extractRoleView('## 建议\n给予买入。').conclusion.stance).toBe('bullish')
    expect(extractRoleView('## 建议\n建议减持。').conclusion.stance).toBe('bearish')
    expect(extractRoleView('## 建议\n继续观望。').conclusion.stance).toBe('neutral')
  })

  it('否定说法不展示这句话', () => {
    const view = extractRoleView('## 投资建议\n当前不建议买入。')
    expect(view.conclusion).toEqual({ stance: 'unknown', sentence: '' })
  })

  it('后句被否定时，改用前面仍成立的原句', () => {
    const markdown = '## 结论\n公司质地不错，建议看多。\n短期不建议买入。'
    expect(extractRoleView(markdown).conclusion).toEqual({
      stance: 'bullish',
      sentence: '公司质地不错，建议看多'
    })
  })

  it('不是买入时不把买入当成看多', () => {
    const view = extractRoleView('## 建议\n这不是买入的时机，建议持有。')
    expect(view.conclusion).toEqual({
      stance: 'neutral',
      sentence: '这不是买入的时机，建议持有'
    })
  })

  it('买入价和卖出价是价位，不覆盖前面的持有评级', () => {
    const markdown = [
      '## 投资建议',
      '投资评级：持有（观望）。',
      '突破买入价：HK$26.85。',
      '跌破卖出价：HK$25.30。'
    ].join('\n')
    expect(extractRoleView(markdown).conclusion).toEqual({
      stance: 'neutral',
      sentence: '投资评级：持有（观望）'
    })
  })
  it('持有人和持有周期不算中性观点', () => {
    expect(extractRoleView('## 结论\n第一大持有人未变。').conclusion).toEqual({
      stance: 'unknown',
      sentence: ''
    })
    expect(extractRoleView('## 建议\n持有周期建议：12个月。').conclusion).toEqual({
      stance: 'unknown',
      sentence: ''
    })
  })

  it('转述别人的评级、以及“买入，不是……”都不出结论', () => {
    expect(extractRoleView('开篇给出“持有（观望）”评级。').conclusion).toEqual({
      stance: 'unknown',
      sentence: ''
    })
    expect(extractRoleView('空头认为“卖出”。').conclusion).toEqual({
      stance: 'unknown',
      sentence: ''
    })
    const markdown = ['## 我的结论', '不是看空它。', '此刻买入，不是拥抱成长。'].join('\n')
    expect(extractRoleView(markdown).conclusion).toEqual({ stance: 'unknown', sentence: '' })
  })

  it('本人给出的评级引号仍算本岗观点', () => {
    expect(extractRoleView('我的决定很明确：给出“卖出”建议。').conclusion).toEqual({
      stance: 'bearish',
      sentence: '我的决定很明确：给出“卖出”建议'
    })
    expect(extractRoleView('综合后给出**卖出**建议。').conclusion).toEqual({
      stance: 'bearish',
      sentence: '综合后给出卖出建议'
    })
    expect(extractRoleView('## 建议\n评级为“买入”。').conclusion).toEqual({
      stance: 'bullish',
      sentence: '评级为“买入”'
    })
  })

  it('看跌/看涨作观点词，但看跌分析师称谓不算', () => {
    expect(extractRoleView('## 结论\n结论看跌。').conclusion.stance).toBe('bearish')
    expect(extractRoleView('## 结论\n结论看涨。').conclusion.stance).toBe('bullish')
    expect(extractRoleView('支持看跌分析师。').conclusion).toEqual({
      stance: 'unknown',
      sentence: ''
    })
  })

  it('研究经理决策句优先于后文买入机会等论据词', () => {
    const markdown = [
      '听完双方陈述，我的决定很明确：支持看跌分析师，给出“卖出”建议。这不是一个轻松的决定。',
      '为什么看跌方的观点更胜一筹。多头提到的买入机会在流动性约束下站不住脚。'
    ].join('')
    expect(extractRoleView(markdown).conclusion).toEqual({
      stance: 'bearish',
      sentence: '听完双方陈述，我的决定很明确：支持看跌分析师，给出“卖出”建议'
    })
  })

  it('买入机会 / 买入理由不当作买入评级', () => {
    expect(extractRoleView('## 结论\n多头提到的买入机会站不住脚。').conclusion).toEqual({
      stance: 'unknown',
      sentence: ''
    })
  })

  it('没有结论小节时只用第一个正文段落', () => {
    const markdown = '开篇建议买入。\n\n后文改口卖出。'
    expect(extractRoleView(markdown).conclusion).toEqual({
      stance: 'bullish',
      sentence: '开篇建议买入'
    })
  })

  it('文末裁决优先于开头段落和表格里的同一评级', () => {
    const markdown = [
      '# 风险管理委员会最终裁决',
      '## 一、辩论总结',
      '**最强论点：**',
      '',
      '- 当前价格已为最坏情况部分定价',
      '## 二、最终决策：**卖出（减持）**',
      '',
      '| 决策 | 卖出（减持） |',
      '| --- | --- |',
      '| 置信度 | 0.75 |',
      '',
      '**最终裁决：卖出（减持）。** 在价格已处乐观区间，但不能改变减持的方向性判断。'
    ].join('\n')
    expect(extractRoleView(markdown).conclusion).toEqual({
      stance: 'bearish',
      sentence: '最终裁决：卖出（减持）'
    })
  })

  it('结论小节优先于文首段落', () => {
    const markdown = '文首写着买入。\n\n## 投资建议\n维持持有。'
    expect(extractRoleView(markdown).conclusion.stance).toBe('neutral')
  })

  it('中段结论没有观点时，改用后文投资建议里的原句', () => {
    const markdown = [
      '## 三、明确结论：显著低估',
      '价格处于低位。',
      '',
      '## 五、投资建议',
      '- **买入**：当前价格低于估值，安全边际充足。',
      '- **持有周期建议**：12个月。'
    ].join('\n')
    expect(extractRoleView(markdown).conclusion).toEqual({
      stance: 'bullish',
      sentence: '买入：当前价格低于估值，安全边际充足'
    })
  })

  it('显式裁决取首个动作，后续否定或适用人群不覆盖主结论', () => {
    expect(extractRoleView('最终裁决：建议“持有”，暂不买入或卖出。').conclusion).toEqual({
      stance: 'neutral',
      sentence: '最终裁决：建议“持有”，暂不买入或卖出'
    })
    expect(
      extractRoleView('核心建议：卖出（针对已持仓者）或持有现金（针对观望者）。').conclusion
    ).toEqual({
      stance: 'bearish',
      sentence: '核心建议：卖出（针对已持仓者）或持有现金（针对观望者）'
    })
    expect(extractRoleView('最终裁决：卖出或持有现金观望。').conclusion.stance).toBe('bearish')
    expect(
      extractRoleView(
        '中性派最终建议“20%战术再平衡+认沽对冲”，本质上是一个带对冲的减仓方案，而非“持有”方案。'
      ).conclusion
    ).toEqual({
      stance: 'bearish',
      sentence:
        '中性派最终建议“20%战术再平衡+认沽对冲”，本质上是一个带对冲的减仓方案，而非“持有”方案'
    })
  })

  it('转折后的被排除选项不覆盖前面的明确观点', () => {
    expect(
      extractRoleView('## 结论\n这种不对称性强烈支持采取积极的买入行动，而非观望或持有。')
        .conclusion
    ).toEqual({
      stance: 'bullish',
      sentence: '这种不对称性强烈支持采取积极的买入行动，而非观望或持有'
    })
  })

  it('反面买入情景、持有仓位和退出观望不作为观点', () => {
    expect(extractRoleView('## 结论\n冒进买入也可能导致资金被困。').conclusion).toEqual({
      stance: 'unknown',
      sentence: ''
    })
    expect(extractRoleView('## 结论\n持有仓位意味着完全暴露于下跌风险。').conclusion).toEqual({
      stance: 'unknown',
      sentence: ''
    })
    expect(extractRoleView('## 结论\n我们应退出观望，让数据提供清晰路标。').conclusion).toEqual({
      stance: 'unknown',
      sentence: ''
    })
  })

  it('表格里的买入不当成观点', () => {
    const markdown = [
      '## 结论',
      '| 建议 | 说明 |',
      '| --- | --- |',
      '| 买入 | 估值低 |',
      '',
      '正文没有给出态度。'
    ].join('\n')
    expect(extractRoleView(markdown).conclusion).toEqual({ stance: 'unknown', sentence: '' })
  })

  it('超长结论句完整保留，观点关键词不被截断', () => {
    // 关键词「买入」位于第 60 字之后，旧逻辑会截断导致看不到观点
    const sentence = `${'估'.repeat(70)}建议买入`
    const markdown = `## 结论\n${sentence}`
    const view = extractRoleView(markdown)
    expect(view.conclusion.stance).toBe('bullish')
    // 不截断、不留省略号，关键词完整可见
    expect(view.conclusion.sentence).toBe(sentence)
    expect(view.conclusion.sentence).toContain('建议买入')
    expect(view.conclusion.sentence.endsWith('…')).toBe(false)
    expect(plainText(markdown)).toContain(view.conclusion.sentence)
  })

  it('长句完整保留时与正文原文一致，仅剥离句尾标点', () => {
    const long = `从行业景气度、估值分位、资金流向与技术形态综合分析，当前价格具备安全边际，建议买入。`
    const markdown = `## 结论\n${long}`
    const view = extractRoleView(markdown)
    // 句尾句号按切句规则剥离，其余原句完整保留，观点关键词可见
    expect(view.conclusion.sentence).toBe(long.replace(/。$/, ''))
    expect(view.conclusion.sentence).toContain('建议买入')
    expect(view.conclusion.sentence.endsWith('…')).toBe(false)
    expect(plainText(markdown)).toContain(view.conclusion.sentence)
  })

  it('加粗标记去掉后，原句仍在正文里', () => {
    const markdown = '## 建议\n**建议买入**。'
    const view = extractRoleView(markdown)
    expect(view.conclusion.sentence).toBe('建议买入')
    expect(plainText(markdown)).toContain('建议买入')
  })

  it('评级句里后文的不建议，不否定前面的持有', () => {
    expect(
      extractRoleView('**投资评级**：**持有/观望**（适合现有持仓者，不建议新建仓）').conclusion
    ).toEqual({
      stance: 'neutral',
      sentence: '投资评级：持有/观望（适合现有持仓者，不建议新建仓）'
    })
    expect(
      extractRoleView('投资建议: 持有，暂不建议买入或大幅减仓，但需密切关注基本面变化。').conclusion
    ).toEqual({
      stance: 'neutral',
      sentence: '投资建议: 持有，暂不建议买入或大幅减仓，但需密切关注基本面变化'
    })
  })

  it('口语结论和文末提案与正文一致，不被开头段落带走', () => {
    const manager = ['双方都提到了买入机会。', '', '**因此，我的建议是：卖出。**'].join('\n')
    expect(extractRoleView(manager).conclusion).toEqual({
      stance: 'bearish',
      sentence: '因此，我的建议是：卖出'
    })
    expect(extractRoleView('### 我的决策：**卖出**').conclusion).toEqual({
      stance: 'bearish',
      sentence: '我的决策：卖出'
    })
    const sentiment = ['开篇只是在复述市场。', '', '**最终交易提案：持有**'].join('\n')
    expect(extractRoleView(sentiment).conclusion).toEqual({
      stance: 'neutral',
      sentence: '最终交易提案：持有'
    })
  })

  it('评级词写在决策句的下一句时，仍取这句结论', () => {
    const markdown = '我的决策是，现在不是追高的时候。我们应持有现有筹码。'
    expect(extractRoleView(markdown).conclusion).toEqual({
      stance: 'neutral',
      sentence: '我们应持有现有筹码'
    })
  })

  it('文首裁决标题不盖过后文的本人建议', () => {
    const markdown = ['# 风险管理委员会最终裁决：买入', '', '我的建议是：卖出，离场观望。'].join('\n')
    expect(extractRoleView(markdown).conclusion).toEqual({
      stance: 'bearish',
      sentence: '我的建议是：卖出，离场观望'
    })
  })

  it('投资评级中性偏多显示为中性', () => {
    expect(extractRoleView('- **投资评级**：中性偏多').conclusion).toEqual({
      stance: 'neutral',
      sentence: '投资评级：中性偏多'
    })
  })

  it('汇总表里的交易建议在正文没有评级句时作为结论', () => {
    const markdown = ['情绪偏淡。', '', '| 项目 | 结论 |', '| --- | --- |', '| 交易建议 | 观望 |'].join('\n')
    expect(extractRoleView(markdown).conclusion).toEqual({
      stance: 'neutral',
      sentence: '观望'
    })
  })

  it('空正文为未识别', () => {
    expect(extractRoleView('').conclusion).toEqual({ stance: 'unknown', sentence: '' })
    expect(extractRoleView('   \n').table).toBeNull()
  })
})

describe('extractRoleView 表与图', () => {
  it('列数不齐的表不抽到卡片上', () => {
    const markdown = ['| 甲 | 乙 |', '| --- | --- |', '| 1 | 2 | 3 |'].join('\n')
    const view = extractRoleView(markdown)
    expect(view.table).toBeNull()
    expect(view.chart).toBeNull()
  })

  it('同单位的两列画成图，数字与单元格一致', () => {
    const markdown = [
      '## 估值对比',
      '| 指标 | 公司 | 行业均值 |',
      '| --- | --- | --- |',
      '| 市净率 | 0.52 | 0.65 |',
      '| 市盈率 | 4.1 | 6.0 |',
      '',
      '## 投资建议',
      '估值偏低，建议买入。'
    ].join('\n')
    const view = extractRoleView(markdown)
    expect(view.table).toEqual({
      caption: '估值对比',
      headers: ['指标', '公司', '行业均值'],
      rows: [
        ['市净率', '0.52', '0.65'],
        ['市盈率', '4.1', '6.0']
      ]
    })
    expect(view.chart).toEqual({
      title: '估值对比',
      unit: '',
      series: ['公司', '行业均值'],
      items: [
        { label: '市净率', values: [0.52, 0.65], displays: ['0.52', '0.65'] },
        { label: '市盈率', values: [4.1, 6], displays: ['4.1', '6.0'] }
      ]
    })
  })

  it('百分号和倍数不放进同一张图', () => {
    const markdown = [
      '| 名称 | 比率 | 倍数 |',
      '| --- | --- | --- |',
      '| 甲 | 6.2% | 1.2倍 |',
      '| 乙 | 5.1% | 0.8倍 |'
    ].join('\n')
    const chart = extractRoleView(markdown).chart
    expect(chart?.unit).toBe('%')
    expect(chart?.series).toEqual(['比率'])
    expect(chart?.items).toEqual([
      { label: '甲', values: [6.2], displays: ['6.2%'] },
      { label: '乙', values: [5.1], displays: ['5.1%'] }
    ])
  })

  it('同一列单位混用时不画图，表仍保留', () => {
    const markdown = [
      '| 指标 | 2024A |',
      '| --- | --- |',
      '| 市净率 | 0.58 |',
      '| 股息率 | 6.2% |'
    ].join('\n')
    const view = extractRoleView(markdown)
    expect(view.table?.rows).toHaveLength(2)
    expect(view.chart).toBeNull()
  })

  it('结论小节里的表优先于文首的表', () => {
    const markdown = [
      '| 名称 | 值 |',
      '| --- | --- |',
      '| 甲 | 1 |',
      '| 乙 | 2 |',
      '',
      '## 投资建议',
      '建议买入。',
      '',
      '| 名称 | 比率 |',
      '| --- | --- |',
      '| 甲 | 10% |',
      '| 乙 | 20% |'
    ].join('\n')
    const view = extractRoleView(markdown)
    expect(view.table?.rows).toEqual([
      ['甲', '10%'],
      ['乙', '20%']
    ])
    expect(view.chart?.unit).toBe('%')
  })

  it('加粗数字仍按原文展示', () => {
    const markdown = [
      '| 名称 | 比例 |',
      '| --- | --- |',
      '| 甲 | **6.2%** |',
      '| 乙 | **5.1%** |'
    ].join('\n')
    const chart = extractRoleView(markdown).chart
    expect(chart?.items[0].displays).toEqual(['6.2%'])
    expect(chart?.items[0].values).toEqual([6.2])
  })

  it('列不齐时跳过，改用后面合格的表', () => {
    const markdown = [
      '| 甲 | 乙 |',
      '| --- | --- |',
      '| 1 | 2 | 3 |',
      '',
      '| 名称 | 比例 |',
      '| --- | --- |',
      '| 甲 | 10% |',
      '| 乙 | 20% |'
    ].join('\n')
    expect(extractRoleView(markdown).table?.headers).toEqual(['名称', '比例'])
  })
})

describe('plainTextLength', () => {
  it('字数去掉标记和空白', () => {
    expect(plainTextLength('**买入** 建议')).toBe('买入建议'.length)
  })
})
