<template>
  <view class="ha-page legal">
    <text class="legal-body">{{ body }}</text>
  </view>
</template>

<script setup lang="ts">
import { AGREEMENT_MD, mdToText } from "@/utils/legal-texts";

const body = mdToText(AGREEMENT_MD);
</script>

<style lang="scss" scoped>
.legal-body {
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
  white-space: pre-wrap;
}
</style>
