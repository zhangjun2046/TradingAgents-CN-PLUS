<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <h1 class="title">注册账号</h1>
      </div>
      <el-card shadow="always">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
        >
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="form.phone" maxlength="11" placeholder="11 位手机号" />
          </el-form-item>
          <el-form-item label="图形验证码" prop="captchaCode">
            <CaptchaImage
              ref="captchaRef"
              v-model="form.captchaCode"
              @change-id="form.captchaId = $event"
            />
          </el-form-item>
          <el-form-item label="短信验证码" prop="code">
            <div class="sms-row">
              <el-input v-model="form.code" maxlength="6" placeholder="6 位短信码" />
              <SmsCodeButton
                :phone="form.phone"
                scene="register"
                :captcha-id="form.captchaId"
                :captcha-code="form.captchaCode"
                @need-refresh="captchaRef?.refresh?.()"
              />
            </div>
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" show-password placeholder="6～64 位" />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm">
            <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入密码" />
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="form.agreed">
              我已阅读并同意
              <router-link to="/legal/agreement" target="_blank">《用户协议》</router-link>
              和
              <router-link to="/legal/privacy" target="_blank">《隐私政策》</router-link>
            </el-checkbox>
            <div v-if="!form.agreed" class="hint">请勾选协议后再注册</div>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              style="width: 100%"
              :disabled="!form.agreed"
              :loading="loading"
              @click="submit"
            >
              注册
            </el-button>
          </el-form-item>
        </el-form>
        <div class="auth-links">
          <router-link to="/login">已有账号，去登录</router-link>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { extractAuthError } from '@/api/auth'
import CaptchaImage from '@/components/Auth/CaptchaImage.vue'
import SmsCodeButton from '@/components/Auth/SmsCodeButton.vue'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref()
const captchaRef = ref()
const loading = ref(false)

const form = reactive({
  phone: '',
  captchaId: '',
  captchaCode: '',
  code: '',
  password: '',
  confirm: '',
  agreed: true
})

const phoneRule = {
  validator: (_: unknown, value: string, cb: (e?: Error) => void) => {
    if (!/^1[3-9]\d{9}$/.test(value || '')) cb(new Error('请输入正确手机号'))
    else cb()
  },
  trigger: 'blur'
}

const rules = {
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }, phoneRule],
  captchaCode: [{ required: true, message: '请输入图形验证码', trigger: 'blur' }],
  code: [{ required: true, message: '请输入短信验证码', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    {
      validator: (_: unknown, value: string, cb: (e?: Error) => void) => {
        if (!value || value.length < 6 || value.length > 64) cb(new Error('密码长度须为 6～64 位'))
        else cb()
      },
      trigger: 'blur'
    }
  ],
  confirm: [
    {
      validator: (_: unknown, value: string, cb: (e?: Error) => void) => {
        if (value !== form.password) cb(new Error('两次密码不一致'))
        else cb()
      },
      trigger: 'blur'
    }
  ]
}

const submit = async () => {
  if (!form.agreed) {
    ElMessage.warning('请先同意用户协议')
    return
  }
  try {
    await formRef.value.validate()
    loading.value = true
    const ok = await authStore.register({
      phone: form.phone,
      code: form.code,
      password: form.password,
      agreed: true
    })
    if (ok) {
      ElMessage.success('注册成功')
      router.push(authStore.getAndClearRedirectPath())
    }
  } catch (error: any) {
    ElMessage.error(extractAuthError(error) || '注册失败')
    captchaRef.value?.refresh?.()
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.login-container {
  width: 100%;
  max-width: 400px;
}
.login-header {
  text-align: center;
  margin-bottom: 24px;
  color: white;
  .title {
    font-size: 28px;
    margin: 0;
  }
}
.sms-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.hint {
  color: var(--el-color-warning);
  font-size: 12px;
  margin-top: 4px;
}
.auth-links {
  text-align: center;
  a {
    color: var(--el-color-primary);
  }
}
</style>
