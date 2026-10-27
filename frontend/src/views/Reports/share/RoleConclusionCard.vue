<template>
  <section class="conclusion-card">
    <header class="card-head">
      <span class="avatar" aria-hidden="true">{{ initial }}</span>
      <h2 class="role-name">{{ roleName }}</h2>
      <span v-if="showStance" class="stance" :class="`is-${conclusion.stance}`">{{ stanceText }}</span>
    </header>

    <div v-if="conclusion.sentence" class="sentence">
      <span class="sentence-label">一句话结论</span>
      <p>{{ conclusion.sentence }}</p>
    </div>

    <div v-if="table" class="table-block">
      <h3 v-if="table.caption" class="block-title">{{ table.caption }}</h3>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th v-for="(header, index) in table.headers" :key="`h-${index}`">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in table.rows" :key="`r-${rowIndex}`">
              <td v-for="(cell, cellIndex) in row" :key="`c-${rowIndex}-${cellIndex}`">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="chart" class="chart-block">
      <h3 v-if="showChartTitle" class="block-title">{{ chart.title }}</h3>
      <div v-for="(item, itemIndex) in chart.items" :key="`i-${itemIndex}`" class="chart-group">
        <div class="chart-label">{{ item.label }}</div>
        <div v-for="(seriesName, seriesIndex) in chart.series" :key="`s-${itemIndex}-${seriesIndex}`" class="chart-row">
          <span v-if="seriesName" class="series-name">{{ seriesName }}</span>
          <div class="track">
            <div
              class="bar"
              :class="seriesIndex === 0 ? 'is-primary' : 'is-secondary'"
              :style="{ width: barWidth(item.values[seriesIndex]) }"
            />
          </div>
          <span class="chart-value">{{ item.displays[seriesIndex] }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { STANCE_LABEL, type Conclusion, type ExtractedChart, type ExtractedTable } from '@/utils/reportConclusion'
import { barWidthFor, maxAbsValue, roleInitial, shouldShowChartTitle } from './conclusionCard'

const props = defineProps<{
  roleName: string
  conclusion: Conclusion
  table: ExtractedTable | null
  chart: ExtractedChart | null
  /** 辩论席与交易员不显示观点徽章 */
  showStance: boolean
}>()

const initial = computed(() => roleInitial(props.roleName))
const stanceText = computed(() => STANCE_LABEL[props.conclusion.stance])
const showChartTitle = computed(() => shouldShowChartTitle(props.chart?.title || '', props.table?.caption))
const maxValue = computed(() => maxAbsValue(props.chart?.items))

function barWidth(value: number): string {
  return barWidthFor(value, maxValue.value)
}
</script>

<style lang="scss" scoped>
.conclusion-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.card-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex: none;
  border-radius: 50%;
  background: linear-gradient(90deg, #4f7cf2, #7b57c9);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
}

.role-name {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 16px;
  line-height: 1.4;
  color: #303133;
}

.stance {
  flex: none;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
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

.sentence {
  margin-top: 12px;
  padding: 12px;
  border-left: 3px solid #3b82f6;
  border-radius: 8px;
  background: #eff6ff;

  p {
    margin: 0;
    color: #303133;
    font-size: 14px;
    line-height: 1.7;
    word-break: break-word;
  }
}

.sentence-label {
  display: block;
  margin-bottom: 4px;
  color: #3b82f6;
  font-size: 12px;
  font-weight: 600;
}

.block-title {
  margin: 0 0 8px;
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}

.table-block,
.chart-block {
  margin-top: 14px;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  border: 1px solid #e5e7eb;
  padding: 8px 10px;
  text-align: left;
  white-space: nowrap;
}

th {
  background: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

td {
  color: #303133;
}

.chart-group + .chart-group {
  margin-top: 10px;
}

.chart-label {
  color: #303133;
  font-size: 13px;
  font-weight: 600;
}

.chart-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.series-name {
  width: 72px;
  flex: none;
  overflow: hidden;
  color: #909399;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track {
  flex: 1;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #f5f7fa;
}

.bar {
  height: 100%;
  border-radius: 999px;

  &.is-primary {
    background: linear-gradient(90deg, #3b82f6, #1d4ed8);
  }

  &.is-secondary {
    background: linear-gradient(90deg, #9b7ad6, #7b57c9);
  }
}

.chart-value {
  flex: none;
  min-width: 52px;
  color: #303133;
  font-size: 12px;
  text-align: right;
}
</style>
