<template>
  <div class="risk-badge">
    <span class="risk-chip">{{ displayLabel }}</span>
    <span class="risk-bar" role="img" :aria-label="`${displayLabel}，${info.level} 段，共 ${segmentCount} 段`">
      <i
        v-for="segment in segmentCount"
        :key="segment"
        class="risk-seg"
        :class="{ 'is-on': segment <= info.level }"
        :style="segment <= info.level ? { background: info.color } : undefined"
      />
    </span>
    <span v-if="hint" class="risk-hint">{{ hint }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RISK_SEGMENT_COUNT, riskDisplayLabel, riskHint, riskLevelInfo } from './chartData'

const props = defineProps<{ risk: unknown }>()

const info = computed(() => riskLevelInfo(props.risk))
const displayLabel = computed(() => riskDisplayLabel(info.value))
const hint = computed(() => riskHint(info.value.tone))
const segmentCount = RISK_SEGMENT_COUNT
</script>

<style lang="scss" scoped>
.risk-badge {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  width: 100%;
  min-width: 0;
  height: 100%;
}

.risk-chip {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  background: #eef5ff;
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
}

.risk-bar {
  display: flex;
  width: 100%;
  gap: 6px;
}

.risk-seg {
  flex: 1 1 0;
  height: 10px;
  min-width: 0;
  border-radius: 999px;
  background: #d9dce3;
}

.risk-hint {
  align-self: flex-end;
  font-size: 12px;
  line-height: 1.4;
  color: #8a9099;
  text-align: right;
}
</style>
