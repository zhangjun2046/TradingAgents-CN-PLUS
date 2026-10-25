<template>
  <view class="analysts">
    <view class="analyst-grid">
      <view
        v-for="item in ANALYSTS"
        :key="item.id"
        class="analyst-card"
        :class="{
          'is-active': isSelected(item.id),
          'is-disabled': isDisabled(item.id),
        }"
        @click="toggle(item.id)"
      >
        <view class="analyst-icon">{{ item.icon }}</view>
        <view class="analyst-body">
          <text class="analyst-name">{{ item.name }}</text>
          <text class="analyst-desc">{{ item.description }}</text>
        </view>
        <text v-if="isSelected(item.id)" class="analyst-check">✓</text>
      </view>
    </view>
    <view v-if="socialDisabled" class="analyst-tip">
      <text>ⓘ A股市场暂不支持社媒分析（国内数据源限制）</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { ANALYSTS, SOCIAL_ANALYST_ID } from "@/constants/analysts";

const props = defineProps<{
  /** 选中的分析师 ID */
  modelValue: string[];
  /** A 股时社媒分析师禁用 */
  socialDisabled: boolean;
}>();

const emit = defineEmits<{ (e: "update:modelValue", value: string[]): void }>();

const selectedSet = computed(() => new Set(props.modelValue));

function isSelected(id: string): boolean {
  return selectedSet.value.has(id);
}

function isDisabled(id: string): boolean {
  return props.socialDisabled && id === SOCIAL_ANALYST_ID;
}

function toggle(id: string) {
  if (isDisabled(id)) {
    uni.showToast({ title: "A股暂不支持社媒分析", icon: "none" });
    return;
  }
  const next = isSelected(id)
    ? props.modelValue.filter((v) => v !== id)
    : [...props.modelValue, id];
  emit("update:modelValue", next);
}
</script>

<style lang="scss" scoped>
.analyst-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.analyst-card {
  position: relative;
  display: flex;
  align-items: center;
  width: calc(50% - 8rpx);
  min-height: 132rpx;
  padding: 16rpx;
  border: 2rpx solid #dcdfe6;
  border-radius: 16rpx;
  background: #fff;
  box-sizing: border-box;

  &.is-active {
    border-color: #409eff;
    background: #f2f8ff;
  }

  &.is-disabled {
    opacity: 0.55;
    border-style: dashed;
    background: #f5f7fa;
  }
}

.analyst-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56rpx;
  height: 56rpx;
  margin-right: 12rpx;
  border-radius: 50%;
  background: #e6f0ff;
  color: #409eff;
  font-size: 28rpx;
}

.analyst-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.analyst-name {
  font-size: 26rpx;
  font-weight: 600;
  color: #303133;
}

.analyst-desc {
  margin-top: 4rpx;
  font-size: 20rpx;
  line-height: 1.4;
  color: #909399;
}

.analyst-check {
  flex-shrink: 0;
  margin-left: 8rpx;
  font-size: 28rpx;
  font-weight: 700;
  color: #409eff;
}

.analyst-tip {
  margin-top: 16rpx;
  padding: 14rpx 20rpx;
  border-radius: 12rpx;
  background: #f0f2f5;
  font-size: 22rpx;
  color: #909399;
}
</style>
