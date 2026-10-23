<template>
  <view class="ha-page legal">
    <text class="legal-body">{{ body }}</text>
  </view>
</template>

<script setup lang="ts">
import { PRIVACY_MD, mdToText } from "@/utils/legal-texts";

const body = mdToText(PRIVACY_MD);
</script>

<style lang="scss" scoped>
.legal-body {
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
  white-space: pre-wrap;
}
</style>
