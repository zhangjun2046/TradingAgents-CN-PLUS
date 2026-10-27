<template>
  <div class="overview-panel">
    <!-- 投资建议 + 置信度 + 风险（P4.3） -->
    <section class="card">
      <div class="card-body">
        <div class="decision-item">
          <span class="label">投资建议</span>
          <div class="value">
            <span class="action-tag" :class="`is-${suggest.tone}`">{{ stanceLabel }}</span>
            <span class="action-text">{{ suggest.text }}</span>
          </div>
        </div>
        <div class="metric-row">
          <div class="metric-cell">
            <span class="label">模型置信度</span>
            <ConfidenceGauge :value="confidenceValue" />
          </div>
          <div class="metric-cell metric-cell--risk">
            <span class="label">风险评估</span>
            <RiskBadge :risk="report.risk_level" />
          </div>
        </div>
      </div>
    </section>

    <!-- 决策链（P4.3） -->
    <section class="card">
      <DecisionChain :departments="departments" @navigate="onNavigate" />
    </section>

    <!-- 多空对比（P4.3，仅研究部有多空研究员时显示） -->
    <section v-if="hasBullBear" class="card">
      <BullBearCompare :departments="departments" @navigate="onNavigate" />
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
import { computed, defineAsyncComponent } from 'vue'
import { STANCE_LABEL } from '@/utils/reportConclusion'
import BullBearCompare from './BullBearCompare.vue'
import DecisionChain from './DecisionChain.vue'
import RiskBadge from './RiskBadge.vue'
import { buildBullBear, normalizeConfidence, suggestAction } from './chartData'
import { formatOverviewSummary } from './overviewSummary'
import type { VisibleDept } from './shareConfig'
import type { SharedReport } from './types'

/** ECharts 仪表盘按需异步加载，避免拖慢首屏 */
const ConfidenceGauge = defineAsyncComponent(() => import('./ConfidenceGauge.vue'))

const props = defineProps<{ report: SharedReport; departments: VisibleDept[] }>()

const emit = defineEmits<{
  (e: 'navigate', tab: string, role: string): void
}>()

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

const confidenceValue = computed(() => normalizeConfidence(props.report.confidence_score))

const suggest = computed(() => suggestAction(props.report))
const stanceLabel = computed(() => STANCE_LABEL[suggest.value.tone])

const hasBullBear = computed(() => {
  const { bull, bear } = buildBullBear(props.departments)
  return Boolean(bull || bear)
})

function onNavigate(tab: string, role: string): void {
  emit('navigate', tab, role)
}
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
  padding-bottom: 14px;
  border-bottom: 1px solid #eef0f4;

  .label {
    display: block;
    font-size: 13px;
    color: #909399;
    margin-bottom: 6px;
  }

  .value {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .action-text {
    font-size: 16px;
    font-weight: 600;
    line-height: 1.5;
    color: #303133;
    word-break: break-word;
  }
}

.action-tag {
  flex: none;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.4;

  &.is-bullish {
    color: #fff;
    background: linear-gradient(90deg, #10b981, #059669);
  }

  &.is-bearish {
    color: #fff;
    background: linear-gradient(90deg, #f56c6c, #e04b4b);
  }

  &.is-neutral {
    color: #3b82f6;
    background: #eff6ff;
  }

  &.is-unknown {
    color: #909399;
    background: #f5f7fa;
  }
}

.metric-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 14px;
}

.metric-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;

  .label {
    font-size: 13px;
    color: #909399;
  }

  &--risk {
    justify-content: center;
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