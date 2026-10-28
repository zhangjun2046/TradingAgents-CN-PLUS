<template>
  <div class="decision-chain">
    <div class="section-head-row">
      <h2 class="section-head">决策链 · 部门岗位观点串联</h2>
      <p v-if="hasClickable" class="section-hint">点击节点跳转对应岗位详情 ›</p>
    </div>
    <ol v-if="nodes.length" class="chain-timeline">
      <li
        v-for="(node, index) in nodes"
        :key="node.key"
        class="chain-item"
        :class="[`is-${node.stance}`, { 'is-final': !node.clickable, 'is-last': index === nodes.length - 1 }]"
      >
        <div class="rail" aria-hidden="true">
          <span class="node-icon">{{ nodeIcon(node) }}</span>
          <span v-if="index < nodes.length - 1" class="rail-connector">
            <span class="rail-line" />
            <span class="rail-arrow">↓</span>
          </span>
        </div>
        <button
          type="button"
          class="chain-node"
          :disabled="!node.clickable"
          @click="onClick(node)"
        >
          <span class="node-name">{{ node.name }}</span>
          <span class="node-stance">{{ STANCE_LABEL[node.stance] }}</span>
        </button>
      </li>
    </ol>
    <p v-else class="chain-empty">各岗位暂未形成明确观点</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { STANCE_LABEL } from '@/utils/reportConclusion'
import { buildDecisionChain, type ChainNode, type SuggestResult } from './chartData'
import type { VisibleDept } from './shareConfig'

const props = defineProps<{
  departments: VisibleDept[]
  suggest: SuggestResult
}>()

const emit = defineEmits<{
  (e: 'navigate', tab: string, role: string): void
}>()

const nodes = computed(() => buildDecisionChain(props.departments, props.suggest))
const hasClickable = computed(() => nodes.value.some((node) => node.clickable))

function nodeIcon(node: ChainNode): string {
  if (!node.clickable) return '决'
  const name = node.name.trim()
  return name ? name.charAt(0) : '岗'
}

function onClick(node: ChainNode): void {
  if (!node.clickable) return
  emit('navigate', node.tab, node.role)
}
</script>

<style lang="scss" scoped>
.decision-chain {
  padding: 16px;
}

.section-head-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}

.section-head {
  margin: 0;
  color: #909399;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.4;
}

.section-hint {
  flex: none;
  margin: 0;
  max-width: 52%;
  color: #3b82f6;
  font-size: 12px;
  line-height: 1.4;
  text-align: right;
}

.chain-timeline {
  margin: 0;
  padding: 0;
  list-style: none;
}

.chain-item {
  display: flex;
  align-items: stretch;
  gap: 12px;
  min-width: 0;

  .rail {
    display: flex;
    flex: none;
    flex-direction: column;
    align-items: center;
    width: 32px;
  }

  .node-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 700;
    color: #fff;
    background: #909399;
    z-index: 1;
  }

  .rail-connector {
    display: flex;
    flex: 1;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 20px;
    margin: 2px 0 4px;
    gap: 0;
  }

  .rail-line {
    flex: 1;
    width: 2px;
    min-height: 6px;
    background: #d1d5db;
    border-radius: 999px;
  }

  .rail-arrow {
    flex: none;
    margin-top: -2px;
    color: #9ca3af;
    font-size: 12px;
    font-weight: 700;
    line-height: 1;
  }

  .chain-node {
    display: flex;
    flex: 1;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;
    margin-bottom: 4px;
    padding: 10px 12px;
    border: 1px solid #eef0f4;
    border-radius: 12px;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    background: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

    &:disabled {
      cursor: default;
    }
  }

  &.is-last .chain-node {
    margin-bottom: 0;
  }

  .node-name {
    min-width: 0;
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    line-height: 1.4;
    word-break: break-word;
  }

  .node-stance {
    flex: none;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    line-height: 1.4;
    background: #f5f7fa;
    color: #909399;
  }

  /* A 股：看多红 / 看空绿 / 中性蓝 */
  &.is-bullish {
    .node-icon {
      background: #e15252;
    }

    .node-stance {
      color: #e15252;
      background: #fef2f2;
    }
  }

  &.is-bearish {
    .node-icon {
      background: #10b981;
    }

    .node-stance {
      color: #059669;
      background: #ecfdf5;
    }
  }

  &.is-neutral {
    .node-icon {
      background: #3b82f6;
    }

    .node-stance {
      color: #3b82f6;
      background: #eff6ff;
    }
  }

  &.is-final {
    .chain-node {
      border-color: #bfdbfe;
      background: #eff6ff;
    }

    .node-name {
      font-weight: 700;
      color: #1d4ed8;
    }
  }
}

.chain-empty {
  margin: 0;
  color: #909399;
  font-size: 14px;
}
</style>
