<template>
  <div class="decision-chain">
    <h2 class="section-head">决策链</h2>
    <div v-if="nodes.length" class="chain-row">
      <template v-for="(node, index) in nodes" :key="node.key">
        <button type="button" class="chain-node" :class="`is-${node.stance}`" @click="emit('navigate', node.tab, node.role)">
          <span class="node-name">{{ node.name }}</span>
          <span class="node-stance">{{ STANCE_LABEL[node.stance] }}</span>
        </button>
        <span v-if="index < nodes.length - 1" class="chain-arrow" aria-hidden="true">›</span>
      </template>
    </div>
    <p v-else class="chain-empty">各岗位暂未形成明确观点</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { STANCE_LABEL } from '@/utils/reportConclusion'
import { buildDecisionChain } from './chartData'
import type { VisibleDept } from './shareConfig'

const props = defineProps<{ departments: VisibleDept[] }>()

const emit = defineEmits<{
  (e: 'navigate', tab: string, role: string): void
}>()

const nodes = computed(() => buildDecisionChain(props.departments))
</script>

<style lang="scss" scoped>
.decision-chain {
  padding: 16px;
}

.section-head {
  margin: 0 0 12px;
  color: #909399;
  font-size: 13px;
  font-weight: 400;
}

.chain-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.chain-node {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 0;
  border-radius: 999px;
  cursor: pointer;
  font-family: inherit;
  background: #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);

  .node-name {
    font-size: 13px;
    color: #303133;
    font-weight: 600;
  }

  .node-stance {
    font-size: 12px;
    font-weight: 600;
  }

  &.is-bullish .node-stance {
    color: #059669;
  }

  &.is-bearish .node-stance {
    color: #e04b4b;
  }

  &.is-neutral .node-stance {
    color: #3b82f6;
  }
}

.chain-arrow {
  color: #c0c4cc;
  font-size: 16px;
}

.chain-empty {
  margin: 0;
  color: #909399;
  font-size: 14px;
}
</style>