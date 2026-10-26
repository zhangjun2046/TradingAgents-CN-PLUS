<template>
  <div class="overview-panel">
    <!-- 决策链、仪表盘、风险色块由 P4.3 引入 -->
    <section class="card">
      <div class="card-body">
        <div class="decision-item">
          <span class="label">分析参考</span>
          <div class="value">
            <MarkdownBody :content="report.recommendation || '暂无'" />
          </div>
        </div>
        <div class="decision-item">
          <span class="label">风险评估</span>
          <div class="value">{{ report.risk_level || '中等' }}</div>
        </div>
        <div class="decision-item">
          <span class="label">模型置信度</span>
          <div class="value">{{ confidenceText }}</div>
        </div>
      </div>
    </section>

    <section v-if="keyPoints.length" class="card">
      <h2 class="section-head">关键要点</h2>
      <ul class="key-points">
        <li v-for="(point, index) in keyPoints" :key="index">{{ point }}</li>
      </ul>
    </section>

    <section v-if="summaryText" class="card">
      <h2 class="section-head">执行摘要</h2>
      <div class="card-body summary-text">{{ summaryText }}</div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownBody from './MarkdownBody.vue'
import { formatOverviewSummary } from './overviewSummary'
import type { SharedReport } from './types'

const props = defineProps<{ report: SharedReport }>()

const keyPoints = computed(() => props.report.key_points || [])

function moduleText(key: string): string {
  const value = props.report.reports?.[key]
  return typeof value === 'string' ? value : ''
}

/** 优先用完整裁决书抽一句；旧 summary 被表格截断时不会把半张表画出来。 */
const summaryText = computed(() =>
  formatOverviewSummary(
    moduleText('final_trade_decision') ||
      moduleText('risk_management_decision') ||
      props.report.summary ||
      ''
  )
)

const confidenceText = computed(() => {
  const score = Number(props.report.confidence_score || 0)
  const percent = score > 1 ? Math.round(score) : Math.round(score * 100)
  return `${percent} 分`
})
</script>

<style lang="scss" scoped>
.card {
  background: #fff;
  border-radius: 12px;
  margin-bottom: 14px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 16px 16px 0;
  color: #909399;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.4;

  &::before {
    content: '';
    flex: 0 0 3px;
    width: 3px;
    height: 14px;
    border-radius: 2px;
    background: #3b82f6;
  }
}

.card-body {
  min-width: 0;
  padding: 16px;
}

.summary-text {
  padding-top: 6px;
  font-size: 16px;
  line-height: 1.7;
  color: #303133;
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
    color: #909399;
    margin-bottom: 6px;
  }

  .value {
    font-size: 17px;
    font-weight: 600;
    line-height: 1.6;
    color: #303133;
  }
}

.key-points {
  margin: 0;
  padding: 6px 16px 16px 34px;

  li {
    font-size: 16px;
    line-height: 1.7;
    margin-bottom: 8px;
  }
}
</style>