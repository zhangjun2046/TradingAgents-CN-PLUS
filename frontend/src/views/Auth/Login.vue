<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <img src="/logo.svg" alt="TradingAgents-CN" class="logo" />
        <h1 class="title">TradingAgents-CN</h1>
        <p class="subtitle">多智能体股票分析学习平台</p>
      </div>

      <el-card class="login-card" shadow="always">
        <el-tabs v-model="loginTab">
          <el-tab-pane label="密码登录" name="password">
            <el-form
              :model="loginForm"
              :rules="loginRules"
              ref="loginFormRef"
              label-position="top"
              size="large"
            >
              <el-form-item label="账号" prop="username">
                <el-input
                  v-model="loginForm.username"
                  placeholder="用户名或手机号"
                  prefix-icon="User"
                />
              </el-form-item>
              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="loginForm.password"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="请输入密码"
                  prefix-icon="Lock"
                  @keyup.enter="handlePasswordLogin"
                >
                  <template #suffix>
                    <span class="pwd-toggle" @click.stop="showPassword = !showPassword">
                      {{ showPassword ? '隐藏' : '显示' }}
                    </span>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  style="width: 100%"
                  :loading="loginLoading"
                  @click="handlePasswordLogin"
                >
                  登录
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="验证码登录" name="sms">
            <el-form
              :model="smsForm"
              :rules="smsRules"
              ref="smsFormRef"
              label-position="top"
              size="large"
            >
              <el-form-item label="手机号" prop="phone">
                <el-input v-model="smsForm.phone" maxlength="11" placeholder="11 位手机号" />
              </el-form-item>
              <el-form-item label="图形验证码" prop="captchaCode">
                <CaptchaImage
                  ref="captchaRef"
                  v-model="smsForm.captchaCode"
                  @change-id="smsForm.captchaId = $event"
                />
              </el-form-item>
              <el-form-item label="短信验证码" prop="code">
                <div class="sms-row">
                  <el-input v-model="smsForm.code" maxlength="6" placeholder="6 位短信码" />
                  <SmsCodeButton
                    :phone="smsForm.phone"
                    scene="login"
                    :captcha-id="smsForm.captchaId"
                    :captcha-code="smsForm.captchaCode"
                    @need-refresh="refreshCaptcha"
                  />
                </div>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  style="width: 100%"
                  :loading="loginLoading"
                  @click="handleSmsLogin"
                >
                  登录
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>

        <div class="auth-links">
          <router-link to="/register">注册账号</router-link>
          <router-link to="/forgot-password">忘记密码</router-link>
        </div>
      </el-card>

      <div class="login-footer">
        <p>&copy; 2025 TradingAgents-CN. All rights reserved.</p>
        <p class="disclaimer">
          TradingAgents-CN 是一个 AI 多 Agents 的股票分析学习平台。平台中的分析结论、观点和“投资建议”均由 AI 自动生成，仅用于学习、研究与交流，不构成任何形式的投资建议或承诺。用户据此进行的任何投资行为及其产生的风险与后果，均由用户自行承担。市场有风险，入市需谨慎。
        </p>
      </div>
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

const loginTab = ref('password')
const showPassword = ref(false)
const loginFormRef = ref()
const smsFormRef = ref()
const captchaRef = ref()
const loginLoading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const smsForm = reactive({
  phone: '',
  captchaId: '',
  captchaCode: '',
  code: ''
})

const phoneRule = {
  validator: (_: unknown, value: string, cb: (e?: Error) => void) => {
    if (!/^1[3-9]\d{9}$/.test(value || '')) cb(new Error('请输入正确手机号'))
    else cb()
  },
  trigger: 'blur'
}

const loginRules = {
  username: [{ required: true, message: '请输入用户名或手机号', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const smsRules = {
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }, phoneRule],
  captchaCode: [{ required: true, message: '请输入图形验证码', trigger: 'blur' }],
  code: [{ required: true, message: '请输入短信验证码', trigger: 'blur' }]
}

function refreshCaptcha() {
  captchaRef.value?.refresh?.()
}

function afterLogin() {
  ElMessage.success('登录成功')
  const redirectPath = authStore.getAndClearRedirectPath()
  router.push(redirectPath)
}

const handlePasswordLogin = async () => {
  if (loginLoading.value) return
  try {
    await loginFormRef.value.validate()
    loginLoading.value = true
    const success = await authStore.login({
      username: loginForm.username,
      password: loginForm.password
    })
    if (success) afterLogin()
    else ElMessage.error('用户名或密码错误')
  } catch (error: any) {
    if (error?.message && !String(error.message).includes('validate')) {
      ElMessage.error(extractAuthError(error) || '登录失败，请重试')
    }
  } finally {
    loginLoading.value = false
  }
}

const handleSmsLogin = async () => {
  if (loginLoading.value) return
  try {
    await smsFormRef.value.validate()
    loginLoading.value = true
    const success = await authStore.loginBySms(smsForm.phone, smsForm.code)
    if (success) afterLogin()
    else ElMessage.error('验证码错误或已过期')
  } catch (error: any) {
    ElMessage.error(extractAuthError(error) || '登录失败，请重试')
    refreshCaptcha()
  } finally {
    loginLoading.value = false
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
  margin-bottom: 32px;
  color: white;

  .logo {
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
  }

  .title {
    font-size: 32px;
    font-weight: 600;
    margin: 0 0 8px 0;
  }

  .subtitle {
    font-size: 16px;
    opacity: 0.9;
    margin: 0;
  }
}

.sms-row {
  display: flex;
  gap: 8px;
  width: 100%;
}

.pwd-toggle {
  cursor: pointer;
  color: var(--el-color-primary);
  font-size: 13px;
  user-select: none;
}

.auth-links {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;

  a {
    color: var(--el-color-primary);
    font-size: 14px;
  }
}

.login-footer {
  text-align: center;
  margin-top: 32px;
  color: white;
  opacity: 0.9;

  p {
    margin: 0;
    font-size: 14px;
  }

  .disclaimer {
    margin-top: 8px;
    font-size: 12px;
    line-height: 1.6;
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
    color: white;
    opacity: 0.85;
  }
}
</style>
