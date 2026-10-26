/** 概览执行摘要最长约 100 字，且必须停在句末。 */
const SUMMARY_MAX_LENGTH = 100

const SENTENCE_END = /[。！？]/

/** 标题、分隔线、表格行不进入摘要，避免把半张表渲染出来。 */
function isSkippableLine(line: string): boolean {
  const text = line.trim()
  if (!text) return true
  if (/^#{1,6}\s+/.test(text)) return true
  if (/^[-*_]{3,}$/.test(text)) return true
  if (text.startsWith('|')) return true
  if (/^\|?[\s|:-]*-{3,}[\s|:-]*$/.test(text)) return true
  return false
}

function proseText(content: string): string {
  return content
    .split(/\r?\n/)
    .filter((line) => !isSkippableLine(line))
    .map((line) => line.replace(/[*_`>#]/g, '').trim())
    .filter(Boolean)
    .join('')
    .replace(/\.{3}$|…$/g, '')
    .trim()
}

/**
 * 从裁决书或已截断的 summary 中取第一句完整中文。
 * 没有句末标点，或第一句超过上限且上限内没有句号时，返回空字符串。
 */
export function formatOverviewSummary(content: unknown): string {
  if (typeof content !== 'string' || !content.trim()) return ''
  const prose = proseText(content)
  if (!prose) return ''

  const firstEnd = prose.search(SENTENCE_END)
  if (firstEnd === -1) return ''
  if (firstEnd < SUMMARY_MAX_LENGTH) return prose.slice(0, firstEnd + 1).trim()

  let lastEnd = -1
  for (let index = 0; index < SUMMARY_MAX_LENGTH && index < prose.length; index += 1) {
    if (SENTENCE_END.test(prose[index])) lastEnd = index
  }
  if (lastEnd === -1) return ''
  return prose.slice(0, lastEnd + 1).trim()
}
