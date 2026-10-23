import { ApiClient } from './request'
import type {
  LoginForm,
  PhoneRegisterForm,
  LoginResponse,
  RefreshTokenResponse,
  User,
  ChangePasswordForm,
  SmsSendPayload,
  SmsLoginForm,
  ResetPasswordBySmsForm
} from '@/types/auth'

const skipAuth = { skipAuth: true, skipAuthError: true, skipErrorHandler: true }

export function extractAuthError(error: any): string {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) return String(detail.message)
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
  return error?.message || '请求失败'
}

export const authApi = {
  login: (data: LoginForm) =>
    ApiClient.post<LoginResponse>('/api/auth/login', data, skipAuth),

  loginBySms: (data: SmsLoginForm) =>
    ApiClient.post<LoginResponse>('/api/auth/login/sms', data, skipAuth),

  register: (data: PhoneRegisterForm) =>
    ApiClient.post<LoginResponse>('/api/auth/register', data, skipAuth),

  getCaptcha: () =>
    ApiClient.get<{ captcha_id: string; image_base64: string }>(
      '/api/auth/captcha',
      undefined,
      skipAuth
    ),

  sendSmsCode: (data: SmsSendPayload) =>
    ApiClient.post<{ expires_in: number; resend_after: number }>(
      '/api/auth/sms/send',
      data,
      skipAuth
    ),

  resetPasswordBySms: (data: ResetPasswordBySmsForm) =>
    ApiClient.post('/api/auth/password/reset-by-sms', data, skipAuth),

  logout: () => ApiClient.post('/api/auth/logout'),

  refreshToken: (refreshToken: string) =>
    ApiClient.post<RefreshTokenResponse>('/api/auth/refresh', { refresh_token: refreshToken }),

  getUserInfo: () => ApiClient.get<User>('/api/auth/me'),

  updateUserInfo: (data: Partial<User>) =>
    ApiClient.put<User>('/api/auth/me', data),

  changePassword: (data: ChangePasswordForm) =>
    ApiClient.post('/api/auth/change-password', data),

  /** 管理员重置他人密码（与忘记密码接口不同） */
  resetPassword: (username: string, new_password: string) =>
    ApiClient.post('/api/auth/reset-password', { username, new_password })
}
