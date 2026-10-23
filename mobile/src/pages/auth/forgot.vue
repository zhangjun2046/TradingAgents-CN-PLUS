<template>
  <view class="ha-page login-page">
    <view class="login-title">忘记密码</view>
    <view class="login-form">
      <input class="login-input" v-model="phone" maxlength="11" placeholder="11 位手机号" type="number" />
      <CaptchaImage ref="captchaRef" v-model="captchaCode" @change-id="captchaId = $event" />
      <view class="sms-row">
        <input class="login-input sms-input" v-model="code" maxlength="6" placeholder="6 位短信码" />
        <SmsCodeButton
          :phone="phone"
          scene="reset"
          :captcha-id="captchaId"
          :captcha-code="captchaCode"
          @need-refresh="captchaRef?.refresh?.()"
        />
      </view>
      <input class="login-input" v-model="password" password placeholder="新密码 6～64 位" />
      <input class="login-input" v-model="confirm" password placeholder="确认新密码" />
      <button class="ha-btn-primary login-btn" :loading="loading" @click="onSubmit">重置密码</button>
    </view>
    <view class="auth-links">
      <text @click="uni.navigateTo({ url: '/pages/auth/login' })">返回登录</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { resetPasswordBySms } from "@/api/auth";
import CaptchaImage from "@/components/CaptchaImage.vue";
import SmsCodeButton from "@/components/SmsCodeButton.vue";

const phone = ref("");
const captchaId = ref("");
const captchaCode = ref("");
const code = ref("");
const password = ref("");
const confirm = ref("");
const loading = ref(false);
const captchaRef = ref<{ refresh: () => void } | null>(null);

async function onSubmit() {
  if (!/^1[3-9]\d{9}$/.test(phone.value) || !code.value) {
    uni.showToast({ title: "请填写手机号和短信验证码", icon: "none" });
    return;
  }
  if (!password.value || password.value.length < 6 || password.value.length > 64) {
    uni.showToast({ title: "密码长度须为 6～64 位", icon: "none" });
    return;
  }
  if (password.value !== confirm.value) {
    uni.showToast({ title: "两次密码不一致", icon: "none" });
    return;
  }
  loading.value = true;
  try {
    await resetPasswordBySms({
      phone: phone.value,
      code: code.value,
      new_password: password.value,
    });
    uni.showToast({ title: "密码已重置，请使用新密码登录", icon: "success" });
    setTimeout(() => {
      uni.redirectTo({ url: "/pages/auth/login" });
    }, 500);
  } catch {
    captchaRef.value?.refresh?.();
  } finally {
    loading.value = false;
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  padding-top: 48rpx;
}
.login-title {
  font-size: 22px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 32rpx;
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
}
.sms-row {
  display: flex;
  gap: 16rpx;
}
.sms-input {
  flex: 1;
}
.login-btn {
  height: 88rpx;
  line-height: 88rpx;
}
.auth-links {
  margin-top: 32rpx;
  text-align: center;
  color: #409eff;
  font-size: 14px;
}
</style>
