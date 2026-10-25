/**
 * 分析师配置常量（复制自 PC frontend/src/constants/analysts.ts，保持 ID 与中文名一致）。
 */

export interface Analyst {
  id: "market" | "fundamentals" | "news" | "social";
  name: string;
  description: string;
  /** 卡片图标（简单字符，避免引入图标库） */
  icon: string;
}

export const ANALYSTS: Analyst[] = [
  {
    id: "market",
    name: "市场分析师",
    description: "分析市场趋势、行业动态和宏观经济环境",
    icon: "↗",
  },
  {
    id: "fundamentals",
    name: "基本面分析师",
    description: "分析公司财务状况、业务模式和竞争优势",
    icon: "▥",
  },
  {
    id: "news",
    name: "新闻分析师",
    description: "分析相关新闻、公告和市场事件的影响",
    icon: "▤",
  },
  {
    id: "social",
    name: "社媒分析师",
    description: "分析社交媒体情绪、投资者心理和舆论导向",
    icon: "◌",
  },
];

/** H5 默认选中的分析师（需求 5.1.1：市场 + 基本面 + 新闻） */
export const DEFAULT_ANALYST_IDS: Analyst["id"][] = [
  "market",
  "fundamentals",
  "news",
];

/** A 股不支持社媒分析（国内数据源限制，与现网一致） */
export const SOCIAL_ANALYST_ID: Analyst["id"] = "social";

/** 中文名称 → 英文 ID（提交载荷使用 ID） */
export const ANALYST_NAME_TO_ID_MAP: Record<string, string> = Object.fromEntries(
  ANALYSTS.map((a) => [a.name, a.id])
);

export function convertAnalystNamesToIds(names: string[]): string[] {
  return names.map((n) => ANALYST_NAME_TO_ID_MAP[n] || n);
}
