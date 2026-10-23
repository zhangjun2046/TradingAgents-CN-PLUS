import { tokenStorage } from "@/utils/storage";

const BASE_URL = (import.meta.env.VITE_API_BASE as string) || "";

export interface ApiResponse<T = unknown> {
  success?: boolean;
  data?: T;
  message?: string;
  detail?: string;
}

export function extractErrorMessage(body: unknown, statusCode = 0): string {
  if (typeof body === "string" && body.trim()) return body;
  const data = body as ApiResponse & { detail?: unknown };
  const detail = data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail && typeof detail === "object") {
    const d = detail as { message?: string; code?: string };
    if (d.message) return d.message;
  }
  if (data?.message) return String(data.message);
  if (statusCode === 429) return "请求过于频繁，请稍后重试";
  return "请求失败";
}

export class ApiError extends Error {
  statusCode: number;
  cause?: unknown;

  constructor(message: string, statusCode = 0, cause?: unknown) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.cause = cause;
  }
}

type RequestOptions = UniApp.RequestOptions & {
  /** 跳过自动附带 Authorization（如登录、刷新） */
  skipAuth?: boolean;
  /** 内部：避免刷新后死循环 */
  _retried?: boolean;
};

let refreshing: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) return false;

  return new Promise((resolve) => {
    uni.request({
      url: `${BASE_URL}/api/auth/refresh`,
      method: "POST",
      timeout: 30000,
      data: { refresh_token: refreshToken },
      success: (res) => {
        const body = res.data as ApiResponse<{
          access_token: string;
          refresh_token: string;
        }>;
        if (
          res.statusCode >= 200 &&
          res.statusCode < 300 &&
          body?.success !== false &&
          body?.data?.access_token
        ) {
          tokenStorage.setTokens(
            body.data.access_token,
            body.data.refresh_token || refreshToken
          );
          resolve(true);
          return;
        }
        resolve(false);
      },
      fail: () => resolve(false),
    });
  });
}

function refreshOnce(): Promise<boolean> {
  if (!refreshing) {
    refreshing = doRefresh().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

function redirectToLogin(): void {
  tokenStorage.clear();
  const pages = getCurrentPages();
  const current = pages[pages.length - 1] as { route?: string } | undefined;
  const route = current?.route ? `/${current.route}` : "/pages/analysis/single";
  const redirect = encodeURIComponent(route);
  uni.navigateTo({
    url: `/pages/auth/login?redirect=${redirect}`,
    fail: () => {
      uni.reLaunch({ url: `/pages/auth/login?redirect=${redirect}` });
    },
  });
}

async function retryAfterRefresh<T>(opt: RequestOptions): Promise<T> {
  const ok = await refreshOnce();
  if (!ok) {
    redirectToLogin();
    return Promise.reject(new ApiError("登录已过期，请重新登录", 401));
  }
  return request<T>({ ...opt, _retried: true });
}

function toastAndReject(message: string, statusCode: number): Promise<never> {
  uni.showToast({ title: message, icon: "none" });
  return Promise.reject(new ApiError(message, statusCode));
}

/**
 * uni.request 封装：Bearer、统一响应、401 刷新排队重放。
 */
export function request<T>(opt: RequestOptions): Promise<T> {
  return new Promise((resolve, reject) => {
    const header: Record<string, string> = {
      ...(opt.header as Record<string, string>),
    };
    if (!opt.skipAuth) {
      const token = tokenStorage.getToken();
      if (token) {
        header.Authorization = `Bearer ${token}`;
      }
    }

    const { skipAuth: _skipAuth, _retried: _wasRetried, ...reqOpt } = opt;
    uni.request({
      ...reqOpt,
      url: `${BASE_URL}${opt.url}`,
      header,
      timeout: opt.timeout ?? 30000,
      success: async (res) => {
        if (res.statusCode === 401 && !opt.skipAuth && !opt._retried) {
          try {
            resolve(await retryAfterRefresh<T>(opt));
          } catch (e) {
            reject(e);
          }
          return;
        }

        const body = res.data as ApiResponse<T>;
        if (res.statusCode >= 400 || body?.success === false) {
          const msg = extractErrorMessage(body, res.statusCode);
          try {
            await toastAndReject(String(msg), res.statusCode);
          } catch (e) {
            reject(e);
          }
          return;
        }

        // 兼容 data 包裹与直接返回
        if (body && typeof body === "object" && "data" in body) {
          resolve(body.data as T);
        } else {
          resolve(body as unknown as T);
        }
      },
      fail: (err) => {
        const error = new ApiError("网络异常，请稍后重试", 0, err);
        uni.showToast({ title: error.message, icon: "none" });
        reject(error);
      },
    });
  });
}
