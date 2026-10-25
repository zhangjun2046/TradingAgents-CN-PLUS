/**
 * 单股分析表单常量：市场、深度档位、股票代码规则。
 */

export type MarketType = "A股" | "美股" | "港股";

export interface MarketOption {
  value: MarketType;
  label: string;
  /** 市场标识小标签 */
  badge: string;
  /** 输入格式提示 */
  hint: string;
  /** 代码格式（提交前已转大写） */
  pattern: RegExp;
  placeholder: string;
}

export const MARKETS: MarketOption[] = [
  {
    value: "A股",
    label: "A股市场",
    badge: "CN",
    hint: "6位数字",
    pattern: /^\d{6}$/,
    placeholder: "如 000001",
  },
  {
    value: "美股",
    label: "美股市场",
    badge: "US",
    hint: "1-5位字母",
    pattern: /^[A-Za-z.]{1,5}$/,
    placeholder: "如 AAPL",
  },
  {
    value: "港股",
    label: "港股市场",
    badge: "HK",
    hint: "1-5位数字",
    pattern: /^\d{1,5}$/,
    placeholder: "如 00700",
  },
];

export const DEFAULT_MARKET: MarketType = "A股";

export interface DepthLevel {
  level: 1 | 2 | 3 | 4 | 5;
  /** 提交给后端的中文档位名（与 PC getDepthDescription 一致） */
  name: "快速" | "基础" | "标准" | "深度" | "全面";
  /** 档位按钮副标题 */
  subtitle: string;
  /** 说明条标题，如「3级 - 标准分析」 */
  title: string;
  description: string;
  time: string;
  recommended?: boolean;
}

export const DEPTH_LEVELS: DepthLevel[] = [
  {
    level: 1,
    name: "快速",
    subtitle: "快速",
    title: "1级 - 快速分析",
    description: "基础数据概览，快速决策",
    time: "约 2-5 分钟",
  },
  {
    level: 2,
    name: "基础",
    subtitle: "基础",
    title: "2级 - 基础分析",
    description: "常规投资决策",
    time: "约 3-6 分钟",
  },
  {
    level: 3,
    name: "标准",
    subtitle: "标准",
    title: "3级 - 标准分析",
    description: "技术面 + 基本面综合研判（推荐）",
    time: "约 4-8 分钟",
    recommended: true,
  },
  {
    level: 4,
    name: "深度",
    subtitle: "深度",
    title: "4级 - 深度分析",
    description: "多轮辩论，深度研究",
    time: "约 6-11 分钟",
  },
  {
    level: 5,
    name: "全面",
    subtitle: "全面",
    title: "5级 - 全面分析",
    description: "最全面的分析报告",
    time: "约 8-16 分钟",
  },
];

export const DEFAULT_DEPTH_LEVEL = 3;

/** 隐藏项：H5 不渲染，提交固定默认值（需求 5.1.2） */
export const HIDDEN_DEFAULTS = {
  include_sentiment: true,
  include_risk: true,
  language: "zh-CN",
} as const;

/** 当前进行中任务的 sessionStorage 键（P3.4 恢复进度使用） */
export const CURRENT_TASK_KEY = "ha-current-task";
