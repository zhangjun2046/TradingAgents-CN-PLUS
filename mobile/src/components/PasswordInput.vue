<template>
  <view class="pwd-wrap">
    <input
      class="pwd-input"
      :value="modelValue"
      :password="!visible"
      :placeholder="placeholder"
      @input="onInput"
      @confirm="$emit('confirm')"
    />
    <view class="pwd-toggle" @click="visible = !visible">
      <image class="pwd-icon" :src="visible ? ICON_EYE_OFF : ICON_EYE" mode="aspectFit" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";

const ICON_EYE =
  "data:image/svg+xml," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" stroke="#909399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 11s4-7 10-7 10 7 10 7-4 7-10 7S1 11 1 11z"/><circle cx="11" cy="11" r="3"/></svg>'
  );
const ICON_EYE_OFF =
  "data:image/svg+xml," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" stroke="#909399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 11 19c-6 0-10-8-10-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 11 4c6 0 10 8 10 8a18.5 18.5 0 0 1-2.16 3.19"/><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="21" y2="21"/></svg>'
  );

defineProps<{
  modelValue: string;
  placeholder?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  confirm: [];
}>();

const visible = ref(false);

function onInput(e: { detail?: { value?: string }; target?: { value?: string } }) {
  emit("update:modelValue", e.detail?.value ?? e.target?.value ?? "");
}
</script>

<style lang="scss" scoped>
.pwd-wrap {
  display: flex;
  align-items: center;
  height: 88rpx;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  padding-right: 8rpx;
}
.pwd-input {
  flex: 1;
  height: 88rpx;
  padding: 0 24rpx;
  font-size: 16px;
  border: none;
  background: transparent;
}
.pwd-toggle {
  flex: 0 0 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pwd-icon {
  width: 40rpx;
  height: 40rpx;
}
</style>
