import { describe, it, expect } from 'vitest'
import {
  DEPARTMENTS,
  MODULE_TITLES,
  OTHER_DEPT_KEY,
  OVERVIEW_DEPT_KEY,
  buildVisibleDepartments,
  hasContent,
  moduleTitle,
  pickRoleContent,
  resolveLocation,
} from '../shareConfig'

describe('hasContent', () => {
  it('空白字符串视为空', () => {
    expect(hasContent('')).toBe(false)
    expect(hasContent('   \n ')).toBe(false)
    expect(hasContent('有内容')).toBe(true)
  })

  it('null / undefined / 空集合视为空', () => {
    expect(hasContent(null)).toBe(false)
    expect(hasContent(undefined)).toBe(false)
    expect(hasContent({})).toBe(false)
    expect(hasContent([])).toBe(false)
  })

  it('非空集合与非字符串原始值视为非空', () => {
    expect(hasContent({ a: 1 })).toBe(true)
    expect(hasContent([1])).toBe(true)
    expect(hasContent(0)).toBe(true)
  })
})

describe('DEPARTMENTS 映射表', () => {
  it('与 tech_solution 5.2 的部门顺序一致，且概览无二级岗位', () => {
    expect(DEPARTMENTS.map((dept) => dept.key)).toEqual([
      'overview',
      'analysts',
      'research',
      'trading',
      'risk',
    ])
    expect(DEPARTMENTS[0].roles).toEqual([])
  })

  it('一级页签使用证券公司部门名称，分析师岗对应分析部', () => {
    expect(DEPARTMENTS.map((dept) => dept.name)).toEqual([
      '概览',
      '分析部',
      '研究部',
      '交易部',
      '风控部',
    ])
  })

  it('风控部主席合并两段相同正文，优先 risk_management_decision', () => {
    const risk = DEPARTMENTS.find((dept) => dept.key === 'risk')
    const chair = risk?.roles[risk.roles.length - 1]
    expect(chair).toEqual({
      key: 'riskManager',
      name: '风险管理委员会主席',
      fields: ['risk_management_decision', 'final_trade_decision'],
    })
  })

  it('研究经理合并 research_team_decision 与 investment_plan 两个字段', () => {
    const research = DEPARTMENTS.find((dept) => dept.key === 'research')
    const manager = research?.roles.find((role) => role.key === 'manager')
    expect(manager?.fields).toEqual(['research_team_decision', 'investment_plan'])
  })
})

describe('moduleTitle', () => {
  it('未映射字段使用中文名，标题表不与岗位字段重叠', () => {
    const mapped = new Set(DEPARTMENTS.flatMap((dept) => dept.roles.flatMap((role) => role.fields)))
    expect(Object.keys(MODULE_TITLES).some((key) => mapped.has(key))).toBe(false)
    expect(moduleTitle('company_overview')).toBe('公司概况')
    expect(moduleTitle('financial_analysis')).toBe('财务分析')
    expect(moduleTitle('technical_analysis')).toBe('技术分析')
    expect(moduleTitle('market_analysis')).toBe('市场分析')
    expect(moduleTitle('risk_analysis')).toBe('风险分析')
    expect(moduleTitle('valuation_analysis')).toBe('估值分析')
    expect(moduleTitle('investment_recommendation')).toBe('投资建议')
  })

  it('已映射字段和未登记字段都不走岗位中文标题', () => {
    expect(moduleTitle('market_report')).toBe('market report')
    expect(moduleTitle('final_trade_decision')).toBe('final trade decision')
    expect(moduleTitle('custom_module')).toBe('custom module')
  })
})

describe('pickRoleContent', () => {
  const manager = { key: 'manager', name: '研究经理', fields: ['research_team_decision', 'investment_plan'] }

  it('多个字段时取第一个非空字段', () => {
    expect(pickRoleContent({ investment_plan: '计划' }, manager)).toEqual({
      field: 'investment_plan',
      content: '计划',
    })
    expect(
      pickRoleContent({ research_team_decision: '决策', investment_plan: '计划' }, manager)
    ).toEqual({ field: 'research_team_decision', content: '决策' })
  })

  it('第一个字段为空字符串时向后回退', () => {
    expect(pickRoleContent({ research_team_decision: '  ', investment_plan: '计划' }, manager)).toEqual({
      field: 'investment_plan',
      content: '计划',
    })
  })

  it('全部字段无内容时返回 null', () => {
    expect(pickRoleContent({}, manager)).toBeNull()
    expect(pickRoleContent({ research_team_decision: '' }, manager)).toBeNull()
  })
})

describe('buildVisibleDepartments', () => {
  it('无 reports 时只保留概览', () => {
    expect(buildVisibleDepartments(undefined)).toEqual([
      { key: OVERVIEW_DEPT_KEY, name: '概览', roles: [], showSubTabs: false },
    ])
    expect(buildVisibleDepartments({})).toHaveLength(1)
  })

  it('空岗位被剔除、空部门整条不显示', () => {
    const result = buildVisibleDepartments({
      market_report: '市场分析正文',
      bull_researcher: '多头观点',
    })
    expect(result.map((dept) => dept.key)).toEqual([OVERVIEW_DEPT_KEY, 'analysts', 'research'])
    const analysts = result.find((dept) => dept.key === 'analysts')
    expect(analysts?.roles.map((role) => role.key)).toEqual(['market'])
    // 交易部 / 风控部无内容，整条不出现
    expect(result.find((dept) => dept.key === 'trading')).toBeUndefined()
    expect(result.find((dept) => dept.key === 'risk')).toBeUndefined()
  })

  it('部门下只有一个岗位时不显示二级页签', () => {
    const result = buildVisibleDepartments({ trader_investment_plan: '交易员计划' })
    const trading = result.find((dept) => dept.key === 'trading')
    expect(trading?.roles).toEqual([
      expect.objectContaining({ key: 'trader', name: '交易员' }),
    ])
    expect(trading?.showSubTabs).toBe(false)
  })

  it('部门下多个岗位有内容时显示二级页签', () => {
    const result = buildVisibleDepartments({
      market_report: 'a',
      fundamentals_report: 'b',
    })
    const analysts = result.find((dept) => dept.key === 'analysts')
    expect(analysts?.roles.map((role) => role.key)).toEqual(['market', 'fundamentals'])
    expect(analysts?.showSubTabs).toBe(true)
  })

  it('研究经理优先用 research_team_decision，缺失时用 investment_plan', () => {
    const withDecision = buildVisibleDepartments({ research_team_decision: '决策' })
    expect(withDecision.find((dept) => dept.key === 'research')?.roles[0].field).toBe(
      'research_team_decision'
    )

    const withPlanOnly = buildVisibleDepartments({ investment_plan: '计划' })
    const managerRole = withPlanOnly.find((dept) => dept.key === 'research')?.roles[0]
    expect(managerRole?.field).toBe('investment_plan')
    expect(managerRole?.name).toBe('研究经理')
  })

  it('未映射的已知模块进「其他」并使用中文名，已映射字段仍用岗位名', () => {
    const result = buildVisibleDepartments({
      market_report: '市场正文',
      company_overview: '公司概况正文',
      financial_analysis: '财务正文',
    })
    const analysts = result.find((dept) => dept.key === 'analysts')
    expect(analysts?.roles.map((role) => role.name)).toEqual(['市场分析师'])
    const other = result.find((dept) => dept.key === OTHER_DEPT_KEY)
    expect(other?.roles.map((role) => role.name)).toEqual(['公司概况', '财务分析'])
    expect(other?.showSubTabs).toBe(true)
  })

  it('映射表外的字段落入「其他」部门，不丢失内容', () => {
    const result = buildVisibleDepartments({ market_report: 'a', custom_module: '自定义正文' })
    const other = result.find((dept) => dept.key === OTHER_DEPT_KEY)
    expect(other?.name).toBe('其他')
    expect(other?.roles).toEqual([
      { key: 'custom_module', name: 'custom module', field: 'custom_module', content: '自定义正文' },
    ])
    expect(other?.showSubTabs).toBe(false)
  })

  it('「其他」部门有多个字段时显示二级页签，且顺序与 reports 一致', () => {
    const result = buildVisibleDepartments({ alpha_field: 'a', beta_field: 'b' })
    const other = result.find((dept) => dept.key === OTHER_DEPT_KEY)
    expect(other?.roles.map((role) => role.key)).toEqual(['alpha_field', 'beta_field'])
    expect(other?.showSubTabs).toBe(true)
  })

  it('已映射字段不会重复出现在「其他」部门', () => {
    const result = buildVisibleDepartments({ market_report: 'a', bull_researcher: 'b' })
    expect(result.find((dept) => dept.key === OTHER_DEPT_KEY)).toBeUndefined()
  })

  it('主席两段正文同时存在时只显示一次，不进入「其他」', () => {
    const result = buildVisibleDepartments({
      risk_management_decision: '主席裁决',
      final_trade_decision: '主席裁决',
    })
    expect(result.map((dept) => dept.key)).toEqual([OVERVIEW_DEPT_KEY, 'risk'])
    const chair = result.find((dept) => dept.key === 'risk')?.roles[0]
    expect(chair).toEqual({
      key: 'riskManager',
      name: '风险管理委员会主席',
      field: 'risk_management_decision',
      content: '主席裁决',
    })
    expect(result.find((dept) => dept.key === OTHER_DEPT_KEY)).toBeUndefined()
  })

  it('只有 final_trade_decision 时仍归风控部主席', () => {
    const result = buildVisibleDepartments({ final_trade_decision: '旧报告裁决' })
    const chair = result.find((dept) => dept.key === 'risk')?.roles[0]
    expect(chair?.field).toBe('final_trade_decision')
    expect(chair?.content).toBe('旧报告裁决')
    expect(result.find((dept) => dept.key === OTHER_DEPT_KEY)).toBeUndefined()
  })

  it('概览始终排在第一位且不参与岗位内容判空', () => {
    const result = buildVisibleDepartments({ bull_researcher: 'b' })
    expect(result[0].key).toBe(OVERVIEW_DEPT_KEY)
  })
})

describe('resolveLocation', () => {
  const departments = buildVisibleDepartments({
    market_report: 'a',
    fundamentals_report: 'b',
    bull_researcher: 'c',
  })

  it('合法 tab + role 原样返回', () => {
    expect(resolveLocation(departments, 'analysts', 'fundamentals')).toEqual({
      tab: 'analysts',
      role: 'fundamentals',
    })
    expect(resolveLocation(departments, 'research', 'bull')).toEqual({
      tab: 'research',
      role: 'bull',
    })
  })

  it('缺失或非法 tab 回落到概览', () => {
    expect(resolveLocation(departments, undefined, 'bull')).toEqual({
      tab: OVERVIEW_DEPT_KEY,
      role: '',
    })
    expect(resolveLocation(departments, 'not-exist', 'bull')).toEqual({
      tab: OVERVIEW_DEPT_KEY,
      role: '',
    })
    // 空部门的 tab 也视为非法
    expect(resolveLocation(departments, 'trading', 'trader').tab).toBe(OVERVIEW_DEPT_KEY)
  })

  it('tab 合法但 role 缺失或非法时取该部门第一个岗位', () => {
    expect(resolveLocation(departments, 'analysts', undefined)).toEqual({
      tab: 'analysts',
      role: 'market',
    })
    expect(resolveLocation(departments, 'analysts', 'not-exist')).toEqual({
      tab: 'analysts',
      role: 'market',
    })
  })

  it('概览部门忽略 role', () => {
    expect(resolveLocation(departments, 'overview', 'market')).toEqual({
      tab: OVERVIEW_DEPT_KEY,
      role: '',
    })
  })

  it('旧的 tab=decision 在主席可见时打开风控部主席', () => {
    const withChair = buildVisibleDepartments({
      risk_management_decision: '主席裁决',
      final_trade_decision: '主席裁决',
    })
    expect(resolveLocation(withChair, 'decision', 'final')).toEqual({
      tab: 'risk',
      role: 'riskManager',
    })
  })

  it('旧的 tab=decision 在主席不存在时回落到概览', () => {
    expect(resolveLocation(departments, 'decision', 'final')).toEqual({
      tab: OVERVIEW_DEPT_KEY,
      role: '',
    })
  })
})