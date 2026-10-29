import { tokenStorage } from "@/utils/storage";

const LOGIN_REQUIRED = ["/pages/reports/list", "/pages/auth/change-password"];

export function pathNeedsLogin(url: string): boolean {
  let path = url.split("?")[0];
  if (path && !path.startsWith("/")) path = `/${path}`;
  return LOGIN_REQUIRED.some((p) => path === p);
}

export function ensureLogin(redirect?: string): boolean {
  if (tokenStorage.getToken()) return true;
  const target = redirect || "/pages/analysis/single";
  const url = `/pages/auth/login?redirect=${encodeURIComponent(target)}`;
  uni.navigateTo({
    url,
    fail: () => uni.reLaunch({ url }),
  });
  return false;
}

export function goAfterLogin(redirect: string) {
  const target = redirect || "/pages/analysis/single";
  const tabRoots = [
    "/pages/analysis/single",
    "/pages/reports/list",
    "/pages/mine/index",
  ];
  if (tabRoots.some((p) => target.startsWith(p))) {
    uni.switchTab({ url: target.split("?")[0] });
    return;
  }
  uni.reLaunch({ url: target });
}

export function installAuthInterceptors() {
  const wrap = (args: { url?: string }) => {
    const url = args.url || "";
    if (pathNeedsLogin(url) && !tokenStorage.getToken()) {
      ensureLogin(url.startsWith("/") ? url : `/${url}`);
      return false;
    }
    return args;
  };
  uni.addInterceptor("navigateTo", { invoke: wrap });
  uni.addInterceptor("redirectTo", { invoke: wrap });
  uni.addInterceptor("switchTab", { invoke: wrap });
}
