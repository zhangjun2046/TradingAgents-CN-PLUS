<template>
  <header class="share-header">
    <div class="top-row">
      <a class="back-list" :href="reportListUrl" @click="onBackToList">返回报告列表</a>
      <slot name="actions" />
    </div>
    <p class="eyebrow">HunterAgent 分析报告</p>
    <h1>{{ title }}</h1>
    <div class="meta">
      <span v-if="report.stock_symbol" class="chip-code">{{ report.stock_symbol }}</span>
      <span v-if="report.analysis_date">{{ report.analysis_date }}</span>
      <span v-if="expiresText" class="chip-muted">{{ expiresText }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { resolveReportListUrl, logBackToList } from './shareConfig'
import type { SharedReport } from './types'

const props = defineProps<{ report: SharedReport }>()

const title = computed(
  () => `${props.report.stock_name || props.report.stock_symbol || ''} 分析报告`
)

const reportListUrl = resolveReportListUrl()

/** 分享有效期仅展示，不改后端行为 */
const expiresText = computed(() => {
  const raw = props.report.expires_at
  if (!raw) return ''
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (value: number) => String(value).padStart(2, '0')
  return `有效期至 ${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
})

function onBackToList(): void {
  logBackToList()
}
</script>

<style lang="scss" scoped>
.share-header {
  margin-bottom: 14px;
  padding: 16px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);

  .eyebrow {
    margin: 0 0 8px;
    font-size: 13px;
    letter-spacing: 0.04em;
    color: #909399;
  }

  h1 {
    margin: 0 0 12px;
    font-size: 24px;
    line-height: 1.35;
    font-weight: 700;
    color: #303133;
  }

  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    span {
      font-size: 13px;
      color: #909399;
      background: #f5f7fa;
      border-radius: 999px;
      padding: 4px 10px;
    }

    .chip-code {
      color: #fff;
      background: linear-gradient(90deg, #3b82f6, #1d4ed8);
    }

    .chip-muted {
      color: #909399;
      background: #f5f7fa;
    }
  }
}

.top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.back-list {
  display: inline-flex;
  color: #3b82f6;
  font-size: 14px;
  line-height: 1.4;
  text-decoration: none;
}

@media (max-width: 480px) {
  .share-header h1 {
    font-size: 22px;
  }
}
</style>