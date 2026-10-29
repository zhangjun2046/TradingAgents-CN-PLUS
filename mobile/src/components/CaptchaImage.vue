<template>
  <view class="captcha-row">
    <input
      class="login-input captcha-input"
      :value="modelValue"
      maxlength="8"
      placeholder="图形验证码"
      @input="onInput"
    />
    <view class="captcha-img" @click="refresh">
      <image v-if="src" :src="src" mode="aspectFit" class="captcha-image" />
      <text v-else class="captcha-placeholder">{{ loading ? "加载中" : "点击获取" }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { getCaptcha } from "@/api/auth";

const props = defineProps<{ modelValue: string }>();
const emit = defineEmits<{
  "update:modelValue": [string];
  changeId: [string];
}>();

const captchaId = ref("");
const imageBase64 = ref("");
const loading = ref(false);

const src = computed(() => {
  if (!imageBase64.value) return "";
  return imageBase64.value.startsWith("data:")
    ? imageBase64.value
    : `data:image/png;base64,${imageBase64.value}`;
});

function onInput(e: Event) {
  const value = (e.target as HTMLInputElement)?.value ?? (e as { detail?: { value: string } }).detail?.value ?? "";
  emit("update:modelValue", value);
}

async function refresh() {
  loading.value = true;
  try {
    const data = await getCaptcha();
    captchaId.value = data.captcha_id;
    imageBase64.value = data.image_base64;
    emit("changeId", captchaId.value);
    emit("update:modelValue", "");
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  refresh();
});

defineExpose({ refresh, captchaId });
</script>

<style lang="scss" scoped>
.captcha-row {
  display: flex;
  gap: 16rpx;
  align-items: stretch;
}
.captcha-input {
  flex: 1;
}
.captcha-img {
  width: 260rpx;
  height: 88rpx;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.captcha-image {
  width: 100%;
  height: 100%;
}
.captcha-placeholder {
  font-size: 12px;
  color: #909399;
}
.login-input {
  height: 88rpx;
  padding: 0 24rpx;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 16px;
  background: #fff;
}
</style>
