/**
 * 分享页「部门 - 岗位」映射与显示规则（配置化）。
 *
 * 设计依据：doc/tech_solution.md 5.2、doc/requirement.md 5.2.3。
 * 本文件只放纯函数与静态映射，便于单元测试，不依赖 Vue 运行时。
 */

export interface RoleDef {
  key: string
  name: string
  /** 多个字段时取第一个非空字段（如研究经理合并 research_team_decision / investment_plan） */
  fields: string[]
}

export interface DeptDef {
  key: string
  name: string
  roles: RoleDef[]
}

/** 概览部门固定存在，无二级岗位 */
export const OVERVIEW_DEPT_KEY = 'overview'

/** 映射表外的模块落到这里，避免内容丢失 */
export const OTHER_DEPT_KEY = 'other'

export const OTHER_DEPT_NAME = '其他'

export const DEPARTMENTS: DeptDef[] = [
  { key: OVERVIEW_DEPT_KEY, name: '概览', roles: [] },
  {
    key: 'analysts',
    // 分析师岗用「分析部」，避免与「研究部」混淆；URL 仍用 analysts
    name: '分析部',
    roles: [
      { key: 'market', name: '市场分析师', fields: ['market_report'] },
      { key: 'fundamentals', name: '基本面分析师', fields: ['fundamentals_report'] },
      { key: 'news', name: '新闻分析师', fields: ['news_report'] },
      { key: 'sentiment', name: '社媒 / 情绪分析师', fields: ['sentiment_report'] },
    ],
  },
  {
    key: 'research',
    name: '研究部',
    roles: [
      { key: 'bull', name: '多头研究员', fields: ['bull_researcher'] },
      { key: 'bear', name: '空头研究员', fields: ['bear_researcher'] },
      {
        key: 'manager',
        name: '研究经理',
        fields: ['research_team_decision', 'investment_plan'],
      },
    ],
  },
  {
    key: 'trading',
    name: '交易部',
    roles: [{ key: 'trader', name: '交易员', fields: ['trader_investment_plan'] }],
  },
  {
    key: 'risk',
    name: '风控部',
    roles: [
      { key: 'risky', name: '激进风控分析师', fields: ['risky_analyst'] },
      { key: 'safe', name: '保守风控分析师', fields: ['safe_analyst'] },
      { key: 'neutral', name: '中性风控分析师', fields: ['neutral_analyst'] },
      {
        key: 'riskManager',
        name: '风险管理委员会主席',
        // 与 final_trade_decision 是同一次输出；优先主席字段，旧报告只有后者时仍归本岗
        fields: ['risk_management_decision', 'final_trade_decision'],
      },
    ],
  },
]

/**
 * 未进入部门映射的模块，在「其他」里使用的中文名。
 * 已分配给岗位的字段用岗位名展示，不在这里重复登记。
 */
export const MODULE_TITLES: Record<string, string> = {
  company_overview: '公司概况',
  financial_analysis: '财务分析',
  technical_analysis: '技术分析',
  market_analysis: '市场分析',
  risk_analysis: '风险分析',
  valuation_analysis: '估值分析',
  investment_recommendation: '投资建议',
}

/** 模块字段的展示标题，未登记时把下划线替换为空格 */
export function moduleTitle(key: string): string {
  return MODULE_TITLES[key] || key.replace(/_/g, ' ')
}

/** 与后端 report_share_service._has_module_content 保持一致的判空规则 */
export function hasContent(content: unknown): boolean {
  if (content === null || content === undefined) return false
  if (typeof content === 'string') return content.trim().length > 0
  if (Array.isArray(content)) return content.length > 0
  if (typeof content === 'object') return Object.keys(content as object).length > 0
  return true
}

export interface VisibleRole {
  key: string
  name: string
  /** 命中的模块字段（多个字段时取第一个非空的） */
  field: string
  content: unknown
}

export interface VisibleDept {
  key: string
  name: string
  roles: VisibleRole[]
  /** 至少两个岗位时才显示二级页签 */
  showSubTabs: boolean
}

/** 取岗位第一个非空字段的内容 */
export function pickRoleContent(
  reports: Record<string, unknown>,
  role: RoleDef
): { field: string; content: unknown } | null {
  for (const field of role.fields) {
    const content = reports[field]
    if (hasContent(content)) return { field, content }
  }
  return null
}

/** 全部已被映射表消费的模块字段 */
function mappedFields(): Set<string> {
  const used = new Set<string>()
  for (const dept of DEPARTMENTS) {
    for (const role of dept.roles) {
      for (const field of role.fields) used.add(field)
    }
  }
  return used
}

/**
 * 派生可见部门与岗位：
 * - 空岗位剔除；部门下无任何岗位时该部门剔除；概览始终保留；
 * - `reports` 里未被映射表消费的字段追加为「其他」部门，每个字段一个岗位。
 */
export function buildVisibleDepartments(
  reports?: Record<string, unknown> | null
): VisibleDept[] {
  const source = reports || {}
  const result: VisibleDept[] = []

  for (const dept of DEPARTMENTS) {
    if (dept.key === OVERVIEW_DEPT_KEY) {
      result.push({ key: dept.key, name: dept.name, roles: [], showSubTabs: false })
      continue
    }
    const roles: VisibleRole[] = []
    for (const role of dept.roles) {
      const hit = pickRoleContent(source, role)
      if (!hit) continue
      roles.push({ key: role.key, name: role.name, field: hit.field, content: hit.content })
    }
    if (roles.length === 0) continue
    result.push({ key: dept.key, name: dept.name, roles, showSubTabs: roles.length > 1 })
  }

  const used = mappedFields()
  const extraRoles: VisibleRole[] = []
  for (const [field, content] of Object.entries(source)) {
    if (used.has(field) || !hasContent(content)) continue
    extraRoles.push({
      key: field,
      name: moduleTitle(field),
      field,
      content,
    })
  }
  if (extraRoles.length > 0) {
    result.push({
      key: OTHER_DEPT_KEY,
      name: OTHER_DEPT_NAME,
      roles: extraRoles,
      showSubTabs: extraRoles.length > 1,
    })
  }

  return result
}

export interface ShareLocation {
  tab: string
  role: string
}

/** 开发期分享页在 :3000，报告列表在 H5 :3100；同域部署时走当前站点 /m/ */
export function resolveReportListUrl(): string {
  if (typeof window === 'undefined') return '/m/#/pages/reports/list'
  const { hostname, port, origin } = window.location
  const isDevPc = (hostname === 'localhost' || hostname === '127.0.0.1') && port === '3000'
  const base = isDevPc ? 'http://localhost:3100' : origin
  return `${base}/m/#/pages/reports/list`
}

export function logBackToList(): void {
  console.info('[Share] back to report list', { url: resolveReportListUrl() })
}

/** 已取消的一级页签；旧链接改指向风控部主席 */
const LEGACY_DECISION_TAB = 'decision'

/**
 * 解析 `?tab=&role=`：
 * - 一级页签缺失或非法 -> 概览；
 * - 旧的 `tab=decision` -> 风控部主席（该岗位可见时），否则概览；
 * - 一级页签合法但二级岗位缺失或非法 -> 该部门第一个岗位；概览部门忽略 role。
 */
export function resolveLocation(
  departments: VisibleDept[],
  tab?: string | null,
  role?: string | null
): ShareLocation {
  if (tab === LEGACY_DECISION_TAB) {
    const risk = departments.find((dept) => dept.key === 'risk')
    const chair = risk?.roles.find((item) => item.key === 'riskManager')
    if (!chair) return { tab: OVERVIEW_DEPT_KEY, role: '' }
    return { tab: 'risk', role: 'riskManager' }
  }
  const target = departments.find((dept) => dept.key === tab)
  if (!target) return { tab: OVERVIEW_DEPT_KEY, role: '' }
  if (target.roles.length === 0) return { tab: target.key, role: '' }
  const matched = target.roles.find((item) => item.key === role)
  return { tab: target.key, role: matched ? matched.key : target.roles[0].key }
}