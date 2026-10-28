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
  unknown: '未识别'
}

const STANCE_WORDS: Array<{ stance: Exclude<Stance, 'unknown'>; words: string[] }> = [
  { stance: 'bearish', words: ['卖出', '减持', '看空', '看跌'] },
  { stance: 'bullish', words: ['买入', '增持', '看多', '看涨'] },
  { stance: 'neutral', words: ['持有', '观望'] }
]

/** 仓位动作只在「最终建议 / 裁决」等显式语境中用于定性，避免普通止损说明误判。 */
const EXPLICIT_POSITION_WORDS: Array<{
  stance: Exclude<Stance, 'unknown'>
  words: string[]
}> = [{ stance: 'bearish', words: ['减仓', '清仓'] }]

/** 紧挨关键词的否定，避免「无明显」这类远处的「无」误伤。 */
const NEGATION_TAIL =
  /(?:不建议|不要|无法|并非|避免|不宜|不是|不算|不能|不会|不可|不再|并不|不|未|勿|别)$/

/** 「持有周期 / 买入价 / 买入机会 / 卖出价」不是本岗评级，只是期限、价位或论据称谓。 */
const TRAILING_BLOCK: Record<string, string> = {
  持有: '人者量期周仓股',
  买入: '价机理',
  卖出: '价',
  增持: '价',
  减持: '价'
}

/** 明确裁决语句优先取引导词后的第一个有效动作，不被后面的适用人群或否定项覆盖。 */
const EXPLICIT_DECISION_LEAD =
  /最终裁决|最终决策|最终建议|最终交易建议|最终交易提案|最终重申|核心建议|投资评级|操作建议|我的建议是|我的裁决|我的决策|我的决定|明确(?:的)?(?:决策|立场|建议)|评级(?:为)?|建议/

/** 「买入，而非观望」中转折后的动作是被排除项，不参与当前观点判定。 */
const REJECTED_ALTERNATIVE = /而非|而不是/

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
    .map(line => {
      if (isSeparatorRow(line)) return ''
      if (isPipeRow(line)) return splitCells(line).map(stripInline).join('')
      return stripInline(line)
    })
    .filter(line => line.length > 0)
    .join('\n')
}

/** 折叠按钮上的字数：去掉标记和空白。 */
export function plainTextLength(markdown: string): number {
  return plainText(markdown).replace(/\s+/g, '').length
}

export function extractRoleView(markdown: string): RoleExtract {
  const source = markdown || ''
  let conclusion = extractConclusion(proseOnly(source))
  if (conclusion.stance === 'unknown') {
    const fromTable = ratingFromSummaryTable(source)
    if (fromTable) conclusion = fromTable
  }
  const table = pickTable(source)
  return {
    conclusion,
    table,
    chart: table ? chartFromTable(table) : null
  }
}

function extractConclusion(prose: string): Conclusion {
  // 最后一句点名结论（投资评级 / 我的建议是 / 最终裁决）就是正文结论
  const strong = scanLeadSentences(prose, STRONG_LEAD)
  if (strong.stance !== 'unknown') return strong

  const sections = findConclusionSections(prose)
  if (sections.length > 0) {
    for (const scope of [...sections].reverse()) {
      const decision = scanLeadSentences(scope, DECISION_LEAD)
      if (decision.stance !== 'unknown') return decision
      const conclusion = conclusionFromScope(scope, prose)
      if (conclusion.stance !== 'unknown') return conclusion
    }
  }

  // 没有结论标题时，再认「给出…建议 / 建议：」；仍没有就只用开头段，避免后文论据改口
  const decision = scanLeadSentences(prose, DECISION_LEAD)
  if (decision.stance !== 'unknown') return decision
  if (sections.length === 0) return conclusionFromScope(firstProseParagraph(prose), prose)
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

/**
 * 正文里点名的结论句。从后往前取最后一句，避免文首标题盖过后文的「我的建议是 / 我的裁决」。
 * 不包含光秃的「建议：」，以免文末风险提示盖过正式评级。
 */
const STRONG_LEAD =
  /最终裁决|最终决策|最终建议|最终交易建议|最终交易提案|最终重申|我的建议是|我的裁决|我的决策|我的决定|投资评级|核心建议|操作建议/

/** 本人决策句：避免后文「买入机会」等论据词盖过真正的卖出/买入结论。 */
const DECISION_LEAD =
  /我的决定|我的建议是|我的裁决|我的决策|最终交易建议|最终交易提案|最终重申|给出[\s\S]{0,20}建议|最终建议|明确(?:的)?(?:决策|立场|建议)|建议[：:]|评级为|评级[：:]|投资评级|核心建议|操作建议/

/** 汇总表里表示本岗评级的行名。普通数据表的「买入」不在此列。 */
const RATING_ROW_LABEL = /^(投资评级|交易建议|投资建议|操作建议|建议操作|最终建议|最终交易提案|最终交易建议)$/

/** 从后往前找带引导词、且能判定观点的原句。 */
function scanLeadSentences(prose: string, lead: RegExp): Conclusion {
  const sentences = prose
    .split(/[。！？；\n]+/)
    .map(part => part.trim())
    .filter(part => part.length > 0)
  for (let index = sentences.length - 1; index >= 0; index -= 1) {
    const raw = sentences[index]
    if (!lead.test(stripInline(raw))) continue
    let conclusion = conclusionFromScope(raw, prose)
    // 「我的决策是：……。持有。」评级词有时落在下一句，仍属同一结论。
    if (conclusion.stance === 'unknown' && index + 1 < sentences.length) {
      conclusion = conclusionFromScope(`${raw}。${sentences[index + 1]}`, prose)
    }
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

function findStanceSentence(
  text: string
): { raw: string; stance: Exclude<Stance, 'unknown'> } | null {
  const sentences = text
    .split(/[。！？；\n]+/)
    .map(part => part.trim())
    .filter(part => part.length > 0)

  for (let index = sentences.length - 1; index >= 0; index -= 1) {
    const raw = sentences[index]
    const stance = stanceOf(stripInline(raw))
    if (stance) return { raw, stance }
  }
  return null
}

function stanceOf(sentence: string): Exclude<Stance, 'unknown'> | null {
  const explicit = explicitStanceOf(sentence)
  if (explicit) return explicit

  const rejectedAt = sentence.search(REJECTED_ALTERNATIVE)
  let bestIndex = -1
  let best: Exclude<Stance, 'unknown'> | null = null
  for (const rule of STANCE_WORDS) {
    for (const word of rule.words) {
      let from = 0
      while (from < sentence.length) {
        const index = sentence.indexOf(word, from)
        if (index < 0) break
        if (rejectedAt >= 0 && index > rejectedAt) {
          from = index + word.length
          continue
        }
        const quoted = isQuoted(sentence, index)
        const blocked =
          isBlocked(sentence, word, index) ||
          isNegated(sentence, index, word) ||
          (quoted && !isOwnRatingQuote(sentence, index))
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

/**
 * 显式结论按引导词后的首个有效动作定性。
 * 例如「最终裁决：持有，暂不买入或卖出」应取“持有”，
 * 「核心建议：卖出或持有现金」应取“卖出”。
 */
function explicitStanceOf(sentence: string): Exclude<Stance, 'unknown'> | null {
  const lead = sentence.match(EXPLICIT_DECISION_LEAD)
  if (lead?.index !== undefined) {
    const start = lead.index + lead[0].length
    const phrase = ratingPhraseStance(sentence.slice(start))
    if (phrase) return phrase
    const found = firstValidStance(sentence, start, Math.min(sentence.length, start + 48))
    if (found) return found
  }

  // 「给出“卖出”建议」的动作位于“建议”之前。
  const give = sentence.match(
    /给出[\s"'“”「」『』（）()]*?(买入|增持|看多|看涨|卖出|减持|看空|看跌|持有|观望)[\s"'“”「」『』（）()]*?建议/
  )
  if (!give) return null
  return stanceForWord(give[1])
}

function firstValidStance(
  sentence: string,
  start: number,
  end: number
): Exclude<Stance, 'unknown'> | null {
  const rejectedAt = sentence.search(REJECTED_ALTERNATIVE)
  const effectiveEnd = rejectedAt >= start ? Math.min(end, rejectedAt) : end
  let firstIndex = Number.POSITIVE_INFINITY
  let first: Exclude<Stance, 'unknown'> | null = null
  for (const rule of [...STANCE_WORDS, ...EXPLICIT_POSITION_WORDS]) {
    for (const word of rule.words) {
      let index = sentence.indexOf(word, start)
      while (index >= 0 && index < effectiveEnd) {
        if (
          !isBlocked(sentence, word, index) &&
          !isNegated(sentence, index, word) &&
          index < firstIndex
        ) {
          firstIndex = index
          first = rule.stance
        }
        index = sentence.indexOf(word, index + word.length)
      }
    }
  }
  return first
}

function stanceForWord(word: string): Exclude<Stance, 'unknown'> | null {
  return STANCE_WORDS.find(rule => rule.words.includes(word))?.stance || null
}

/** 「投资评级：中性偏多 / 中性」紧跟在评级引导词后，中性是主评级。 */
function ratingPhraseStance(text: string): Exclude<Stance, 'unknown'> | null {
  const matched = text.match(/^[\s:：*_"'“”「」]*?(中性偏多|中性偏空|中性|偏多|偏空)/)
  if (!matched) return null
  if (matched[1] === '偏多') return 'bullish'
  if (matched[1] === '偏空') return 'bearish'
  return 'neutral'
}

function isNegated(sentence: string, index: number, word: string): boolean {
  const before = sentence.slice(0, index).replace(/[\s,，、：:；;]+$/g, '')
  if (NEGATION_TAIL.test(before)) return true
  // 否定并列项：「暂不买入或卖出」「避免增持、买入」。
  if (/(?:暂?不|不要|避免|无须|无需)[^，。；]{0,16}(?:或|和|、)$/.test(before)) return true
  // 「此刻买入，不是……」：否定要紧挨关键词。后文另起的「不建议新建仓」不能反过来否定前面的持有。
  const after = sentence.slice(index + word.length, index + word.length + 12)
  return /^(?:[\s,，、：:；;（(]*)(?:不是|不建议|并非|不要)/.test(after)
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

/**
 * 本人给出的评级常写成 给出"卖出"建议 / 评级为"买入"。
 * 这类引号不是转述，应放行；「空头认为"卖出"」不含本模式，仍忽略。
 */
function isOwnRatingQuote(sentence: string, index: number): boolean {
  const giveAt = sentence.lastIndexOf('给出', index)
  if (giveAt >= 0 && sentence.indexOf('建议', index) >= 0) return true

  const before = sentence.slice(Math.max(0, index - 16), index)
  return /(?:评级为|建议为|评级[:：]|建议[:：])[\s"'“”「」『』（(]*$/.test(before)
}

function isBlocked(sentence: string, word: string, index: number): boolean {
  // 「看跌分析师 / 看涨分析师」是角色称谓，不是本岗观点
  if (
    (word === '看跌' || word === '看涨') &&
    sentence.slice(index + word.length).startsWith('分析师')
  ) {
    return true
  }
  const before = sentence.slice(Math.max(0, index - 12), index)
  // 「冒进/盲目买入会导致风险」描述的是反面情景，不是看多建议。
  if (word === '买入' && /(?:冒进|盲目|贸然|追高)$/.test(before)) return true
  // 「退出观望」表示结束观望，不应被识别为中性观点。
  if (word === '观望' && /(?:退出|结束|停止)$/.test(before)) return true
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

/**
 * 正文没有写成句子、只在汇总表里给出评级时，用行名「交易建议 / 投资评级」对应的单元格。
 * 不读普通数据表，避免「建议 | 买入」这种列被当成观点。
 */
function ratingFromSummaryTable(markdown: string): Conclusion | null {
  const lines = stripFences(markdown).split(/\r?\n/)
  const tables = collectTables(lines)
  const readable = plainText(markdown)
  for (let tableIndex = tables.length - 1; tableIndex >= 0; tableIndex -= 1) {
    const table = tables[tableIndex]
    if (!table.valid) continue
    for (let rowIndex = table.rows.length - 1; rowIndex >= 0; rowIndex -= 1) {
      const row = table.rows[rowIndex]
      const label = (row[0] || '').trim()
      const value = (row[1] || '').trim()
      if (!RATING_ROW_LABEL.test(label) || !value) continue
      const stance = stanceOf(value) || ratingPhraseStance(value)
      if (!stance || !readable.includes(value)) continue
      return { stance, sentence: value }
    }
  }
  return null
}

function pickTable(markdown: string): ExtractedTable | null {
  const lines = stripFences(markdown).split(/\r?\n/)
  const tables = collectTables(lines)
  const span = conclusionSpan(lines)
  const inSection = span
    ? tables.filter(table => table.headerLine >= span.start && table.headerLine < span.end)
    : []
  const chosen = inSection.find(table => table.valid) || tables.find(table => table.valid)
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
    valid
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
  return cells.length >= 2 && cells.every(cell => /^:?-{3,}:?$/.test(cell.trim()))
}

function splitCells(line: string): string[] {
  let text = line.trim()
  if (text.startsWith('|')) text = text.slice(1)
  if (text.endsWith('|')) text = text.slice(0, -1)
  return text.split('|').map(cell => cell.trim())
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
    table.rows.some(row => parseNumeric(row[column] || '') === null)
  )
  if (labelCol < 0) return null

  const numericCols: Array<{ index: number; unit: string; name: string }> = []
  for (let column = 0; column < table.headers.length; column += 1) {
    if (column === labelCol) continue
    const parsed = table.rows.map(row => parseNumeric(row[column] || ''))
    if (parsed.some(item => item === null)) continue
    const units = new Set(parsed.map(item => item!.unit))
    if (units.size !== 1 || parsed.length < 2) continue
    numericCols.push({
      index: column,
      unit: parsed[0]!.unit,
      name: table.headers[column] || ''
    })
  }
  if (numericCols.length === 0) return null

  const unit = numericCols[0].unit
  const seriesCols = numericCols.filter(column => column.unit === unit).slice(0, 2)
  const items = table.rows
    .map(row => {
      const label = (row[labelCol] || '').trim()
      return {
        label,
        values: seriesCols.map(column => parseNumeric(row[column.index] || '')!.value),
        displays: seriesCols.map(column => (row[column.index] || '').trim())
      }
    })
    .filter(item => item.label.length > 0)

  if (items.length < 2) return null
  const series = seriesCols.map(column => column.name)
  return {
    title: table.caption || series.filter(name => name.length > 0).join('、'),
    unit,
    series,
    items
  }
}
