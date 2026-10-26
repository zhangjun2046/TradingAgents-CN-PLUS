<template>
  <section class="role-panel">
    <div class="role-body">
      <MarkdownBody v-if="isText" :content="textContent" />
      <pre v-else class="json-block">{{ jsonContent }}</pre>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownBody from './MarkdownBody.vue'
import { stripTrailingDisclaimer } from './stripDisclaimer'
import type { VisibleRole } from './shareConfig'

const props = defineProps<{ role: VisibleRole }>()

const isText = computed(() => typeof props.role.content === 'string')

const textContent = computed(() =>
  typeof props.role.content === 'string' ? stripTrailingDisclaimer(props.role.content) : ''
)

/** 非文本模块（对象 / 数组）沿用改造前的 JSON 展示 */
const jsonContent = computed(() => JSON.stringify(props.role.content, null, 2))
</script>

<style lang="scss" scoped>
.role-panel {
  background: #fff;
  border-radius: 12px;
  margin-bottom: 14px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.role-body {
  min-width: 0;
  padding: 16px;
  color: #303133;
}

.json-block {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>