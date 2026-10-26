<template>
  <view class="ha-page login-page">
    <view class="login-title">注册账号</view>
    <view class="login-form">
      <input class="login-input" v-model="phone" maxlength="11" placeholder="11 位手机号" type="number" />
      <CaptchaImage ref="captchaRef" v-model="captchaCode" @change-id="captchaId = $event" />
      <view class="sms-row">
        <input class="login-input sms-input" v-model="code" maxlength="6" placeholder="6 位短信码" />
        <SmsCodeButton
          :phone="phone"
          scene="register"
          :captcha-id="captchaId"
          :captcha-code="captchaCode"
          @need-refresh="captchaRef?.refresh?.()"
        />
      </view>
      <PasswordInput v-model="password" placeholder="密码 6～64 位" />
      <PasswordInput v-model="confirm" placeholder="确认密码" />
      <label class="agree">
        <checkbox :checked="agreed" @click="agreed = !agreed" />
        <text>我已阅读并同意</text>
        <text class="link" @click.stop="go('/pages/legal/agreement')">《用户协议》</text>
        <text>和</text>
        <text class="link" @click.stop="go('/pages/legal/privacy')">《隐私政策》</text>
      </label>
      <text v-if="!agreed" class="hint">请勾选协议后再注册</text>
      <button class="ha-btn-primary login-btn" :disabled="!agreed" :loading="loading" @click="onSubmit">
        注册
      </button>
    </view>
    <view class="auth-links">
      <text @click="go('/pages/auth/login')">已有账号，去登录</text>
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
const phone = ref("");
const captchaId = ref("");
const captchaCode = ref("");
const code = ref("");
const password = ref("");
const confirm = ref("");
const agreed = ref(true);
const loading = ref(false);
const captchaRef = ref<{ refresh: () => void } | null>(null);
const redirect = ref("/pages/analysis/single");

onLoad((query) => {
  if (query?.redirect) redirect.value = decodeURIComponent(String(query.redirect));
});

function go(url: string) {
  uni.navigateTo({ url });
}

async function onSubmit() {
  if (!agreed.value) {
    uni.showToast({ title: "请先同意用户协议", icon: "none" });
    return;
  }
  if (!/^1[3-9]\d{9}$/.test(phone.value)) {
    uni.showToast({ title: "请输入正确手机号", icon: "none" });
    return;
  }
  if (!code.value) {
    uni.showToast({ title: "请输入短信验证码", icon: "none" });
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
    await auth.register({
      phone: phone.value,
      code: code.value,
      password: password.value,
      agreed: true,
    });
    uni.showToast({ title: "注册成功", icon: "success" });
    setTimeout(() => goAfterLogin(redirect.value), 400);
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
.agree {
  font-size: 13px;
  color: #606266;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4rpx;
}
.link {
  color: #409eff;
}
.hint {
  font-size: 12px;
  color: #e6a23c;
}
.auth-links {
  margin-top: 32rpx;
  text-align: center;
  color: #409eff;
  font-size: 14px;
}
</style>
