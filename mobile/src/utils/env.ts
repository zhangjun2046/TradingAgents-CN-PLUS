/**
 * 运行环境相关工具：公开访问地址、分享链接拼装。
 */

/**
 * 公开访问地址（不含结尾斜杠）。
 * 优先读取 VITE_PUBLIC_APP_URL（开发期 H5 在 :3100，分享页在 PC 前端 :3000），
 * 缺省取当前页面 origin（同域部署，tech_solution 2.3）。
 */
export function getPublicAppUrl(): string {
  const configured = String(import.meta.env.VITE_PUBLIC_APP_URL || "").trim();
  const base =
    configured || (typeof window !== "undefined" ? window.location.origin : "");
  return base.replace(/\/+$/, "");
}

/** 拼装免登录分享页地址：{公开地址}/s/{token}。复制给他人时用这个，不带应用内标记。 */
export function buildShareUrl(token: string): string {
  return `${getPublicAppUrl()}/s/${token}`;
}

/** 从 H5 里打开同一份报告时加上 from=app，分享页据此显示「返回报告列表」。 */
export function buildInAppShareUrl(token: string): string {
  const url = new URL(buildShareUrl(token));
  url.searchParams.set("from", "app");
  return url.toString();
}
