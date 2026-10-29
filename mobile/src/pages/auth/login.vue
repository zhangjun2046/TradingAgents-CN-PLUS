<template>
  <view class="ha-page login-page">
    <view class="login-title">登录</view>
    <view class="tabs">
      <text :class="['tab', tab === 'password' ? 'active' : '']" @click="tab = 'password'">密码登录</text>
      <text :class="['tab', tab === 'sms' ? 'active' : '']" @click="tab = 'sms'">验证码登录</text>
    </view>

    <view class="login-form" v-if="tab === 'password'">
      <input class="login-input" v-model="username" placeholder="用户名或手机号" />
      <PasswordInput v-model="password" placeholder="请输入密码" @confirm="onPasswordLogin" />
      <button class="ha-btn-primary login-btn" :loading="loading" @click="onPasswordLogin">登录</button>
    </view>

    <view class="login-form" v-else>
      <input class="login-input" v-model="phone" maxlength="11" placeholder="11 位手机号" type="number" />
      <CaptchaImage ref="captchaRef" v-model="captchaCode" @change-id="captchaId = $event" />
      <view class="sms-row">
        <input class="login-input sms-input" v-model="smsCode" maxlength="6" placeholder="6 位短信码" />
        <SmsCodeButton
          :phone="phone"
          scene="login"
          :captcha-id="captchaId"
          :captcha-code="captchaCode"
          @need-refresh="refreshCaptcha"
        />
      </view>
      <button class="ha-btn-primary login-btn" :loading="loading" @click="onSmsLogin">登录</button>
    </view>

    <view class="auth-links">
      <text @click="go('/pages/auth/register')">注册账号</text>
      <text @click="go('/pages/auth/forgot')">忘记密码</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { useAuthStore } from "@/stores/auth";
import { goAfterLogin } from "@/utils/guard";
import CaptchaImage from "@/components/CaptchaImage.vue";
import SmsCodeButton from "@/components/SmsCodeButton.vue";
import PasswordInput from "@/components/PasswordInput.vue";

const auth = useAuthStore();
const tab = ref<"password" | "sms">("password");
const username = ref("");
const password = ref("");
const phone = ref("");
const captchaId = ref("");
const captchaCode = ref("");
const smsCode = ref("");
const captchaRef = ref<{ refresh: () => void } | null>(null);
const loading = ref(false);
const redirect = ref("/pages/analysis/single");

onLoad((query) => {
  if (query?.redirect) {
    redirect.value = decodeURIComponent(String(query.redirect));
  }
});

function refreshCaptcha() {
  captchaRef.value?.refresh?.();
}

function go(url: string) {
  uni.navigateTo({ url });
}

async function onPasswordLogin() {
  if (!username.value.trim() || !password.value) {
    uni.showToast({ title: "请输入用户名和密码", icon: "none" });
    return;
  }
  loading.value = true;
  try {
    await auth.login(username.value.trim(), password.value);
    uni.showToast({ title: "登录成功", icon: "success" });
    setTimeout(() => goAfterLogin(redirect.value), 400);
  } catch {
    // toast 已在 request 中处理
  } finally {
    loading.value = false;
  }
}

async function onSmsLogin() {
  if (!/^1[3-9]\d{9}$/.test(phone.value) || !smsCode.value) {
    uni.showToast({ title: "请填写手机号和短信验证码", icon: "none" });
    return;
  }
  loading.value = true;
  try {
    await auth.loginBySms(phone.value, smsCode.value);
    uni.showToast({ title: "登录成功", icon: "success" });
    setTimeout(() => goAfterLogin(redirect.value), 400);
  } catch {
    refreshCaptcha();
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
  margin-bottom: 32rpx;
  text-align: center;
}
.tabs {
  display: flex;
  justify-content: center;
  gap: 48rpx;
  margin-bottom: 24rpx;
}
.tab {
  font-size: 16px;
  color: #909399;
  padding-bottom: 8rpx;
}
.tab.active {
  color: #409eff;
  border-bottom: 4rpx solid #409eff;
  font-weight: 600;
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
.sms-row {
  display: flex;
  gap: 16rpx;
}
.sms-input {
  flex: 1;
}
.login-btn {
  margin-top: 16rpx;
  height: 88rpx;
  line-height: 88rpx;
}
.auth-links {
  margin-top: 32rpx;
  display: flex;
  justify-content: space-between;
  color: #409eff;
  font-size: 14px;
}
</style>
