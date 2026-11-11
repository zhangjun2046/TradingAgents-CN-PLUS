import { describe, expect, it } from 'vitest'
import { shouldOfferPwaInstall } from '../pwaInstallGate'

const safari = 'Mozilla/5.0 (iPhone) AppleWebKit Safari'
const wechat = 'Mozilla/5.0 (iPhone) MicroMessenger/8.0.0'

describe('安装到桌面是否提示', () => {
  it('微信里不提示', () => {
    expect(shouldOfferPwaInstall({ userAgent: wechat, path: '/' })).toBe(false)
    expect(shouldOfferPwaInstall({ userAgent: wechat, path: '/login' })).toBe(false)
  })

  it('分享页不提示', () => {
    expect(shouldOfferPwaInstall({ userAgent: safari, path: '/s/abc' })).toBe(false)
    expect(shouldOfferPwaInstall({ userAgent: safari, path: '/s' })).toBe(false)
  })

  it('普通浏览器的其他页面可以提示', () => {
    expect(shouldOfferPwaInstall({ userAgent: safari, path: '/' })).toBe(true)
    expect(shouldOfferPwaInstall({ userAgent: safari, path: '/login' })).toBe(true)
    expect(shouldOfferPwaInstall({ userAgent: safari, path: '/settings' })).toBe(true)
    expect(shouldOfferPwaInstall({ userAgent: safari, path: '/stocks' })).toBe(true)
  })
})
