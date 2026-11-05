import { request } from "./request";
import { tokenStorage } from "@/utils/storage";
import { type PublicModelsData } from "@/constants/models";

export interface PublicModelsResult {
  data: PublicModelsData | null;
  /** 未登录，不请求接口 */
  loggedOut: boolean;
  /** 已登录但请求失败 */
  loadError: boolean;
  /** 已登录且可用名单为空 */
  empty: boolean;
}

/** 校验接口返回。空的 models 也是合法结果，表示当前没有可用模型。 */
function isValidPublicModels(data: unknown): data is PublicModelsData {
  const d = data as PublicModelsData | null | undefined;
  return !!d
    && Array.isArray(d.models)
    && Array.isArray(d.quick_models)
    && Array.isArray(d.deep_models);
}

/**
 * 拉取公开模型列表（契约：GET /api/config/public/models）。
 * 未登录不请求，名单留空。已登录后名单为空或请求失败都不再使用写死模型。
 */
export async function getPublicModels(): Promise<PublicModelsResult> {
  // 未登录时不请求，避免 401 触发全局跳转登录页（单股分析页允许未登录浏览）
  if (!tokenStorage.getToken()) {
    return { data: null, loggedOut: true, loadError: false, empty: false };
  }
  try {
    const data = await request<PublicModelsData>({
      url: "/api/config/public/models",
      method: "GET",
      silent: true,
    });
    if (!isValidPublicModels(data)) {
      return { data: null, loggedOut: false, loadError: true, empty: false };
    }
    console.info("[Config] public models loaded", data.models.length);
    return {
      data,
      loggedOut: false,
      loadError: false,
      empty: data.models.length === 0,
    };
  } catch (e) {
    const status = (e as { statusCode?: number })?.statusCode ?? 0;
    console.info("[Config] public models failed", status || "network-error");
    return { data: null, loggedOut: false, loadError: true, empty: false };
  }
}
