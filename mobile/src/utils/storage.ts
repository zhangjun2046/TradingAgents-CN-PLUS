/**
 * H5 登录态存储：直接读写 window.localStorage，键名与 PC 一致。
 * 不使用 uni.setStorageSync（会包一层 JSON，与 PC 不兼容）。
 */
const TOKEN_KEY = "auth-token";
const REFRESH_KEY = "refresh-token";
const USER_KEY = "user-info";

function getItem(key: string): string {
  if (typeof localStorage === "undefined") return "";
  return localStorage.getItem(key) || "";
}

function setItem(key: string, value: string): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(key, value);
}

function removeItem(key: string): void {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem(key);
}

export const tokenStorage = {
  getToken(): string {
    return getItem(TOKEN_KEY);
  },
  getRefreshToken(): string {
    return getItem(REFRESH_KEY);
  },
  getUserInfo<T = Record<string, unknown>>(): T | null {
    const raw = getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  },
  setTokens(access: string, refresh: string): void {
    setItem(TOKEN_KEY, access);
    setItem(REFRESH_KEY, refresh);
  },
  setUserInfo(user: unknown): void {
    setItem(USER_KEY, JSON.stringify(user));
  },
  clear(): void {
    ;[TOKEN_KEY, REFRESH_KEY, USER_KEY].forEach((k) => removeItem(k));
  },
};
