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

/** 任务步骤（后端 progress tracker 的 steps 元素） */
export interface TaskStep {
  name: string;
  description?: string;
  /** pending | current | completed | failed */
  status: string;
}

/** 任务状态（GET /api/analysis/tasks/{id}/status 的 data，字段均可能缺失） */
export interface TaskStatusData {
  task_id?: string;
  /** pending | processing | running | completed | failed | cancelled */
  status?: string;
  /** 0-100 */
  progress?: number;
  message?: string;
  /** 当前步骤索引（数字）；历史记录恢复时可能是状态字符串 */
  current_step?: number | string;
  current_step_name?: string;
  current_step_description?: string;
  /** 已耗时（秒） */
  elapsed_time?: number;
  /** 预计剩余（秒） */
  remaining_time?: number;
  steps?: TaskStep[];
  error_message?: string;
}

/** 任务结果（GET /api/analysis/tasks/{id}/result 的 data，仅取 H5 需要的字段） */
export interface TaskResultData {
  analysis_id?: string | null;
}

/** 查询任务进度（需登录；静默模式，错误由调用方判定，如 404 / 网络失败） */
export async function getTaskStatus(taskId: string): Promise<TaskStatusData> {
  const data = await request<TaskStatusData>({
    url: `/api/analysis/tasks/${encodeURIComponent(taskId)}/status`,
    method: "GET",
    silent: true,
  });
  return data || {};
}

/** 查询任务结果，用于取得 analysis_id（需登录；静默模式） */
export async function getTaskResult(taskId: string): Promise<TaskResultData> {
  const data = await request<TaskResultData>({
    url: `/api/analysis/tasks/${encodeURIComponent(taskId)}/result`,
    method: "GET",
    silent: true,
  });
  return data || {};
}
