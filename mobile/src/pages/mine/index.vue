<template>
  <view class="ha-page mine">
    <view class="profile" @click="onProfile">
      <view class="avatar">
        <image class="avatar-img" src="@/static/default-avatar.png" mode="aspectFill" />
      </view>
      <view class="profile-text">
        <text class="profile-title">{{ profileTitle }}</text>
        <text v-if="profileSub" class="profile-sub">{{ profileSub }}</text>
      </view>
    </view>

    <view class="menu">
      <view class="menu-row" @click="goChange">
        <text>修改密码</text>
        <uni-icons type="right" size="16" color="#c0c4cc" />
      </view>
      <view class="menu-row" @click="go('/pages/legal/agreement')">
        <text>用户协议</text>
        <uni-icons type="right" size="16" color="#c0c4cc" />
      </view>
      <view class="menu-row" @click="go('/pages/legal/privacy')">
        <text>隐私政策</text>
        <uni-icons type="right" size="16" color="#c0c4cc" />
      </view>
      <view class="menu-row" @click="go('/pages/mine/about')">
        <text>关于我们</text>
        <uni-icons type="right" size="16" color="#c0c4cc" />
      </view>
    </view>

    <view v-if="auth.isLoggedIn" class="menu">
      <view class="menu-row logout" @click="onLogout">
        <text>退出登录</text>
      </view>
    </view>

    <text class="beian" @click="openBeian">京ICP备2021035986号-4</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

function maskPhone(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (/^1[3-9]\d{9}$/.test(digits)) {
    return `${digits.slice(0, 3)}****${digits.slice(-4)}`;
  }
  return "";
}

const maskedPhone = computed(() => {
  const phone = auth.user?.phone?.trim() || "";
  const fromPhone = maskPhone(phone);
  if (fromPhone) return fromPhone;
  return maskPhone(auth.user?.username || "");
});

const displayName = computed(
  () => auth.user?.name || auth.user?.username || "用户"
);

const profileTitle = computed(() => {
  if (!auth.isLoggedIn) return "登录 / 注册";
  return maskedPhone.value || displayName.value;
});

const profileSub = computed(() => {
  if (!auth.isLoggedIn || !maskedPhone.value) return "";
  if (displayName.value === auth.user?.username && maskPhone(auth.user?.username || "")) {
    return "";
  }
  if (displayName.value === maskedPhone.value) return "";
  return displayName.value;
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

function onProfile() {
  if (!auth.isLoggedIn) {
    uni.navigateTo({ url: "/pages/auth/login?redirect=/pages/mine/index" });
  }
}

function goChange() {
  uni.navigateTo({ url: "/pages/auth/change-password" });
}

function onLogout() {
  uni.showModal({
    title: "退出登录",
    content: "确定退出当前账号？",
    success: async (res) => {
      if (!res.confirm) return;
      await auth.logout();
      uni.showToast({ title: "已退出", icon: "none" });
    },
  });
}
</script>

<style lang="scss" scoped>
.mine {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  padding-bottom: 120rpx;
}

.profile {
  background: #fff;
  border-radius: 12px;
  padding: 40rpx 32rpx;
  display: flex;
  align-items: center;
  gap: 28rpx;
}

.avatar {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background: #e4e7ed;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-img {
  width: 100%;
  height: 100%;
}

.profile-text {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  min-width: 0;
}

.profile-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--ha-text-primary);
}

.profile-sub {
  font-size: 14px;
  color: #909399;
}

.menu {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}

.menu-row {
  min-height: 96rpx;
  padding: 0 32rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 16px;
  color: var(--ha-text-primary);
  border-bottom: 1px solid #f2f3f5;
}

.menu-row:last-child {
  border-bottom: none;
}

.logout {
  justify-content: center;
  color: #f56c6c;
}

.beian {
  position: fixed;
  left: 0;
  right: 0;
  bottom: calc(50px + env(safe-area-inset-bottom));
  z-index: 20;
  padding: 12rpx 32rpx;
  text-align: center;
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
}
</style>
