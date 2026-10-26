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
    <text class="pwd-toggle" @click="visible = !visible">{{ visible ? "隐藏" : "显示" }}</text>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";

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
  padding-right: 16rpx;
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
  flex: 0 0 auto;
  font-size: 14px;
  color: #409eff;
  padding: 0 8rpx;
}
</style>
