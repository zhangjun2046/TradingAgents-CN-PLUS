<template>
  <el-button :disabled="disabled || counting" :loading="sending" @click="send">
    {{ counting ? `${remain}s` : '获取验证码' }}
  </el-button>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi, extractAuthError } from '@/api/auth'
import type { SmsScene } from '@/types/auth'

const props = defineProps<{
  phone: string
  scene: SmsScene
  captchaId: string
  captchaCode: string
}>()

const emit = defineEmits<{
  sent: []
  needRefresh: []
}>()

const sending = ref(false)
const remain = ref(0)
let timer: number | undefined

const phoneOk = computed(() => /^1[3-9]\d{9}$/.test((props.phone || '').trim()))
const disabled = computed(
  () => !phoneOk.value || !props.captchaId || !(props.captchaCode || '').trim()
)

function startCount(seconds: number) {
  remain.value = seconds
  window.clearInterval(timer)
  timer = window.setInterval(() => {
    remain.value -= 1
    if (remain.value <= 0) {
      window.clearInterval(timer)
      remain.value = 0
    }
  }, 1000)
}

const counting = computed(() => remain.value > 0)

async function send() {
  if (disabled.value || counting.value || sending.value) return
  sending.value = true
  try {
    const res = await authApi.sendSmsCode({
      phone: props.phone.trim(),
      scene: props.scene,
      platform: 'pc',
      captcha_id: props.captchaId,
      captcha_code: props.captchaCode.trim()
    })
    const data = res.data || (res as any)
    ElMessage.success('验证码已发送')
    startCount(Number(data.resend_after) || 60)
    emit('sent')
    emit('needRefresh')
  } catch (error) {
    ElMessage.error(extractAuthError(error))
    emit('needRefresh')
  } finally {
    sending.value = false
  }
}

onUnmounted(() => {
  window.clearInterval(timer)
})
</script>
