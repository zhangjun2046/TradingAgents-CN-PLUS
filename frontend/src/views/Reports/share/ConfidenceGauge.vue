<template>
  <div ref="gaugeRef" class="confidence-gauge" role="img" :aria-label="`模型置信度 ${value} 分`" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { GaugeChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([GaugeChart, CanvasRenderer])

const props = defineProps<{ value: number }>()

const gaugeRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

function render(): void {
  if (!chart) return
  chart.setOption(
    {
      series: [
        {
          type: 'gauge',
          startAngle: 210,
          endAngle: -30,
          min: 0,
          max: 100,
          radius: '95%',
          center: ['50%', '58%'],
          axisLine: {
            lineStyle: {
              width: 14,
              color: [
                [0.5, '#f56c6c'],
                [0.8, '#e6a23c'],
                [1, '#10b981'],
              ],
            },
          },
          pointer: { width: 5, itemStyle: { color: '#303133' } },
          axisTick: { show: false },
          splitLine: { length: 10, lineStyle: { color: '#fff', width: 2 } },
          axisLabel: { distance: 22, color: '#909399', fontSize: 11 },
          title: { show: false },
          detail: {
            valueAnimation: true,
            formatter: '{value}分',
            offsetCenter: [0, '74%'],
            color: '#303133',
            fontSize: 22,
            fontWeight: 700,
          },
          data: [{ value: props.value }],
        },
      ],
    },
    false
  )
}

onMounted(() => {
  if (!gaugeRef.value) return
  chart = echarts.init(gaugeRef.value)
  render()
})

watch(
  () => props.value,
  () => render()
)

onUnmounted(() => {
  chart?.dispose()
  chart = null
})
</script>

<style lang="scss" scoped>
.confidence-gauge {
  width: 160px;
  height: 120px;
}
</style>