<template>
  <view class="progress-card">
    <view class="head">
      <view class="head-left">
        <text class="head-icon" :class="{ 'is-done': completed }">{{ completed ? "✓" : "◔" }}</text>
        <text class="head-title">智能分析进度</text>
      </view>
      <text class="head-percent" :class="{ 'is-done': completed }">{{ percentText }}</text>
    </view>

    <view class="bar">
      <view class="bar-fill" :class="{ 'is-done': completed }" :style="{ width: percentText }"></view>
    </view>

    <view class="stats">
      <view class="stat">
        <text class="stat-label">已用时间</text>
        <text class="stat-value">{{ formatDuration(elapsedSeconds) }}</text>
      </view>
      <view class="stat">
        <text class="stat-label">预计剩余</text>
        <text class="stat-value is-green">{{ completed ? "00分 00秒" : remainingText }}</text>
      </view>
      <view class="stat">
        <text class="stat-label">分析师团队</text>
        <text class="stat-value is-team">{{ teamText }}</text>
      </view>
    </view>

    <!-- 当前步骤（进行中） -->
    <view v-if="!completed && currentText" class="current">
      <text class="current-label">当前步骤</text>
      <text class="current-text">{{ currentText }}</text>
    </view>

    <!-- 步骤列表（完成后默认收起，避免把完成卡挤到屏幕下方） -->
    <view v-if="steps.length > 0" class="steps-toggle" @click="showSteps = !showSteps">
      <text>步骤详情（{{ doneCount }}/{{ steps.length }}）</text>
      <text class="steps-toggle-arrow">{{ showSteps ? "收起 ▴" : "展开 ▾" }}</text>
    </view>
    <view v-if="steps.length > 0 && showSteps" class="steps">
      <view
        v-for="(step, index) in steps"
        :key="index"
        class="step"
        :class="stepClass(step.status)"
      >
        <text class="step-name">{{ index + 1 }}. {{ step.name }}</text>
        <text class="step-state">{{ stepStateText(step.status) }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { TaskStep } from "@/api/analysis";

const props = withDefaults(
  defineProps<{
    /** 0-100 */
    progress: number;
    completed?: boolean;
    /** 后端返回的当前步骤名 */
    stepName?: string;
    /** 后端最近一条进度消息，步骤名缺失时兜底展示 */
    message?: string;
    elapsedSeconds?: number;
    remainingSeconds?: number;
    analystNames?: string[];
    steps?: TaskStep[];
  }>(),
  {
    completed: false,
    stepName: "",
    message: "",
    elapsedSeconds: 0,
    remainingSeconds: 0,
    analystNames: () => [],
    steps: () => [],
  }
);

/** 步骤列表展开状态：进行中展开，完成后自动收起 */
const showSteps = ref(!props.completed);
watch(
  () => props.completed,
  (done) => {
    showSteps.value = !done;
  }
);

const doneCount = computed(
  () => props.steps.filter((s) => s.status === "completed").length
);

const percentText = computed(() => {
  const p = props.completed ? 100 : Math.round(Math.min(100, Math.max(0, props.progress)));
  return `${p}%`;
});

const currentText = computed(() => props.stepName || props.message || "正在准备分析...");

const teamText = computed(() =>
  props.analystNames.length > 0
    ? props.analystNames.map((n) => n.replace("分析师", "")).join("/")
    : "-"
);

/** 剩余时间为 0 且仍在运行时，说明后端无法估算 */
const remainingText = computed(() =>
  props.remainingSeconds > 0 ? formatDuration(props.remainingSeconds) : "估算中"
);

/** 秒 → 「04分 32秒」 */
function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds || 0));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${mm}分 ${ss}秒`;
}

function stepClass(status: string): string {
  if (status === "completed") return "is-completed";
  if (status === "current") return "is-current";
  if (status === "failed") return "is-failed";
  return "is-pending";
}

function stepStateText(status: string): string {
  if (status === "completed") return "✓ 完成";
  if (status === "current") return "进行中";
  if (status === "failed") return "失败";
  return "待执行";
}
</script>

<style lang="scss" scoped>
.progress-card {
  margin-bottom: 24rpx;
  padding: 28rpx 32rpx;
  border-radius: 24rpx;
  background: #fff;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.head-left {
  display: flex;
  align-items: center;
}

.head-icon {
  margin-right: 12rpx;
  font-size: 30rpx;
  color: #409eff;

  &.is-done {
    color: #10b981;
  }
}

.head-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #303133;
}

.head-percent {
  font-size: 40rpx;
  font-weight: 700;
  color: #409eff;

  &.is-done {
    color: #10b981;
  }
}

.bar {
  height: 20rpx;
  margin-top: 20rpx;
  border-radius: 10rpx;
  background: #ebeef5;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 10rpx;
  background: linear-gradient(90deg, #3b82f6, #1d4ed8);
  transition: width 0.4s ease;

  &.is-done {
    background: linear-gradient(90deg, #1d4ed8, #10b981);
  }
}

.stats {
  display: flex;
  margin-top: 24rpx;
  padding: 20rpx 8rpx;
  border-radius: 16rpx;
  background: #f5f7fa;
}

.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 8rpx;
  text-align: center;
}

.stat-label {
  font-size: 22rpx;
  color: #909399;
}

.stat-value {
  margin-top: 8rpx;
  font-size: 26rpx;
  font-weight: 700;
  color: #303133;

  &.is-green {
    color: #10b981;
  }

  &.is-team {
    font-size: 24rpx;
  }
}

.current {
  display: flex;
  flex-direction: column;
  margin-top: 20rpx;
  padding: 16rpx 20rpx;
  border-radius: 12rpx;
  background: #ecf5ff;
}

.current-label {
  font-size: 22rpx;
  color: #909399;
}

.current-text {
  margin-top: 4rpx;
  font-size: 26rpx;
  color: #409eff;
  font-weight: 600;
}

.steps-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20rpx;
  padding: 8rpx 4rpx;
  font-size: 24rpx;
  font-weight: 600;
  color: #606266;
}

.steps-toggle-arrow {
  color: #409eff;
}

.steps {
  margin-top: 8rpx;
}

.step {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
  padding: 16rpx 20rpx;
  border-radius: 12rpx;
  font-size: 24rpx;

  &.is-completed {
    background: #e8f8ef;
    color: #166534;
  }

  &.is-current {
    background: #ecf5ff;
    color: #409eff;
    font-weight: 600;
  }

  &.is-pending {
    background: #f5f7fa;
    color: #909399;
  }

  &.is-failed {
    background: #fef0f0;
    color: #f56c6c;
  }
}

.step-name {
  flex: 1;
  padding-right: 16rpx;
}

.step-state {
  flex-shrink: 0;
  font-weight: 600;
}
</style>
