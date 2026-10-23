<template>
  <view class="ha-page login-page">
    <view class="login-title">登录</view>
    <view class="login-form">
      <input
        class="login-input"
        v-model="username"
        placeholder="用户名"
        confirm-type="next"
      />
      <input
        class="login-input"
        v-model="password"
        password
        placeholder="密码"
        confirm-type="done"
        @confirm="onSubmit"
      />
      <button
        class="ha-btn-primary login-btn"
        :loading="loading"
        :disabled="loading"
        @click="onSubmit"
      >
        登录
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const username = ref("");
const password = ref("");
const loading = ref(false);
const redirect = ref("/pages/analysis/single");

onLoad((query) => {
  if (query?.redirect) {
    redirect.value = decodeURIComponent(String(query.redirect));
  }
});

function goAfterLogin() {
  const target = redirect.value || "/pages/analysis/single";
  const tabRoots = [
    "/pages/analysis/single",
    "/pages/reports/list",
    "/pages/mine/index",
  ];
  if (tabRoots.some((p) => target.startsWith(p))) {
    uni.switchTab({ url: target.split("?")[0] });
    return;
  }
  uni.reLaunch({ url: target });
}

async function onSubmit() {
  if (!username.value.trim() || !password.value) {
    uni.showToast({ title: "请输入用户名和密码", icon: "none" });
    return;
  }
  loading.value = true;
  try {
    await auth.login(username.value.trim(), password.value);
    uni.showToast({ title: "登录成功", icon: "success" });
    setTimeout(goAfterLogin, 400);
  } catch {
    // toast 已在 request 中处理
  } finally {
    loading.value = false;
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  padding-top: 80rpx;
}

.login-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--ha-text-primary);
  margin-bottom: 48rpx;
  text-align: center;
}

.login-form {
  background: #fff;
  border-radius: 8px;
  padding: 32rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.login-input {
  height: 88rpx;
  padding: 0 24rpx;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 16px;
  background: #fff;
}

.login-btn {
  margin-top: 16rpx;
  height: 88rpx;
  line-height: 88rpx;
}
</style>
