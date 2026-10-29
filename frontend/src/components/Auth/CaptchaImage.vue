<template>
  <div class="captcha-row">
    <el-input
      :model-value="modelValue"
      maxlength="8"
      placeholder="图形验证码"
      @update:model-value="emit('update:modelValue', $event)"
      @keyup.enter="emit('enter')"
    />
    <button type="button" class="captcha-img-btn" :disabled="loading" @click="refresh">
      <img v-if="imageSrc" :src="imageSrc" alt="图形验证码，点击刷新" />
      <span v-else>{{ loading ? '加载中' : '点击获取' }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi, extractAuthError } from '@/api/auth'

defineProps<{ modelValue: string }>()
const emit = defineEmits<{
  'update:modelValue': [string]
  changeId: [string]
  enter: []
}>()

const captchaId = ref('')
const imageBase64 = ref('')
const loading = ref(false)

const imageSrc = computed(() => {
  if (!imageBase64.value) return ''
  return imageBase64.value.startsWith('data:')
    ? imageBase64.value
    : `data:image/png;base64,${imageBase64.value}`
})

async function refresh() {
  loading.value = true
  try {
    const res = await authApi.getCaptcha()
    const data = res.data || (res as any)
    captchaId.value = data.captcha_id
    imageBase64.value = data.image_base64
    emit('changeId', captchaId.value)
    emit('update:modelValue', '')
  } catch (error) {
    ElMessage.error(extractAuthError(error) || '图形验证码加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
})

defineExpose({ refresh, captchaId })
</script>

<style scoped>
.captcha-row {
  display: flex;
  gap: 8px;
  width: 100%;
}

.captcha-img-btn {
  flex: 0 0 130px;
  height: 40px;
  padding: 0;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  overflow: hidden;
}

.captcha-img-btn img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
</style>
