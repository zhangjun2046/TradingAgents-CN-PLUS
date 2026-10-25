<template>
  <view class="depth">
    <view class="depth-list">
      <view
        v-for="item in DEPTH_LEVELS"
        :key="item.level"
        class="depth-item"
        :class="{ 'is-active': item.level === modelValue }"
        @click="emit('update:modelValue', item.level)"
      >
        <text class="depth-level">{{ item.level }}级{{ item.recommended ? " ★" : "" }}</text>
        <text class="depth-sub">{{ item.subtitle }}</text>
      </view>
    </view>
    <view class="depth-info">
      <view class="depth-info-text">
        <text class="depth-info-title">{{ current.title }}：</text>
        <text>{{ current.description }}</text>
      </view>
      <text class="depth-info-time">⏱ {{ current.time }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { DEPTH_LEVELS } from "@/constants/analysis";

const props = defineProps<{ modelValue: number }>();
const emit = defineEmits<{ (e: "update:modelValue", value: number): void }>();

const current = computed(
  () => DEPTH_LEVELS.find((d) => d.level === props.modelValue) || DEPTH_LEVELS[2]
);
</script>

<style lang="scss" scoped>
.depth-list {
  display: flex;
  gap: 12rpx;
}

.depth-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16rpx 0;
  border: 2rpx solid #e4e7ed;
  border-radius: 12rpx;
  background: #fff;
  color: #606266;

  &.is-active {
    border-color: #2f6fed;
    background: linear-gradient(180deg, #4d8cff, #2f6fed);
    color: #fff;
    box-shadow: 0 6rpx 16rpx rgba(47, 111, 237, 0.3);

    .depth-sub {
      color: rgba(255, 255, 255, 0.9);
    }
  }
}

.depth-level {
  font-size: 26rpx;
  font-weight: 600;
}

.depth-sub {
  margin-top: 4rpx;
  font-size: 20rpx;
  color: #909399;
}

.depth-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16rpx;
  padding: 16rpx 20rpx;
  border: 2rpx solid #cfe2ff;
  border-radius: 12rpx;
  background: #eef5ff;
  font-size: 22rpx;
  color: #3a6ea5;
}

.depth-info-text {
  flex: 1;
  min-width: 0;
  line-height: 1.5;
}

.depth-info-title {
  font-weight: 600;
}

.depth-info-time {
  flex-shrink: 0;
  margin-left: 16rpx;
  font-weight: 600;
  color: #2f6fed;
}
</style>
