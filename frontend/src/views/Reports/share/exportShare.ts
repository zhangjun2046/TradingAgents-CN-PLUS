/**
 * 分享页免登录导出与微信内复制链接（纯函数，便于单测）。
 *
 * 下载地址对齐 doc/handoff/Backend-API-Report.md 2.3：
 * GET /api/reports/share/{token}/download?format=markdown|pdf|docx
 * 不带登录头。微信 UA 只负责决定是否展示引导，不改下载地址。
 */

export type ShareExportFormat = 'markdown' | 'pdf' | 'docx'

export interface ShareExportOption {
  format: ShareExportFormat
  title: string
  hint: string
}

/** 弹层里的顺序与原型图一致：PDF、Word、Markdown */
export const SHARE_EXPORT_FORMATS: ShareExportOption[] = [
  { format: 'pdf', title: 'PDF 报告 (.pdf)', hint: '排版固定，适合阅读与打印' },
  { format: 'docx', title: 'Word 文档 (.docx)', hint: '支持二次编辑与批注整理' },
  { format: 'markdown', title: 'Markdown (.md)', hint: '纯文本结构，适合接入知识库与笔记' },
]

export type CopyResult = 'clipboard' | 'execCommand' | 'failed'

export interface CopyEnvironment {
  isSecureContext: boolean
  /** 安全上下文下的 clipboard.writeText；不可用时为 null */
  clipboardWrite: ((value: string) => Promise<void>) | null
  /** 非 HTTPS 或 clipboard 失败时的回退 */
  fallbackCopy: (value: string) => boolean
}

const INVALID_LINK_HINT = '请返回报告列表重新打开'
const RATE_LIMIT_HINT = '下载过于频繁，请稍后再试'
const GENERIC_EXPORT_ERROR = '导出失败，请稍后重试'

/** 微信内置浏览器（含企业微信的 MicroMessenger 标识） */
export function isWechatUserAgent(userAgent: string): boolean {
  return /MicroMessenger/i.test(userAgent || '')
}

export function shareDownloadUrl(token: string, format: ShareExportFormat): string {
  return `/api/reports/share/${encodeURIComponent(token)}/download?format=${format}`
}

/**
 * 免登录下载请求。故意不设置 Authorization，避免把登录态下载和公开导出混在一起。
 */
export function shareDownloadRequest(
  token: string,
  format: ShareExportFormat
): { url: string; init: RequestInit } {
  return {
    url: shareDownloadUrl(token, format),
    init: { method: 'GET' },
  }
}

export function parseDownloadError(status: number, body: string): string {
  if (status === 429) return RATE_LIMIT_HINT
  if (status === 404 || status === 410) return INVALID_LINK_HINT
  const detail = readErrorDetail(body)
  return detail || GENERIC_EXPORT_ERROR
}

export function filenameFromDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback
  const encoded = header.match(/filename\*=UTF-8''([^;]+)/i)
  if (encoded?.[1]) {
    try {
      const name = decodeURIComponent(encoded[1].trim())
      if (name) return name
    } catch (error) {
      console.info('[Share] filename decode failed', error)
    }
  }
  const plain = header.match(/filename="([^"]+)"/i) || header.match(/filename=([^;]+)/i)
  const raw = plain?.[1]?.trim()
  return raw || fallback
}

export function fallbackDownloadName(format: ShareExportFormat, symbol?: string): string {
  const ext = format === 'markdown' ? 'md' : format
  const base = (symbol || 'report').replace(/[^\w.-]+/g, '_') || 'report'
  return `${base}_HunterAgent.${ext}`
}

export async function fetchShareDownload(
  token: string,
  format: ShareExportFormat,
  symbol?: string,
  fetchImpl: typeof fetch = fetch
): Promise<{ blob: Blob; filename: string }> {
  const { url, init } = shareDownloadRequest(token, format)
  console.info('[Share] export', { format })
  const response = await fetchImpl(url, init)
  if (!response.ok) {
    const text = await response.text()
    throw new Error(parseDownloadError(response.status, text))
  }
  const filename = filenameFromDisposition(
    response.headers.get('Content-Disposition'),
    fallbackDownloadName(format, symbol)
  )
  return { blob: await response.blob(), filename }
}

/** 用隐藏链接触发浏览器下载，不把页面导航到接口地址 */
export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.style.display = 'none'
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

export async function copyText(text: string, env: CopyEnvironment = defaultCopyEnvironment()): Promise<CopyResult> {
  if (!text.trim()) return 'failed'
  const canClipboard = Boolean(env.isSecureContext && env.clipboardWrite)
  if (!canClipboard) {
    console.info('clipboard API unavailable, fallback to execCommand')
    return env.fallbackCopy(text) ? 'execCommand' : 'failed'
  }
  // 先同步复制，保留这次点击的用户手势。clipboard 若随后被拒绝，回退已经完成。
  const legacyOk = env.fallbackCopy(text)
  try {
    await env.clipboardWrite!(text)
    return 'clipboard'
  } catch (error) {
    console.info('clipboard API unavailable, fallback to execCommand', error)
    return legacyOk ? 'execCommand' : 'failed'
  }
}

function readErrorDetail(body: string): string {
  if (!body.trim()) return ''
  try {
    const payload = JSON.parse(body) as { detail?: unknown }
    if (typeof payload.detail === 'string' && payload.detail.trim()) return payload.detail.trim()
  } catch {
    // 非 JSON 时不用原文，避免把 HTML 错误页展示给读者
  }
  return ''
}

function defaultCopyEnvironment(): CopyEnvironment {
  const secure = typeof window !== 'undefined' && window.isSecureContext
  const write = typeof navigator !== 'undefined' ? navigator.clipboard?.writeText?.bind(navigator.clipboard) : null
  return {
    isSecureContext: secure,
    clipboardWrite: write ?? null,
    fallbackCopy: fallbackCopyWithInput,
  }
}

function fallbackCopyWithInput(value: string): boolean {
  const input = document.createElement('textarea')
  input.value = value
  input.setAttribute('readonly', 'readonly')
  input.style.position = 'fixed'
  input.style.top = '0'
  input.style.left = '0'
  input.style.opacity = '0'
  document.body.appendChild(input)
  input.focus()
  input.select()
  input.setSelectionRange(0, input.value.length)
  let ok = false
  try {
    ok = document.execCommand('copy')
  } catch (error) {
    console.info('[Share] execCommand copy failed', error)
  }
  document.body.removeChild(input)
  return ok
}
