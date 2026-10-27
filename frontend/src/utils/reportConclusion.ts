/**
 * 岗位结论提取（纯函数）。
 *
 * 观点标签和一句话必须来自同一句正文原句；否定说法或对不上时不展示这句话。
 * 表和图只来自正文里已有的 Markdown 表格，不编造指标。
 */

export type Stance = 'bullish' | 'bearish' | 'neutral' | 'unknown'

export const STANCE_LABEL: Record<Stance, string> = {
  bullish: '看多',
  bearish: '看空',
  neutral: '中性',
  unknown: '未识别',
}

const STANCE_WORDS: Array<{ stance: Exclude<Stance, 'unknown'>; words: string[] }> = [
  { stance: 'bearish', words: ['卖出', '减持', '看空'] },
  { stance: 'bullish', words: ['买入', '增持', '看多'] },
  { stance: 'neutral', words: ['持有', '观望'] },
]

/** 紧挨关键词的否定，避免「无明显」这类远处的「无」误伤。 */
const NEGATION_TAIL = /(?:不建议|不要|无法|并非|避免|不宜|不是|不算|不能|不会|不可|不再|并不|不|未|勿|别)$/

/** 「持有周期 / 买入价 / 卖出价」不是观点，只是期限或价位。 */
const TRAILING_BLOCK: Record<string, string> = {
  持有: '人者量期周',
  买入: '价',
  卖出: '价',
  增持: '价',
  减持: '价',
}

export interface Conclusion {
  stance: Stance
  /** 空字符串表示不展示一句话 */
  sentence: string
}

export interface ExtractedTable {
  caption: string
  headers: string[]
  rows: string[][]
}

export interface ExtractedChartItem {
  label: string
  values: number[]
  /** 与单元格原文一致（仅去掉 Markdown 标记） */
  displays: string[]
}

export interface ExtractedChart {
  title: string
  unit: string
  series: string[]
  items: ExtractedChartItem[]
}

export interface RoleExtract {
  conclusion: Conclusion
  table: ExtractedTable | null
  chart: ExtractedChart | null
}

const UNKNOWN: Conclusion = { stance: 'unknown', sentence: '' }

interface RawTable {
  caption: string
  headers: string[]
  rows: string[][]
  headerLine: number
  next: number
  valid: boolean
}

/** 去掉代码块和表格后的正文，避免表格里的「买入」被当成观点。 */
function proseOnly(markdown: string): string {
  const lines = stripFences(markdown).split(/\r?\n/)
  const kept: string[] = []
  let index = 0
  while (index < lines.length) {
    if (isTableStart(lines, index)) {
      index = readTable(lines, index).next
      continue
    }
    kept.push(lines[index])
    index += 1
  }
  return kept.join('\n')
}

function stripFences(markdown: string): string {
  return markdown.replace(/```[\s\S]*?```/g, '')
}

/** 去掉标记后的可读文本，一句话必须是它的子串。 */
export function plainText(markdown: string): string {
  return stripFences(markdown)
    .split(/\r?\n/)
    .map((line) => {
      if (isSeparatorRow(line)) return ''
      if (isPipeRow(line)) return splitCells(line).map(stripInline).join('')
      return stripInline(line)
    })
    .filter((line) => line.length > 0)
    .join('\n')
}

/** 折叠按钮上的字数：去掉标记和空白。 */
export function plainTextLength(markdown: string): number {
  return plainText(markdown).replace(/\s+/g, '').length
}

export function extractRoleView(markdown: string): RoleExtract {
  const source = markdown || ''
  const conclusion = extractConclusion(proseOnly(source))
  const table = pickTable(source)
  return {
    conclusion,
    table,
    chart: table ? chartFromTable(table) : null,
  }
}

function extractConclusion(prose: string): Conclusion {
  const verdict = verdictFromEnd(prose)
  if (verdict.stance !== 'unknown') return verdict

  const sections = findConclusionSections(prose)
  const scopes = sections.length > 0 ? [...sections].reverse() : [firstProseParagraph(prose)]
  for (const scope of scopes) {
    const conclusion = conclusionFromScope(scope, prose)
    if (conclusion.stance !== 'unknown') return conclusion
  }
  return UNKNOWN
}

function conclusionFromScope(scope: string, prose: string): Conclusion {
  if (!scope.trim()) return UNKNOWN
  const found = findStanceSentence(scope)
  if (!found) return UNKNOWN

  const cleaned = stripInline(found.raw).replace(/\s+/g, ' ').trim()
  if (!cleaned) return UNKNOWN

  // 完整保留观点所在原句，不截断：观点关键词常落在句末，
  // 硬截断会切掉关键词，造成标签与可见句不一致、结论以「…」结尾。
  if (!plainText(prose).includes(cleaned)) return UNKNOWN
  return { stance: found.stance, sentence: cleaned }
}

/** 文末裁决句。没有「结论 / 建议」标题时，主席常把评级写在这里。 */
const VERDICT_LEAD = /最终裁决|最终决策|最终建议/

/** 从后往前找带裁决字样、且含有效观点词的原句。 */
function verdictFromEnd(prose: string): Conclusion {
  const sentences = prose
    .split(/[。！？；\n]+/)
    .map((part) => part.trim())
    .filter((part) => part.length > 0)
  for (let index = sentences.length - 1; index >= 0; index -= 1) {
    const raw = sentences[index]
    if (!VERDICT_LEAD.test(stripInline(raw))) continue
    const conclusion = conclusionFromScope(raw, prose)
    if (conclusion.stance !== 'unknown') return conclusion
  }
  return UNKNOWN
}

/** 文中每个「结论 / 建议」小节。后出现的小节优先，避免中段标题挡住文末的操作建议。 */
function findConclusionSections(prose: string): string[] {
  const lines = prose.split(/\r?\n/)
  const sections: string[] = []
  let index = 0
  while (index < lines.length) {
    const matched = lines[index].match(/^(#{1,6})\s+(.*(?:结论|建议).*)$/)
    if (!matched) {
      index += 1
      continue
    }
    const level = matched[1].length
    const body = [matched[2]]
    let next = index + 1
    for (; next < lines.length; next += 1) {
      const heading = lines[next].match(/^(#{1,6})\s+/)
      if (heading && heading[1].length <= level) break
      body.push(lines[next])
    }
    sections.push(body.join('\n'))
    index = next
  }
  return sections
}

function firstProseParagraph(prose: string): string {
  const lines = prose.split(/\r?\n/)
  const collected: string[] = []
  for (const line of lines) {
    const text = line.trim()
    if (!text) {
      if (collected.length > 0) break
      continue
    }
    if (/^#{1,6}\s+/.test(text) || /^[-*_]{3,}$/.test(text)) {
      if (collected.length > 0) break
      continue
    }
    collected.push(line)
  }
  return collected.join('\n')
}

function findStanceSentence(text: string): { raw: string; stance: Exclude<Stance, 'unknown'> } | null {
  const sentences = text
    .split(/[。！？；\n]+/)
    .map((part) => part.trim())
    .filter((part) => part.length > 0)

  for (let index = sentences.length - 1; index >= 0; index -= 1) {
    const raw = sentences[index]
    const stance = stanceOf(stripInline(raw))
    if (stance) return { raw, stance }
  }
  return null
}

function stanceOf(sentence: string): Exclude<Stance, 'unknown'> | null {
  let bestIndex = -1
  let best: Exclude<Stance, 'unknown'> | null = null
  for (const rule of STANCE_WORDS) {
    for (const word of rule.words) {
      let from = 0
      while (from < sentence.length) {
        const index = sentence.indexOf(word, from)
        if (index < 0) break
        const blocked = isBlocked(sentence, word, index) || isNegated(sentence, index, word) || isQuoted(sentence, index)
        if (!blocked && index >= bestIndex) {
          bestIndex = index
          best = rule.stance
        }
        from = index + word.length
      }
    }
  }
  return best
}

function isNegated(sentence: string, index: number, word: string): boolean {
  const before = sentence.slice(0, index).replace(/[\s,，、：:；;]+$/g, '')
  if (NEGATION_TAIL.test(before)) return true
  // 「此刻买入，不是……」：否定在关键词后面，整句也不是正向建议
  const after = sentence.slice(index + word.length, index + word.length + 16)
  return /(?:不是|不建议|并非|不要)/.test(after)
}

/** 引号里的观点是在转述别人，不当作本岗结论。 */
function isQuoted(sentence: string, index: number): boolean {
  let ascii = false
  let curly = 0
  let corner = 0
  let white = 0
  for (let cursor = 0; cursor < index; cursor += 1) {
    const char = sentence.charAt(cursor)
    if (char === '"') ascii = !ascii
    else if (char === '“') curly += 1
    else if (char === '”') curly = Math.max(0, curly - 1)
    else if (char === '「') corner += 1
    else if (char === '」') corner = Math.max(0, corner - 1)
    else if (char === '『') white += 1
    else if (char === '』') white = Math.max(0, white - 1)
  }
  return ascii || curly > 0 || corner > 0 || white > 0
}

function isBlocked(sentence: string, word: string, index: number): boolean {
  const block = TRAILING_BLOCK[word]
  if (!block) return false
  const next = sentence.charAt(index + word.length)
  if (!next) return false
  return block.includes(next)
}

function stripInline(line: string): string {
  let text = line.trim()
  text = text.replace(/^#{1,6}\s+/, '')
  text = text.replace(/^>\s?/, '')
  text = text.replace(/^[-*+]\s+/, '')
  text = text.replace(/^\d+\.\s+/, '')
  text = text.replace(/!\[[^\]]*]\([^)]*\)/g, '')
  text = text.replace(/\[([^\]]*)]\([^)]*\)/g, '$1')
  for (let round = 0; round < 3; round += 1) {
    text = text.replace(/(\*\*|__)(.*?)\1/g, '$2')
    text = text.replace(/(\*|_)(.*?)\1/g, '$2')
  }
  text = text.replace(/`([^`]*)`/g, '$1')
  // 句号切开后，成对标记可能只剩开头的 **，去掉残留才能和全文对上
  text = text.replace(/\*\*|__|[*_`]/g, '')
  return text.trim()
}

function pickTable(markdown: string): ExtractedTable | null {
  const lines = stripFences(markdown).split(/\r?\n/)
  const tables = collectTables(lines)
  const span = conclusionSpan(lines)
  const inSection = span
    ? tables.filter((table) => table.headerLine >= span.start && table.headerLine < span.end)
    : []
  const chosen = inSection.find((table) => table.valid) || tables.find((table) => table.valid)
  if (!chosen) return null
  return { caption: chosen.caption, headers: chosen.headers, rows: chosen.rows }
}

function conclusionSpan(lines: string[]): { start: number; end: number } | null {
  let start = -1
  let level = 6
  for (let index = 0; index < lines.length; index += 1) {
    const matched = lines[index].match(/^(#{1,6})\s+.*(?:结论|建议)/)
    if (!matched) continue
    start = index
    level = matched[1].length
    break
  }
  if (start < 0) return null
  let end = lines.length
  for (let index = start + 1; index < lines.length; index += 1) {
    const matched = lines[index].match(/^(#{1,6})\s+/)
    if (matched && matched[1].length <= level) {
      end = index
      break
    }
  }
  return { start, end }
}

function collectTables(lines: string[]): RawTable[] {
  const tables: RawTable[] = []
  let index = 0
  while (index < lines.length) {
    if (isTableStart(lines, index)) {
      const table = readTable(lines, index)
      tables.push(table)
      index = table.next
      continue
    }
    index += 1
  }
  return tables
}

function isTableStart(lines: string[], index: number): boolean {
  return index + 1 < lines.length && isPipeRow(lines[index]) && isSeparatorRow(lines[index + 1])
}

function readTable(lines: string[], start: number): RawTable {
  const headers = splitCells(lines[start]).map(stripInline)
  const width = headers.length
  const rows: string[][] = []
  let valid = width >= 2 && isSeparatorRow(lines[start + 1])
  let index = start + 2
  while (index < lines.length && isPipeRow(lines[index]) && !isSeparatorRow(lines[index])) {
    const cells = splitCells(lines[index]).map(stripInline)
    if (cells.length !== width) valid = false
    rows.push(padCells(cells, width))
    index += 1
  }
  if (rows.length === 0) valid = false
  return {
    caption: captionBefore(lines, start),
    headers,
    rows,
    headerLine: start,
    next: index,
    valid,
  }
}

function padCells(cells: string[], width: number): string[] {
  const next = cells.slice(0, width)
  while (next.length < width) next.push('')
  return next
}

function captionBefore(lines: string[], headerIndex: number): string {
  for (let index = headerIndex - 1; index >= 0; index -= 1) {
    const text = lines[index].trim()
    if (!text) continue
    const matched = text.match(/^#{1,6}\s+(.+)$/)
    return matched ? stripInline(matched[1]) : ''
  }
  return ''
}

function isPipeRow(line: string): boolean {
  return line.includes('|') && splitCells(line).length >= 2
}

function isSeparatorRow(line: string): boolean {
  const cells = splitCells(line)
  return cells.length >= 2 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.trim()))
}

function splitCells(line: string): string[] {
  let text = line.trim()
  if (text.startsWith('|')) text = text.slice(1)
  if (text.endsWith('|')) text = text.slice(0, -1)
  return text.split('|').map((cell) => cell.trim())
}

const NUMBER_RE = /^(-?\d+(?:\.\d+)?)(%|％|倍|亿元|万元|元|亿|万)?$/

function parseNumeric(raw: string): { value: number; unit: string } | null {
  const compact = raw.trim().replace(/,/g, '').replace(/\s+/g, '')
  const matched = compact.match(NUMBER_RE)
  if (!matched) return null
  const value = Number(matched[1])
  if (!Number.isFinite(value)) return null
  const unit = matched[2] === '％' ? '%' : matched[2] || ''
  return { value, unit }
}

function chartFromTable(table: ExtractedTable): ExtractedChart | null {
  if (table.rows.length < 2 || table.headers.length < 2) return null

  const labelCol = table.headers.findIndex((_, column) =>
    table.rows.some((row) => parseNumeric(row[column] || '') === null)
  )
  if (labelCol < 0) return null

  const numericCols: Array<{ index: number; unit: string; name: string }> = []
  for (let column = 0; column < table.headers.length; column += 1) {
    if (column === labelCol) continue
    const parsed = table.rows.map((row) => parseNumeric(row[column] || ''))
    if (parsed.some((item) => item === null)) continue
    const units = new Set(parsed.map((item) => item!.unit))
    if (units.size !== 1 || parsed.length < 2) continue
    numericCols.push({
      index: column,
      unit: parsed[0]!.unit,
      name: table.headers[column] || '',
    })
  }
  if (numericCols.length === 0) return null

  const unit = numericCols[0].unit
  const seriesCols = numericCols.filter((column) => column.unit === unit).slice(0, 2)
  const items = table.rows
    .map((row) => {
      const label = (row[labelCol] || '').trim()
      return {
        label,
        values: seriesCols.map((column) => parseNumeric(row[column.index] || '')!.value),
        displays: seriesCols.map((column) => (row[column.index] || '').trim()),
      }
    })
    .filter((item) => item.label.length > 0)

  if (items.length < 2) return null
  const series = seriesCols.map((column) => column.name)
  return {
    title: table.caption || series.filter((name) => name.length > 0).join('、'),
    unit,
    series,
    items,
  }
}
