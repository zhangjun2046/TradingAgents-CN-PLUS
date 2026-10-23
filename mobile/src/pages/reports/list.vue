<template>
  <view class="ha-page">
    <view class="ha-empty">我的报告（P3.5 填充）</view>
  </view>
</template>

<script setup lang="ts">
import { onShow } from "@dcloudio/uni-app";
import { ensureLogin } from "@/utils/guard";

onShow(() => {
  ensureLogin("/pages/reports/list");
});
</script>

<style lang="scss" scoped></style>
