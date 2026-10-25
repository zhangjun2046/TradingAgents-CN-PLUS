<template>
  <picker
    mode="selector"
    :range="labels"
    :value="currentIndex"
    :disabled="options.length === 0"
    @change="onChange"
  >
    <view class="model-box">
      <text class="model-name">{{ current ? current.display_name : "暂无可选模型" }}</text>
      <view v-if="current" class="model-tags">
        <text class="tag tag-level">{{ levelText }}</text>
        <text v-if="showFast" class="tag tag-fast">⚡ 快速</text>
        <text class="tag tag-provider">{{ current.provider }}</text>
      </view>
      <text class="model-arrow">▾</text>
    </view>
  </picker>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { PublicModel } from "@/constants/models";

const props = defineProps<{
  options: PublicModel[];
  modelValue: string;
  /** quick：快速分析模型；deep：深度决策模型（影响标签展示） */
  variant: "quick" | "deep";
}>();

const emit = defineEmits<{ (e: "update:modelValue", value: string): void }>();

const labels = computed(() => props.options.map((o) => o.display_name));

const currentIndex = computed(() => {
  const idx = props.options.findIndex((o) => o.name === props.modelValue);
  return idx >= 0 ? idx : 0;
});

const current = computed(() => props.options[currentIndex.value]);

/** 能力等级 → 标签文案 */
const levelText = computed(() => {
  const level = current.value?.capability_level ?? 2;
  if (props.variant === "deep" && level >= 4) return "深度推理";
  if (level <= 1) return "基础";
  if (level >= 4) return "高级";
  return "标准";
});

const showFast = computed(
  () => props.variant === "quick" && (current.value?.capability_level ?? 2) <= 3
);

function onChange(e: { detail: { value: number | string } }) {
  const option = props.options[Number(e.detail.value)];
  if (option) emit("update:modelValue", option.name);
}
</script>

<style lang="scss" scoped>
.model-box {
  display: flex;
  align-items: center;
  min-height: 80rpx;
  padding: 12rpx 20rpx;
  border: 2rpx solid #dcdfe6;
  border-radius: 12rpx;
  background: #fff;
  box-sizing: border-box;
}

.model-name {
  flex-shrink: 1;
  min-width: 0;
  font-size: 24rpx;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-tags {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  flex-shrink: 0;
  gap: 6rpx;
  margin-left: 10rpx;
}

.tag {
  padding: 2rpx 10rpx;
  border-radius: 8rpx;
  font-size: 18rpx;
  white-space: nowrap;
}

.tag-level {
  color: #409eff;
  background: #ecf5ff;
}

.tag-fast {
  color: #e6a23c;
  background: #fdf6ec;
}

.tag-provider {
  color: #909399;
  background: transparent;
}

.model-arrow {
  flex-shrink: 0;
  margin-left: auto;
  padding-left: 12rpx;
  color: #909399;
}
</style>
