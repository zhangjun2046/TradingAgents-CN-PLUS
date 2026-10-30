import { describe, expect, it, vi } from 'vitest'
import {
  copyText,
  filenameFromDisposition,
  isWechatUserAgent,
  parseDownloadError,
  shareDownloadRequest,
  shareDownloadUrl,
} from '../exportShare'

describe('isWechatUserAgent', () => {
  it('识别微信内置浏览器', () => {
    expect(isWechatUserAgent('Mozilla/5.0 MicroMessenger/8.0.0')).toBe(true)
    expect(isWechatUserAgent('micromessenger')).toBe(true)
  })

  it('系统浏览器不是微信', () => {
    expect(isWechatUserAgent('Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36')).toBe(false)
    expect(isWechatUserAgent('')).toBe(false)
  })
})

describe('shareDownloadRequest', () => {
  it('指向免登录导出地址且不带 Authorization', () => {
    const request = shareDownloadRequest('tok en/1', 'pdf')
    expect(request.url).toBe(shareDownloadUrl('tok en/1', 'pdf'))
    expect(request.url).toBe('/api/reports/share/tok%20en%2F1/download?format=pdf')
    expect(request.init.method).toBe('GET')
    expect(request.init.headers).toBeUndefined()
    expect(JSON.stringify(request.init)).not.toContain('Authorization')
  })
})

describe('parseDownloadError', () => {
  it('429 与 404 / 410 使用固定提示', () => {
    expect(parseDownloadError(429, '{"detail":"其他"}')).toBe('下载过于频繁，请稍后再试')
    expect(parseDownloadError(404, '')).toBe('请返回报告列表重新打开')
    expect(parseDownloadError(410, '{"detail":"gone"}')).toBe('请返回报告列表重新打开')
  })

  it('其他状态优先展示后端 detail', () => {
    expect(parseDownloadError(400, '{"detail":"PDF 导出功能不可用。"}')).toBe('PDF 导出功能不可用。')
    expect(parseDownloadError(500, 'not-json')).toBe('导出失败，请稍后重试')
  })
})

describe('filenameFromDisposition', () => {
  it('优先使用 UTF-8 文件名', () => {
    const header =
      "attachment; filename=\"report.pdf\"; filename*=UTF-8''000001_2026-10-20_HunterAgent.pdf"
    expect(filenameFromDisposition(header, 'fallback.pdf')).toBe('000001_2026-10-20_HunterAgent.pdf')
  })

  it('没有响应头时用兜底名', () => {
    expect(filenameFromDisposition(null, 'report.md')).toBe('report.md')
  })
})

describe('copyText', () => {
  it('安全上下文优先走 clipboard，并在等待前同步复制一次', async () => {
    const clipboardWrite = vi.fn().mockResolvedValue(undefined)
    const fallbackCopy = vi.fn().mockReturnValue(true)
    await expect(
      copyText('https://example.com/s/abc', {
        isSecureContext: true,
        clipboardWrite,
        fallbackCopy,
      })
    ).resolves.toBe('clipboard')
    expect(fallbackCopy).toHaveBeenCalledWith('https://example.com/s/abc')
    expect(clipboardWrite).toHaveBeenCalledWith('https://example.com/s/abc')
  })

  it('clipboard 失败时回退 execCommand', async () => {
    const fallbackCopy = vi.fn().mockReturnValue(true)
    await expect(
      copyText('http://192.168.1.2/s/abc', {
        isSecureContext: true,
        clipboardWrite: vi.fn().mockRejectedValue(new Error('denied')),
        fallbackCopy,
      })
    ).resolves.toBe('execCommand')
    expect(fallbackCopy).toHaveBeenCalledWith('http://192.168.1.2/s/abc')
  })

  it('非安全上下文不调用 clipboard', async () => {
    const clipboardWrite = vi.fn()
    const fallbackCopy = vi.fn().mockReturnValue(false)
    await expect(
      copyText('http://localhost/s/abc', {
        isSecureContext: false,
        clipboardWrite,
        fallbackCopy,
      })
    ).resolves.toBe('failed')
    expect(clipboardWrite).not.toHaveBeenCalled()
  })
})
