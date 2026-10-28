<template>
  <div class="overview-panel">
    <!-- 投资建议横幅（A 股：看多红 / 看空绿） -->
    <section class="suggest-banner" :class="`is-${suggest.tone}`">
      <p class="suggest-title">{{ banner.title }}</p>
    </section>

    <!-- 置信度 + 风险：左右两栏，中间分隔 -->
    <section class="card">
      <div class="metric-row">
        <div class="metric-cell">
          <span class="label">模型置信度</span>
          <ConfidenceGauge :value="confidenceValue" />
        </div>
        <div class="metric-split" aria-hidden="true" />
        <div class="metric-cell metric-cell--risk">
          <span class="label">风险评估</span>
          <RiskBadge :risk="report.risk_level" />
        </div>
      </div>
    </section>

    <!-- 决策链 -->
    <section class="card">
      <DecisionChain :departments="departments" :suggest="suggest" @navigate="onNavigate" />
    </section>

    <section v-if="keyPoints.length" class="card">
      <h2 class="section-head">关键要点</h2>
      <ol class="key-points">
        <li v-for="(point, index) in keyPoints" :key="index">{{ point }}</li>
      </ol>
    </section>

    <section class="card">
      <h2 class="section-head">分析参考</h2>
      <div class="card-body reference-markdown">
        <MarkdownBody :content="referenceText" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import DecisionChain from './DecisionChain.vue'
import MarkdownBody from './MarkdownBody.vue'
import RiskBadge from './RiskBadge.vue'
import { formatSuggestBanner, normalizeConfidence, suggestAction } from './chartData'
import type { VisibleDept } from './shareConfig'
import type { SharedReport } from './types'

/** ECharts 仪表盘按需异步加载，避免拖慢首屏 */
const ConfidenceGauge = defineAsyncComponent(() => import('./ConfidenceGauge.vue'))

const props = defineProps<{ report: SharedReport; departments: VisibleDept[] }>()

const emit = defineEmits<{
  (e: 'navigate', tab: string, role: string): void
}>()

const keyPoints = computed(() => props.report.key_points || [])

/** 与 PC 报告详情「分析参考」同一字段 `recommendation`。 */
const referenceText = computed(() => {
  const recommendation = props.report.recommendation
  const text = typeof recommendation === 'string' ? recommendation.trim() : ''
  return text || '暂无'
})

const confidenceValue = computed(() => normalizeConfidence(props.report.confidence_score))

const suggest = computed(() => suggestAction(props.report))
const banner = computed(() => formatSuggestBanner(suggest.value))

function onNavigate(tab: string, role: string): void {
  emit('navigate', tab, role)
}
</script>

<style lang="scss" scoped>
.suggest-banner {
  margin-bottom: 14px;
  padding: 14px 16px;
  border-radius: 12px;
  color: #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);

  /* A 股：看多红 / 看空绿 / 中性蓝 / 未知灰 */
  &.is-bullish {
    background: linear-gradient(90deg, #e15252, #c93c3c);
  }

  &.is-bearish {
    background: linear-gradient(90deg, #10b981, #059669);
  }

  &.is-neutral {
    background: linear-gradient(90deg, #3b82f6, #1d4ed8);
  }

  &.is-unknown {
    background: linear-gradient(90deg, #909399, #606266);
  }
}

.suggest-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.45;
}

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

.reference-markdown {
  padding-top: 6px;

  :deep(.markdown-body) {
    font-size: 15px;
  }

  :deep(p) {
    margin: 0 0 10px;
  }

  :deep(p:last-child) {
    margin-bottom: 0;
  }
}

.metric-row {
  display: flex;
  align-items: stretch;
  gap: 0;
  padding: 16px 8px 18px;
}

.metric-split {
  flex: 0 0 1px;
  width: 1px;
  margin: 4px 2px;
  background: #e4e7ed;
}

.metric-cell {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  min-width: 0;
  padding: 2px 12px;

  .label {
    font-size: 14px;
    font-weight: 600;
    line-height: 1.4;
    color: #303133;
  }
}

.metric-cell--risk {
  min-height: 0;

  :deep(.risk-badge) {
    flex: 1;
  }
}

.key-points {
  margin: 0;
  padding: 10px 16px 16px;
  list-style: none;
  counter-reset: key-point;

  li {
    position: relative;
    padding-left: 32px;
    margin-bottom: 10px;
    font-size: 15px;
    line-height: 1.7;
    color: #303133;
    counter-increment: key-point;

    &::before {
      content: counter(key-point);
      position: absolute;
      left: 0;
      top: 2px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: #eef0f4;
      color: #606266;
      font-size: 12px;
      font-weight: 700;
      line-height: 1;
    }

    &:last-child {
      margin-bottom: 0;
    }
  }
}
</style>
