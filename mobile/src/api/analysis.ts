import { request } from "./request";
import {
  DEPTH_LEVELS,
  HIDDEN_DEFAULTS,
  type MarketType,
} from "@/constants/analysis";

/** 表单状态（页面维护，提交时转换为载荷） */
export interface SingleAnalysisForm {
  symbol: string;
  market: MarketType;
  /** YYYY-MM-DD */
  analysisDate: string;
  /** 1-5 */
  depthLevel: number;
  /** 分析师 ID */
  analystIds: string[];
  quickModel: string;
  deepModel: string;
}

/** 提交载荷（tech_solution 4.1.2） */
export interface SingleAnalysisPayload {
  symbol: string;
  stock_code: string;
  parameters: {
    market_type: MarketType;
    analysis_date: string;
    research_depth: string;
    selected_analysts: string[];
    include_sentiment: boolean;
    include_risk: boolean;
    language: string;
    quick_analysis_model: string;
    deep_analysis_model: string;
  };
}

/** 界面档位 1-5 → 中文档位名（与 PC getDepthDescription 一致） */
export function depthLevelToName(level: number): string {
  return DEPTH_LEVELS.find((d) => d.level === level)?.name || "标准";
}

export function buildSingleAnalysisPayload(
  form: SingleAnalysisForm
): SingleAnalysisPayload {
  const symbol = form.symbol.trim().toUpperCase();
  return {
    symbol,
    stock_code: symbol,
    parameters: {
      market_type: form.market,
      analysis_date: form.analysisDate,
      research_depth: depthLevelToName(form.depthLevel),
      selected_analysts: [...form.analystIds],
      include_sentiment: HIDDEN_DEFAULTS.include_sentiment,
      include_risk: HIDDEN_DEFAULTS.include_risk,
      language: HIDDEN_DEFAULTS.language,
      quick_analysis_model: form.quickModel,
      deep_analysis_model: form.deepModel,
    },
  };
}

/** 提交单股分析，返回 task_id（POST /api/analysis/single，需登录） */
export async function submitSingleAnalysis(
  payload: SingleAnalysisPayload
): Promise<string> {
  const data = await request<{ task_id?: string }>({
    url: "/api/analysis/single",
    method: "POST",
    data: payload,
  });
  if (!data?.task_id) {
    throw new Error("任务ID获取失败，请重试");
  }
  return data.task_id;
}

/**
 * 查询股票名称（GET /api/stock-data/basic-info/{symbol}，需登录）。
 * 仅用于输入框旁的名称标签；任何失败都静默返回空串，不影响提交。
 */
export async function getStockName(symbol: string): Promise<string> {
  try {
    const data = await request<{ name?: string }>({
      url: `/api/stock-data/basic-info/${encodeURIComponent(symbol)}`,
      method: "GET",
      silent: true,
    });
    return data?.name || "";
  } catch {
    return "";
  }
}
