/**
 * 分享页文末套话。正文中的「风险提示」是分析内容，不在此列。
 * 页底黄色「风险提示与免责声明」单独展示。
 */
const DISCLAIMER_START = /^(?:免责声明|重要声明|风险提示与免责声明)\s*[:：]?/

const SOURCE_LINE = /^(?:>\s*)?(?:\*\*|__)?\s*数据来源\s*(?:\*\*|__)?\s*[:：]/

const HORIZONTAL_RULE = /^[-*_]{3,}$/

/** 去掉引用、标题和加粗/斜体标记，便于识别「*免责声明：…*」这类单行套话。 */
function unwrapLead(line: string): string {
  let text = line.trim()
  for (let i = 0; i < 4; i += 1) {
    const next = text
      .replace(/^>\s*/, '')
      .replace(/^#{1,6}\s*/, '')
      .replace(/^(?:\*\*|__)/, '')
      .replace(/^\*\s*/, '')
      .replace(/^_\s*/, '')
      .trim()
    if (next === text) break
    text = next
  }
  return text
}

function isDisclaimerLine(line: string): boolean {
  return DISCLAIMER_START.test(unwrapLead(line))
}

function isSourceLine(line: string): boolean {
  return SOURCE_LINE.test(line.trim())
}

/**
 * 从最后一处文末声明标题删到结尾。声明后面的「数据来源」行保留。
 * 没有声明时原样返回。
 */
export function stripTrailingDisclaimer(content: string): string {
  if (!content) return content
  const lines = content.split(/\r?\n/)
  let cut = -1
  for (let index = 0; index < lines.length; index += 1) {
    if (isDisclaimerLine(lines[index])) cut = index
  }
  if (cut === -1) return content

  const head = lines.slice(0, cut)
  while (head.length > 0) {
    const last = head[head.length - 1].trim()
    if (!last || HORIZONTAL_RULE.test(last)) {
      head.pop()
      continue
    }
    break
  }
  const sources = lines.slice(cut + 1).filter((line) => isSourceLine(line))
  const merged = sources.length > 0 ? [...head, '', ...sources] : head
  return merged.join('\n').trimEnd()
}
