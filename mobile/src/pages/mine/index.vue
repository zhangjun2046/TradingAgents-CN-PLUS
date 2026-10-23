<template>
  <view class="ha-page">
    <view class="mine-card" v-if="auth.isLoggedIn">
      <text class="mine-name">{{ displayName }}</text>
      <text class="mine-hint">已登录（账号页由 P3.2 完善）</text>
      <button class="ha-btn-primary" @click="onLogout">退出登录</button>
    </view>
    <view class="mine-card" v-else>
      <text class="mine-hint">未登录</text>
      <button class="ha-btn-primary" @click="goLogin">登录</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

const displayName = computed(
  () => auth.user?.name || auth.user?.username || "用户"
);

onShow(() => {
  auth.hydrateFromStorage();
});

function goLogin() {
  uni.navigateTo({ url: "/pages/auth/login?redirect=/pages/mine/index" });
}

function onLogout() {
  auth.logoutLocal();
  uni.showToast({ title: "已退出", icon: "none" });
}
</script>

<style lang="scss" scoped>
.mine-card {
  background: #fff;
  border-radius: 8px;
  padding: 32rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.mine-name {
  font-size: 18px;
  color: var(--ha-text-primary);
  font-weight: 600;
}

.mine-hint {
  font-size: 14px;
  color: var(--ha-text-secondary);
}
</style>
