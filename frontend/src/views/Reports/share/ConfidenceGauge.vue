<template>
  <div class="confidence-wrap">
    <div ref="gaugeRef" class="confidence-gauge" role="img" :aria-label="`模型置信度 ${value} 分，${label}`" />
    <div class="confidence-readout" aria-hidden="true">
      <p class="confidence-score">
        <span class="num">{{ value }}</span><span class="unit">分</span>
      </p>
      <p class="confidence-label" :style="{ color: labelColor }">{{ label }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { GaugeChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { confidenceColor, confidenceLabel, confidenceLabelColor } from './chartData'

echarts.use([GaugeChart, CanvasRenderer])

const props = defineProps<{ value: number }>()

const gaugeRef = ref<HTMLElement | null>(null)
const label = computed(() => confidenceLabel(props.value))
const labelColor = computed(() => confidenceLabelColor(props.value))
let chart: echarts.ECharts | null = null
let observer: ResizeObserver | null = null

function render(): void {
  if (!chart || !gaugeRef.value) return
  const width = gaugeRef.value.clientWidth
  if (width < 20) return
  const ring = Math.max(8, Math.round(width * 0.085))
  chart.setOption(
    {
      animationDurationUpdate: 200,
      series: [
        {
          type: 'gauge',
          startAngle: 90,
          endAngle: -270,
          min: 0,
          max: 100,
          radius: '92%',
          center: ['50%', '50%'],
          axisLine: {
            roundCap: true,
            lineStyle: {
              width: ring,
              color: [
                [props.value / 100, confidenceColor(props.value)],
                [1, '#e7ebf2'],
              ],
            },
          },
          pointer: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          title: { show: false },
          detail: { show: false },
          data: [{ value: props.value }],
        },
      ],
    },
    true
  )
}

onMounted(() => {
  if (!gaugeRef.value) return
  chart = echarts.init(gaugeRef.value)
  render()
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => {
      chart?.resize()
      render()
    })
    observer.observe(gaugeRef.value)
  }
})

watch(
  () => props.value,
  () => render()
)

onUnmounted(() => {
  observer?.disconnect()
  observer = null
  chart?.dispose()
  chart = null
})
</script>

<style lang="scss" scoped>
.confidence-wrap {
  position: relative;
  width: min(100%, 196px);
  aspect-ratio: 1;
  margin: 0 auto;
  container-type: inline-size;
}

.confidence-gauge {
  width: 100%;
  height: 100%;
}

.confidence-readout {
  position: absolute;
  inset: 18%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.confidence-score {
  margin: 0;
  line-height: 1;
  color: #1a1a1a;
}

.num {
  font-size: 28px;
  font-size: 28cqi;
  font-weight: 700;
}

.unit {
  margin-left: 1px;
  font-size: 15px;
  font-size: 15cqi;
  font-weight: 700;
}

.confidence-label {
  margin: 6px 0 0;
  font-size: 13px;
  font-size: 13cqi;
  font-weight: 600;
  line-height: 1.3;
}
</style>
