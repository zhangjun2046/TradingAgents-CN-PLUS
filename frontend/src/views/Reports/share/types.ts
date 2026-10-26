/**
 * 分享页公开数据字段（对齐 doc/handoff/Backend-API-Report.md 2.3 白名单）。
 *
 * 内部字段（model_info / tokens_used / user_id / task_id 等）不会由公开接口下发，
 * 这里也不声明，避免误用。
 */

/** `decision` 仅保留白名单字段，缺失的键不会输出。 */
export interface SharedDecision {
  action?: string
  target_price?: number | string
  confidence?: number
  risk_score?: number
}

export interface SharedReport {
  /** 基本信息 */
  stock_symbol?: string
  stock_name?: string
  analysis_date?: string
  created_at?: string
  /** 结论摘要 */
  recommendation?: string
  risk_level?: string
  confidence_score?: number
  summary?: string
  key_points?: string[]
  /** 参与的岗位 / 分析师，如 ['market', 'fundamentals']，缺失为 [] */
  analysts?: string[]
  /** 研究深度，缺失为 1 */
  research_depth?: number
  /** 决策白名单字段，缺失为 {} */
  decision?: SharedDecision
  /** 该分享的到期时间（ISO 字符串） */
  expires_at?: string
  /** 按固定模块顺序排列、已剔除空内容的模块正文 */
  reports?: Record<string, unknown>
}

/** 公开接口成功响应体 */
export interface ShareApiResponse {
  success?: boolean
  data?: SharedReport
  message?: string
}