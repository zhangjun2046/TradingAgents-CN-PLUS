import { request } from "./request";
import { tokenStorage } from "@/utils/storage";
import {
  FALLBACK_PUBLIC_MODELS,
  type PublicModelsData,
} from "@/constants/models";

export interface PublicModelsResult {
  data: PublicModelsData;
  /** 是否使用了内置兜底列表 */
  fromFallback: boolean;
}

/** 返回内置列表的深拷贝，避免调用方修改常量 */
function buildFallback(reason: string): PublicModelsResult {
  console.info("[Config] public models fallback", reason);
  return {
    data: JSON.parse(JSON.stringify(FALLBACK_PUBLIC_MODELS)) as PublicModelsData,
    fromFallback: true,
  };
}

/** 校验接口返回是否符合 tech_solution 7.3 契约 */
function isValidPublicModels(data: unknown): data is PublicModelsData {
  const d = data as PublicModelsData | null | undefined;
  return !!d && Array.isArray(d.models) && d.models.length > 0;
}

/**
 * 拉取公开模型列表（契约：GET /api/config/public/models）。
 * 该接口要求登录；未登录、接口 404 或失败、返回为空时，退回按契约结构写好的内置列表。
 * 集成后接口可用，自动走真实数据，无需改代码。
 */
export async function getPublicModels(): Promise<PublicModelsResult> {
  // 未登录时不请求，避免 401 触发全局跳转登录页（单股分析页允许未登录浏览）
  if (!tokenStorage.getToken()) {
    return buildFallback("not-logged-in");
  }
  try {
    const data = await request<PublicModelsData>({
      url: "/api/config/public/models",
      method: "GET",
      silent: true,
    });
    if (!isValidPublicModels(data)) {
      return buildFallback("empty-response");
    }
    console.info("[Config] public models loaded", data.models.length);
    return { data, fromFallback: false };
  } catch (e) {
    const status = (e as { statusCode?: number })?.statusCode ?? 0;
    return buildFallback(status ? `http-${status}` : "network-error");
  }
}
