import dayjs from "dayjs";
import { MARKETS, type MarketType } from "@/constants/analysis";

export interface CodeValidation {
  /** 是否为空（空时不展示错误，只在提交时提示必填） */
  empty: boolean;
  valid: boolean;
  /** 规范化后的代码（去空白、转大写） */
  normalized: string;
  message: string;
}

/** 按市场校验股票代码；美股字母统一转大写 */
export function validateStockCode(
  code: string,
  market: MarketType
): CodeValidation {
  const normalized = (code || "").trim().toUpperCase();
  const option = MARKETS.find((m) => m.value === market) || MARKETS[0];
  if (!normalized) {
    return { empty: true, valid: false, normalized, message: "请输入股票代码" };
  }
  if (!option.pattern.test(normalized)) {
    return {
      empty: false,
      valid: false,
      normalized,
      message: `${option.value}代码格式不正确（${option.hint}）`,
    };
  }
  return {
    empty: false,
    valid: true,
    normalized,
    message: `${option.value}代码格式正确`,
  };
}

/** 今天的日期字符串 YYYY-MM-DD */
export function today(): string {
  return dayjs().format("YYYY-MM-DD");
}

/** 是否为未来日期 */
export function isFutureDate(date: string): boolean {
  return dayjs(date).isAfter(dayjs(), "day");
}
