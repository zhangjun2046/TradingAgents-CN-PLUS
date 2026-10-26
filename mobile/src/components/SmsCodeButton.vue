<template>
  <button
    class="sms-btn"
    :disabled="disabled || counting"
    :loading="sending"
    @click="send"
  >
    {{ counting ? `${remain}s` : "获取验证码" }}
  </button>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { sendSmsCode, type SmsScene } from "@/api/auth";

const props = defineProps<{
  phone: string;
  scene: SmsScene;
  captchaId: string;
  captchaCode: string;
}>();

const emit = defineEmits<{
  sent: [];
  needRefresh: [];
}>();

const sending = ref(false);
const remain = ref(0);
let timer: ReturnType<typeof setInterval> | undefined;

const phoneOk = computed(() => /^1[3-9]\d{9}$/.test((props.phone || "").trim()));
const disabled = computed(
  () => !phoneOk.value || !props.captchaId || !(props.captchaCode || "").trim()
);
const counting = computed(() => remain.value > 0);

function startCount(seconds: number) {
  remain.value = seconds;
  if (timer) clearInterval(timer);
  timer = setInterval(() => {
    remain.value -= 1;
    if (remain.value <= 0 && timer) {
      clearInterval(timer);
      remain.value = 0;
      emit("needRefresh");
    }
  }, 1000);
}

async function send() {
  if (disabled.value || counting.value || sending.value) {
    if (!phoneOk.value) {
      uni.showToast({ title: "请输入正确手机号", icon: "none" });
    } else if (!(props.captchaCode || "").trim()) {
      uni.showToast({ title: "请先填写图形验证码", icon: "none" });
    }
    return;
  }
  sending.value = true;
  try {
    const data = await sendSmsCode({
      phone: props.phone.trim(),
      scene: props.scene,
      platform: "h5",
      captcha_id: props.captchaId,
      captcha_code: props.captchaCode.trim(),
    });
    uni.showToast({ title: "验证码已发送", icon: "success" });
    startCount(Number(data.resend_after) || 60);
    emit("sent");
  } catch {
    emit("needRefresh");
  } finally {
    sending.value = false;
  }
}

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style lang="scss" scoped>
.sms-btn {
  flex: 0 0 220rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 14px;
  background: #ecf5ff;
  color: #409eff;
  border: 1px solid #409eff;
  border-radius: 4px;
  padding: 0 12rpx;
}
.sms-btn[disabled] {
  opacity: 0.6;
}
</style>
