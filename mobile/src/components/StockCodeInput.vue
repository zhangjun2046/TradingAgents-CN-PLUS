<template>
  <view class="code-field">
    <view class="code-box" :class="{ 'is-error': showError, 'is-focus': focused }">
      <text class="code-icon">↗</text>
      <input
        class="code-input"
        type="text"
        :value="modelValue"
        :placeholder="placeholder"
        :maxlength="10"
        confirm-type="done"
        @input="onInput"
        @focus="focused = true"
        @blur="focused = false"
      />
      <text v-if="stockName && valid" class="code-name">{{ stockName }}</text>
      <text v-if="modelValue" class="code-clear" @click="clear">✕</text>
    </view>
    <view v-if="message" class="code-tip" :class="valid ? 'is-ok' : 'is-bad'">
      <text>{{ valid ? "✓ " : "ⓘ " }}{{ message }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";

defineProps<{
  modelValue: string;
  placeholder: string;
  /** 代码是否合法 */
  valid: boolean;
  /** 校验提示（合法时为成功文案，非法时为错误文案，空输入时为空串） */
  message: string;
  /** 是否展示错误态（提交失败或已输入但不合法） */
  showError: boolean;
  /** 股票名称标签（查询失败时为空） */
  stockName: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const focused = ref(false);

function onInput(e: Event) {
  const value = (e as unknown as { detail: { value: string } }).detail.value;
  emit("update:modelValue", value);
}

function clear() {
  emit("update:modelValue", "");
}
</script>

<style lang="scss" scoped>
.code-box {
  display: flex;
  align-items: center;
  height: 88rpx;
  padding: 0 24rpx;
  border: 2rpx solid #dcdfe6;
  border-radius: 16rpx;
  background: #fff;
  box-sizing: border-box;

  &.is-focus {
    border-color: #409eff;
    box-shadow: 0 0 0 4rpx rgba(64, 158, 255, 0.15);
  }

  &.is-error {
    border-color: #f56c6c;
  }
}

.code-icon {
  color: #409eff;
  font-size: 32rpx;
  margin-right: 16rpx;
}

.code-input {
  flex: 1;
  min-width: 0;
  font-size: 32rpx;
  font-weight: 600;
  color: #303133;
}

.code-name {
  flex-shrink: 0;
  margin-left: 12rpx;
  padding: 4rpx 14rpx;
  font-size: 22rpx;
  color: #409eff;
  background: #ecf5ff;
  border-radius: 8rpx;
}

.code-clear {
  flex-shrink: 0;
  margin-left: 16rpx;
  padding: 8rpx;
  font-size: 26rpx;
  color: #c0c4cc;
}

.code-tip {
  margin-top: 10rpx;
  font-size: 22rpx;

  &.is-ok {
    color: #67c23a;
  }

  &.is-bad {
    color: #f56c6c;
  }
}
</style>
