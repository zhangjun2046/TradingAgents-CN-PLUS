<template>
  <view class="ha-page login-page">
    <view class="login-title">修改密码</view>
    <view class="login-form">
      <input class="login-input" v-model="oldPassword" password placeholder="当前密码" />
      <input class="login-input" v-model="newPassword" password placeholder="新密码 6～64 位" />
      <input class="login-input" v-model="confirm" password placeholder="确认新密码" />
      <button class="ha-btn-primary login-btn" :loading="loading" @click="onSubmit">保存</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { changePassword } from "@/api/auth";
import { ensureLogin } from "@/utils/guard";

const oldPassword = ref("");
const newPassword = ref("");
const confirm = ref("");
const loading = ref(false);

onShow(() => {
  ensureLogin("/pages/auth/change-password");
});

async function onSubmit() {
  if (!oldPassword.value || !newPassword.value) {
    uni.showToast({ title: "请填写完整", icon: "none" });
    return;
  }
  if (newPassword.value.length < 6 || newPassword.value.length > 64) {
    uni.showToast({ title: "密码长度须为 6～64 位", icon: "none" });
    return;
  }
  if (newPassword.value !== confirm.value) {
    uni.showToast({ title: "两次密码不一致", icon: "none" });
    return;
  }
  loading.value = true;
  try {
    await changePassword(oldPassword.value, newPassword.value);
    uni.showToast({ title: "密码修改成功", icon: "success" });
    setTimeout(() => uni.navigateBack(), 400);
  } catch {
    // toast 已处理
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
.login-btn {
  height: 88rpx;
  line-height: 88rpx;
}
</style>
