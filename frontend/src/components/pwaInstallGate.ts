/** 决定要不要弹出「安装到桌面」。微信和分享报告页都不弹。 */

export function isWechatBrowser(userAgent: string): boolean {
  return /MicroMessenger/i.test(userAgent || '')
}

/** 分享页路由是 /s/:token，不能把 /settings、/stocks 算进去。 */
export function isShareReportPath(path: string): boolean {
  return path === '/s' || path.startsWith('/s/')
}

export function shouldOfferPwaInstall(input: { userAgent: string; path: string }): boolean {
  if (isWechatBrowser(input.userAgent)) return false
  if (isShareReportPath(input.path)) return false
  return true
}
