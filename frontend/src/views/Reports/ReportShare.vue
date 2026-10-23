<template>
  <div class="report-share">
    <div v-if="loading" class="share-status">
      <div class="spinner" />
      <p>正在加载报告…</p>
    </div>

    <div v-else-if="error" class="share-status share-status--error">
      <h1>链接已失效</h1>
      <p>{{ error }}</p>
      <p class="hint">请向分享者重新索取链接。</p>
    </div>

    <article v-else-if="report" class="share-article">
      <header class="share-header">
        <p class="eyebrow">TradingAgents-CN 分析报告</p>
        <h1>{{ report.stock_name || report.stock_symbol }} 分析报告</h1>
        <div class="meta">
          <span v-if="report.stock_symbol">{{ report.stock_symbol }}</span>
          <span v-if="report.analysis_date">{{ report.analysis_date }}</span>
        </div>
      </header>

      <section class="decision-bar">
        <div class="decision-item">
          <span class="label">分析参考</span>
          <div class="value markdown-body" v-html="renderMarkdown(report.recommendation || '暂无')"></div>
        </div>
        <div class="decision-item">
          <span class="label">风险评估</span>
          <div class="value">{{ report.risk_level || '中等' }}</div>
        </div>
        <div class="decision-item">
          <span class="label">模型置信度</span>
          <div class="value">{{ confidenceText }}</div>
        </div>
      </section>

      <section v-if="report.key_points && report.key_points.length" class="block">
        <h2>关键要点</h2>
        <ul class="key-points">
          <li v-for="(point, index) in report.key_points" :key="index">{{ point }}</li>
        </ul>
      </section>

      <section v-if="report.summary" class="block">
        <h2>执行摘要</h2>
        <div class="markdown-body" v-html="renderMarkdown(report.summary)"></div>
      </section>

      <section
        v-for="module in modules"
        :key="module.key"
        class="block module-block"
      >
        <h2>{{ module.title }}</h2>
        <div
          v-if="typeof module.content === 'string'"
          class="markdown-body"
          v-html="renderMarkdown(module.content)"
        ></div>
        <pre v-else class="json-block">{{ JSON.stringify(module.content, null, 2) }}</pre>
      </section>

      <footer class="disclaimer">
        <h2>风险提示与免责声明</h2>
        <ul>
          <li>本系统为股票分析辅助工具，不具备证券投资咨询资质。</li>
          <li>所有分析结果仅为技术分析参考，不构成买卖建议。</li>
          <li>分析基于历史与公开信息，无法预测未来走势，投资有风险。</li>
          <li>投资决策及其后果由投资者自行承担。</li>
        </ul>
      </footer>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

type SharedReport = {
  stock_symbol?: string
  stock_name?: string
  analysis_date?: string
  recommendation?: string
  risk_level?: string
  confidence_score?: number
  summary?: string
  key_points?: string[]
  reports?: Record<string, unknown>
}

const MODULE_TITLES: Record<string, string> = {
  market_report: '市场技术分析',
  sentiment_report: '市场情绪分析',
  news_report: '新闻事件分析',
  fundamentals_report: '基本面分析',
  bull_researcher: '多头研究员观点',
  bear_researcher: '空头研究员观点',
  research_team_decision: '研究经理决策',
  trader_investment_plan: '交易员计划',
  risky_analyst: '激进分析师观点',
  safe_analyst: '保守分析师观点',
  neutral_analyst: '中性分析师观点',
  risk_management_decision: '投资组合经理决策',
  final_trade_decision: '最终交易决策',
  investment_plan: '投资建议'
}

marked.setOptions({ breaks: true, gfm: true })

const route = useRoute()
const loading = ref(true)
const error = ref('')
const report = ref<SharedReport | null>(null)

const modules = computed(() => {
  const reports = report.value?.reports || {}
  return Object.entries(reports).map(([key, content]) => ({
    key,
    content,
    title: MODULE_TITLES[key] || key.replace(/_/g, ' ')
  }))
})

const confidenceText = computed(() => {
  const score = Number(report.value?.confidence_score || 0)
  const percent = score > 1 ? Math.round(score) : Math.round(score * 100)
  return `${percent} 分`
})

const renderMarkdown = (content: string) => {
  if (!content) return ''
  try {
    const html = marked.parse(content) as string
    return DOMPurify.sanitize(html)
  } catch {
    return `<pre>${DOMPurify.sanitize(content)}</pre>`
  }
}

const fetchSharedReport = async () => {
  loading.value = true
  error.value = ''
  try {
    const token = String(route.params.token || '')
    const response = await fetch(`/api/reports/share/${encodeURIComponent(token)}`)
    if (response.status === 404) {
      error.value = '该分享链接不存在、已过期或已被撤销。'
      report.value = null
      return
    }
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const result = await response.json()
    if (!result?.success || !result.data) {
      error.value = '该分享链接不存在、已过期或已被撤销。'
      report.value = null
      return
    }
    report.value = result.data
    const titleName = result.data.stock_name || result.data.stock_symbol || '分析报告'
    document.title = `${titleName} - TradingAgents-CN`
  } catch (err) {
    console.info('Failed to load shared report', err)
    error.value = '报告加载失败，请稍后重试。'
    report.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSharedReport()
})
</script>

<style lang="scss" scoped>
.report-share {
  min-height: 100vh;
  background: #f6f7fb;
  color: #1f2329;
}

.share-status {
  max-width: 720px;
  margin: 0 auto;
  padding: 80px 20px;
  text-align: center;

  h1 {
    font-size: 22px;
    margin: 0 0 12px;
  }

  p {
    font-size: 16px;
    line-height: 1.7;
    color: #5c6370;
    margin: 0;
  }

  .hint {
    margin-top: 8px;
    font-size: 14px;
  }
}

.spinner {
  width: 32px;
  height: 32px;
  margin: 0 auto 16px;
  border: 3px solid #d9dce3;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.share-article {
  max-width: 720px;
  margin: 0 auto;
  padding: 20px 16px 48px;
}

.share-header {
  padding: 8px 0 20px;

  .eyebrow {
    margin: 0 0 8px;
    font-size: 13px;
    letter-spacing: 0.04em;
    color: #6b7280;
  }

  h1 {
    margin: 0 0 12px;
    font-size: 24px;
    line-height: 1.35;
    font-weight: 700;
  }

  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    span {
      font-size: 13px;
      color: #3b82f6;
      background: #e8f1ff;
      border-radius: 999px;
      padding: 4px 10px;
    }
  }
}

.decision-bar,
.block,
.disclaimer {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 14px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}

.decision-item {
  padding: 12px 0;
  border-bottom: 1px solid #eef0f4;

  &:last-child {
    border-bottom: 0;
    padding-bottom: 0;
  }

  &:first-child {
    padding-top: 0;
  }

  .label {
    display: block;
    font-size: 13px;
    color: #6b7280;
    margin-bottom: 6px;
  }

  .value {
    font-size: 17px;
    font-weight: 600;
    line-height: 1.6;
  }
}

.block h2,
.disclaimer h2 {
  margin: 0 0 12px;
  font-size: 18px;
  line-height: 1.4;
}

.key-points {
  margin: 0;
  padding-left: 18px;

  li {
    font-size: 16px;
    line-height: 1.7;
    margin-bottom: 8px;
  }
}

.markdown-body {
  font-size: 16px;
  line-height: 1.7;
  word-break: break-word;

  :deep(h1),
  :deep(h2),
  :deep(h3),
  :deep(h4) {
    line-height: 1.4;
    margin: 1.2em 0 0.6em;
  }

  :deep(h1) { font-size: 22px; }
  :deep(h2) { font-size: 19px; }
  :deep(h3) { font-size: 17px; }

  :deep(p),
  :deep(li) {
    font-size: 16px;
    line-height: 1.7;
  }

  :deep(img) {
    max-width: 100%;
    height: auto;
  }

  :deep(table) {
    display: block;
    width: 100%;
    overflow-x: auto;
    border-collapse: collapse;
    font-size: 14px;
  }

  :deep(th),
  :deep(td) {
    border: 1px solid #e5e7eb;
    padding: 8px 10px;
    white-space: nowrap;
  }

  :deep(pre),
  :deep(code) {
    white-space: pre-wrap;
    word-break: break-word;
  }
}

.json-block {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.disclaimer {
  background: #fff8e8;

  ul {
    margin: 0;
    padding-left: 18px;
  }

  li {
    font-size: 14px;
    line-height: 1.7;
    color: #6b4f12;
    margin-bottom: 6px;
  }
}

@media (max-width: 480px) {
  .share-article {
    padding: 16px 12px 40px;
  }

  .share-header h1 {
    font-size: 22px;
  }
}
</style>
