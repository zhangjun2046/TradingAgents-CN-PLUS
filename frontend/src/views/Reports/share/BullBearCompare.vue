<template>
  <div class="bull-bear">
    <h2 class="section-head">多空对比</h2>
    <div class="compare-grid">
      <button
        v-if="bull"
        type="button"
        class="side-card is-bullish"
        @click="emit('navigate', bull.tab, bull.role)"
      >
        <header class="side-head">
          <span class="side-name">{{ bull.name }}</span>
          <span class="side-stance">{{ STANCE_LABEL[bull.stance] }}</span>
        </header>
        <p v-if="bull.sentence" class="side-sentence">{{ bull.sentence }}</p>
        <p v-else class="side-sentence side-sentence--muted">暂无明确结论</p>
      </button>

      <button
        v-if="bear"
        type="button"
        class="side-card is-bearish"
        @click="emit('navigate', bear.tab, bear.role)"
      >
        <header class="side-head">
          <span class="side-name">{{ bear.name }}</span>
          <span class="side-stance">{{ STANCE_LABEL[bear.stance] }}</span>
        </header>
        <p v-if="bear.sentence" class="side-sentence">{{ bear.sentence }}</p>
        <p v-else class="side-sentence side-sentence--muted">暂无明确结论</p>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { STANCE_LABEL } from '@/utils/reportConclusion'
import { buildBullBear } from './chartData'
import type { VisibleDept } from './shareConfig'

const props = defineProps<{ departments: VisibleDept[] }>()

const emit = defineEmits<{
  (e: 'navigate', tab: string, role: string): void
}>()

const comparison = computed(() => buildBullBear(props.departments))
const bull = computed(() => comparison.value.bull)
const bear = computed(() => comparison.value.bear)
</script>

<style lang="scss" scoped>
.bull-bear {
  padding: 16px;
}

.section-head {
  margin: 0 0 12px;
  color: #909399;
  font-size: 13px;
  font-weight: 400;
}

.compare-grid {
  display: flex;
  gap: 10px;
}

.side-card {
  flex: 1;
  min-width: 0;
  padding: 12px;
  border: 0;
  border-radius: 12px;
  cursor: pointer;
  text-align: left;
  font-family: inherit;

  &.is-bullish {
    background: linear-gradient(180deg, #ecfdf5, #fff);
    border-top: 3px solid #10b981;
  }

  &.is-bearish {
    background: linear-gradient(180deg, #fef2f2, #fff);
    border-top: 3px solid #f56c6c;
  }
}

.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.side-name {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.side-stance {
  font-size: 12px;
  font-weight: 700;

  .is-bullish & {
    color: #059669;
  }

  .is-bearish & {
    color: #e04b4b;
  }
}

.side-sentence {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: #606266;

  &--muted {
    color: #c0c4cc;
  }
}
</style>