<template>
  <div class="risk-badge" :class="`is-${tone}`">
    <span class="risk-label">{{ label }}</span>
    <span class="risk-bar" aria-hidden="true">
      <i v-for="segment in 3" :key="segment" class="risk-seg" :class="{ 'is-on': segment <= litCount }" />
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { riskLevelInfo, type RiskTone } from './chartData'

const props = defineProps<{ risk: unknown }>()

const info = computed(() => riskLevelInfo(props.risk))
const label = computed(() => info.value.label)
const tone = computed<RiskTone>(() => info.value.tone)

/** 点亮的段数：低 1 段、中等 2 段、高 3 段；未知 2 段但灰显 */
const litCount = computed(() => {
  if (tone.value === 'low') return 1
  if (tone.value === 'high') return 3
  return 2
})
</script>

<style lang="scss" scoped>
.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  background: #f5f7fa;

  &.is-low {
    .risk-label {
      color: #67c23a;
    }

    .risk-seg.is-on {
      background: #67c23a;
    }
  }

  &.is-medium {
    .risk-label {
      color: #e6a23c;
    }

    .risk-seg.is-on {
      background: #e6a23c;
    }
  }

  &.is-high {
    .risk-label {
      color: #f56c6c;
    }

    .risk-seg.is-on {
      background: #f56c6c;
    }
  }

  &.is-unknown {
    .risk-label {
      color: #909399;
    }

    .risk-seg.is-on {
      background: #c0c4cc;
    }
  }
}

.risk-label {
  font-size: 14px;
  font-weight: 700;
}

.risk-bar {
  display: inline-flex;
  gap: 3px;
}

.risk-seg {
  width: 14px;
  height: 6px;
  border-radius: 999px;
  background: #e5e7eb;
}
</style>