<template>
  <view class="ha-page">
    <view class="mine-card" v-if="auth.isLoggedIn">
      <text class="mine-name">{{ displayName }}</text>
      <text class="mine-phone">{{ displayPhone }}</text>
      <button class="ha-btn-primary" @click="goChange">修改密码</button>
      <button class="ghost-btn" @click="onLogout">退出登录</button>
    </view>
    <view class="mine-card" v-else>
      <text class="mine-hint">未登录</text>
      <button class="ha-btn-primary" @click="goLogin">登录 / 注册</button>
    </view>

    <view class="mine-card links">
      <text class="link-item" @click="go('/pages/legal/agreement')">《用户协议》</text>
      <text class="link-item" @click="go('/pages/legal/privacy')">《隐私政策》</text>
      <text class="meta">版本 1.0</text>
      <text class="meta source">
        本产品是 HunterAgents。分析能力参考开源 TradingAgents，本产品不是该项目或其 CN 版本。用途与免责以用户协议为准。
      </text>
      <text class="meta beian" @click="openBeian">京ICP备2021035986号-4</text>
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

const displayPhone = computed(() => {
  const p = auth.user?.phone;
  if (p) return p;
  const u = auth.user?.username || "";
  if (/^1[3-9]\d{9}$/.test(u)) return `${u.slice(0, 3)}****${u.slice(-4)}`;
  return "";
});

onShow(() => {
  auth.hydrateFromStorage();
  if (auth.isLoggedIn) {
    auth.refreshMe().catch(() => undefined);
  }
});

function go(url: string) {
  uni.navigateTo({ url });
}

function openBeian() {
  if (typeof window !== "undefined") {
    window.open("https://beian.miit.gov.cn/", "_blank", "noopener");
  }
}

function goLogin() {
  uni.navigateTo({ url: "/pages/auth/login?redirect=/pages/mine/index" });
}

function goChange() {
  uni.navigateTo({ url: "/pages/auth/change-password" });
}

async function onLogout() {
  await auth.logout();
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
  margin-bottom: 24rpx;
}
.mine-name {
  font-size: 18px;
  color: var(--ha-text-primary);
  font-weight: 600;
}
.mine-phone {
  font-size: 16px;
  color: #606266;
}
.mine-hint {
  font-size: 14px;
  color: var(--ha-text-secondary);
}
.ghost-btn {
  background: #fff;
  color: #f56c6c;
  border: 1px solid #f56c6c;
  border-radius: 4px;
}
.links {
  gap: 16rpx;
}
.link-item {
  color: #409eff;
  font-size: 14px;
}
.meta {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}
.source {
  margin-top: 8rpx;
}
.beian {
  margin-top: 8rpx;
  color: #409eff;
}
</style>
