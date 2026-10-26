<template>
  <div class="markdown-body" v-html="html" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked, Renderer } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{
  /** 模块正文；非字符串（对象 / 数组）由调用方决定如何展示 */
  content: string
}>()

marked.setOptions({ breaks: true, gfm: true })

const defaultTable = Renderer.prototype.table

/** 表格包一层可横滑容器，避免移动端撑破布局 */
class TableScrollRenderer extends Renderer {
  table(token: Parameters<Renderer['table']>[0]): string {
    return `<div class="table-scroll">${defaultTable.call(this, token)}</div>`
  }
}

const renderer = new TableScrollRenderer()

function renderMarkdown(content: string): string {
  if (!content) return ''
  try {
    const html = marked.parse(content, { renderer }) as string
    return DOMPurify.sanitize(html)
  } catch (err) {
    console.info('[Share] markdown render failed, fallback to plain text', err)
    return `<pre>${DOMPurify.sanitize(content)}</pre>`
  }
}

const html = computed(() => renderMarkdown(props.content))
</script>

<style lang="scss" scoped>
.markdown-body {
  min-width: 0;
  max-width: 100%;
  font-size: 16px;
  line-height: 1.7;
  color: #303133;
  word-break: break-word;

  :deep(a) {
    color: #3b82f6;
  }

  :deep(h1),
  :deep(h2),
  :deep(h3),
  :deep(h4) {
    line-height: 1.4;
    margin: 1.2em 0 0.6em;
  }

  :deep(h1) {
    font-size: 22px;
  }

  :deep(h2) {
    font-size: 19px;
  }

  :deep(h3) {
    font-size: 17px;
  }

  :deep(p),
  :deep(li) {
    font-size: 16px;
    line-height: 1.7;
  }

  :deep(img) {
    max-width: 100%;
    height: auto;
  }

  /* 表格横滑：外层容器由自定义 renderer 注入 */
  :deep(.table-scroll) {
    width: 100%;
    max-width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin: 12px 0;
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }

  :deep(th),
  :deep(td) {
    border: 1px solid #e5e7eb;
    padding: 8px 10px;
    white-space: normal;
    word-break: break-word;
  }

  :deep(pre),
  :deep(code) {
    white-space: pre-wrap;
    word-break: break-word;
  }
}
</style>