<template>
  <section class="role-panel">
    <RoleConclusionCard
      :role-name="role.name"
      :conclusion="view.conclusion"
      :table="view.table"
      :chart="view.chart"
      :show-stance="role.showsStance"
    />

    <div class="body-card">
      <div ref="bodyRef" class="role-body" :class="{ 'is-collapsed': foldable && !expanded }">
        <div ref="contentRef">
          <MarkdownBody v-if="isText" :content="textContent" />
          <pre v-else class="json-block">{{ jsonContent }}</pre>
        </div>
      </div>
      <button v-if="foldable" type="button" class="fold-btn" :aria-expanded="expanded" @click="toggleFold">
        {{ expanded ? '收起' : `展开阅读完整正文（共 ${charCount} 字）` }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import RoleConclusionCard from './RoleConclusionCard.vue'
import MarkdownBody from './MarkdownBody.vue'
import { stripTrailingDisclaimer } from './stripDisclaimer'
import type { VisibleRole } from './shareConfig'
import { isFoldable } from './roleFold'
import { extractRoleView, plainTextLength, type RoleExtract } from '@/utils/reportConclusion'

const props = defineProps<{ role: VisibleRole }>()

const EMPTY_VIEW: RoleExtract = {
  conclusion: { stance: 'unknown', sentence: '' },
  table: null,
  chart: null,
}

const isText = computed(() => typeof props.role.content === 'string')

/** 展开后的正文与 PC 报告详情同一份模块原文，文末免责声明也保留。 */
const textContent = computed(() =>
  typeof props.role.content === 'string' ? props.role.content : ''
)

/** 结论卡不把文末套话当成观点；页底已有单独的免责声明。 */
const analysisText = computed(() =>
  textContent.value ? stripTrailingDisclaimer(textContent.value) : ''
)

/** 非文本模块（对象 / 数组）沿用改造前的 JSON 展示，不猜测观点 */
const jsonContent = computed(() => JSON.stringify(props.role.content, null, 2))

const view = computed(() => (isText.value ? extractRoleView(analysisText.value) : EMPTY_VIEW))

const charCount = computed(() => plainTextLength(textContent.value))

const bodyRef = ref<HTMLElement | null>(null)
const contentRef = ref<HTMLElement | null>(null)
const foldable = ref(false)
const expanded = ref(false)

let observer: ResizeObserver | null = null

function measure(): void {
  if (!isText.value || typeof window === 'undefined') {
    foldable.value = false
    return
  }
  const content = contentRef.value
  if (!content) return
  foldable.value = isFoldable(content.offsetHeight, window.innerHeight)
}

function toggleFold(): void {
  expanded.value = !expanded.value
  console.info('[Share] toggle role body', { role: props.role.key, expanded: expanded.value })
}

function bindObserver(): void {
  observer?.disconnect()
  if (!contentRef.value || typeof ResizeObserver === 'undefined') return
  observer = new ResizeObserver(() => measure())
  observer.observe(contentRef.value)
}

watch(view, (next) => {
  console.info('[Share] role conclusion', {
    role: props.role.key,
    stance: next.conclusion.stance,
    hasSentence: Boolean(next.conclusion.sentence),
    hasTable: Boolean(next.table),
    hasChart: Boolean(next.chart),
  })
}, { immediate: true })

watch(
  () => [props.role.key, textContent.value],
  async () => {
    expanded.value = false
    await nextTick()
    bindObserver()
    measure()
  }
)

onMounted(async () => {
  await nextTick()
  bindObserver()
  measure()
  window.addEventListener('resize', measure)
})

onUnmounted(() => {
  observer?.disconnect()
  window.removeEventListener('resize', measure)
})
</script>

<style lang="scss" scoped>
.role-panel {
  margin-bottom: 14px;
}

.body-card {
  margin-top: 14px;
  overflow: hidden;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.role-body {
  position: relative;
  min-width: 0;
  padding: 16px;
  color: #303133;

  &.is-collapsed {
    max-height: 60vh;
    overflow: hidden;

    &::after {
      content: '';
      position: absolute;
      right: 0;
      bottom: 0;
      left: 0;
      height: 72px;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0), #fff);
      pointer-events: none;
    }
  }
}

.fold-btn {
  display: block;
  width: calc(100% - 32px);
  height: 44px;
  margin: 0 16px 16px;
  border: 0;
  border-radius: 12px;
  background: linear-gradient(90deg, #3b82f6, #1d4ed8);
  color: #fff;
  font-family: inherit;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.35);
}

.json-block {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
