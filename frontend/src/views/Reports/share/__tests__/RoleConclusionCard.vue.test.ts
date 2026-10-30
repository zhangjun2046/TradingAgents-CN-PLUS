import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import RoleConclusionCard from '../RoleConclusionCard.vue'
import type { Conclusion, ExtractedChart, ExtractedTable } from '@/utils/reportConclusion'

function makeConclusion(overrides: Partial<Conclusion> = {}): Conclusion {
  return { stance: 'unknown', sentence: '', ...overrides }
}

const nothing = { table: null, chart: null }

function render(props: {
  roleName?: string
  conclusion?: Conclusion
  table?: ExtractedTable | null
  chart?: ExtractedChart | null
  showStance?: boolean
}) {
  return mount(RoleConclusionCard, {
    props: {
      roleName: '市场分析师',
      conclusion: makeConclusion(),
      showStance: true,
      ...props,
      table: props.table ?? null,
      chart: props.chart ?? null,
    },
  })
}

describe('RoleConclusionCard 头像与徽章', () => {
  it('头像显示角色名首字', () => {
    expect(render({ roleName: '市场分析师' }).find('.avatar').text()).toBe('市')
    expect(render({ roleName: '风险管理委员会主席' }).find('.avatar').text()).toBe('风')
  })

  it('showStance 为 true 时按结论显示观点徽章', () => {
    const wrapper = render({ conclusion: makeConclusion({ stance: 'bullish' }) })
    expect(wrapper.find('.stance').text()).toBe('看多')
    expect(wrapper.find('.stance').classes()).toContain('is-bullish')
  })

  it('showStance 为 false 时不渲染观点徽章', () => {
    const wrapper = render({ showStance: false, conclusion: makeConclusion({ stance: 'bearish' }) })
    expect(wrapper.find('.stance').exists()).toBe(false)
  })

  it('未识别时徽章显示「未识别」', () => {
    const wrapper = render({ conclusion: makeConclusion({ stance: 'unknown' }) })
    expect(wrapper.find('.stance').text()).toBe('未识别')
    expect(wrapper.find('.stance').classes()).toContain('is-unknown')
  })
})

describe('RoleConclusionCard 一句话结论', () => {
  it('sentence 非空时展示一句话结论', () => {
    const wrapper = render({ conclusion: makeConclusion({ stance: 'bullish', sentence: '建议买入' }) })
    expect(wrapper.find('.sentence-label').text()).toBe('一句话结论')
    expect(wrapper.find('.sentence p').text()).toBe('建议买入')
  })

  it('sentence 为空时不渲染一句话结论块', () => {
    const wrapper = render({ conclusion: makeConclusion({ stance: 'unknown', sentence: '' }) })
    expect(wrapper.find('.sentence').exists()).toBe(false)
  })
})

describe('RoleConclusionCard 表格', () => {
  const table: ExtractedTable = {
    caption: '估值对比',
    headers: ['指标', '公司'],
    rows: [['市净率', '0.52']],
  }

  it('渲染标题、表头与单元格', () => {
    const wrapper = render({ table })
    expect(wrapper.find('.table-block .block-title').text()).toBe('估值对比')
    expect(wrapper.findAll('thead th').map((th) => th.text())).toEqual(['指标', '公司'])
    expect(wrapper.findAll('tbody td').map((td) => td.text())).toEqual(['市净率', '0.52'])
  })

  it('table 为空时不渲染表格块', () => {
    const wrapper = render({ table: null })
    expect(wrapper.find('.table-block').exists()).toBe(false)
  })
})

describe('RoleConclusionCard 图表', () => {
  const chart: ExtractedChart = {
    title: '估值对比',
    unit: '',
    series: ['公司', '行业均值'],
    items: [{ label: '市净率', values: [0.52, 0.26], displays: ['0.52', '0.26'] }],
  }

  it('图表标题与表格标题相同时不重复显示标题', () => {
    const wrapper = render({
      table: { caption: '估值对比', headers: ['指标'], rows: [['市净率']] },
      chart: { ...chart, title: '估值对比' },
    })
    expect(wrapper.find('.table-block .block-title').text()).toBe('估值对比')
    expect(wrapper.find('.chart-block .block-title').exists()).toBe(false)
  })

  it('图表标题不同于表格标题时显示图表标题', () => {
    const wrapper = render({ table: null, chart: { ...chart, title: '行业对比' } })
    expect(wrapper.find('.chart-block .block-title').text()).toBe('行业对比')
  })

  it('条形宽度以绝对值最大者为基准等比缩放', () => {
    const wrapper = render({ table: null, chart })
    const bars = wrapper.findAll('.bar')
    expect(bars.length).toBe(2)
    expect(bars[0].classes()).toContain('is-primary')
    expect(bars[1].classes()).toContain('is-secondary')
    expect(bars[0].element.style.width).toBe('100%')
    expect(bars[1].element.style.width).toBe('50%')
  })

  it('chart 为空时不渲染图表块', () => {
    const wrapper = render({ chart: null })
    expect(wrapper.find('.chart-block').exists()).toBe(false)
  })
})