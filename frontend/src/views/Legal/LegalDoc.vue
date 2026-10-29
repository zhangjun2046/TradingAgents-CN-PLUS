<template>
  <div class="legal-page">
    <el-page-header :content="title" @back="goBack" />
    <div class="legal-body" v-html="html" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{ file: string; title: string }>()
const router = useRouter()
const html = ref('<p>加载中…</p>')

const title = computed(() => props.title)

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/login')
}

onMounted(async () => {
  try {
    const res = await fetch(`/legal/${props.file}`)
    const md = await res.text()
    html.value = DOMPurify.sanitize(marked.parse(md) as string)
  } catch {
    html.value = '<p>协议文案暂不可用。</p>'
  }
})
</script>

<style scoped>
.legal-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}
.legal-body {
  margin-top: 24px;
  line-height: 1.7;
}
</style>
