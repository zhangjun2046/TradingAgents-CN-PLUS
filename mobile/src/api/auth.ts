import { request } from "./request";

export interface LoginUser {
  id: string;
  username: string;
  email?: string | null;
  phone?: string | null;
  name?: string;
  is_admin?: boolean;
}

export interface LoginResult {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: LoginUser;
}

export type SmsScene = "register" | "login" | "reset";

export function login(username: string, password: string) {
  return request<LoginResult>({
    url: "/api/auth/login",
    method: "POST",
    data: { username, password },
    skipAuth: true,
  });
}

export function loginBySms(phone: string, code: string) {
  return request<LoginResult>({
    url: "/api/auth/login/sms",
    method: "POST",
    data: { phone, code },
    skipAuth: true,
  });
}

export function register(payload: {
  phone: string;
  code: string;
  password: string;
  agreed: boolean;
}) {
  return request<LoginResult>({
    url: "/api/auth/register",
    method: "POST",
    data: payload,
    skipAuth: true,
  });
}

export function getCaptcha() {
  return request<{ captcha_id: string; image_base64: string }>({
    url: "/api/auth/captcha",
    method: "GET",
    skipAuth: true,
  });
}

export function sendSmsCode(payload: {
  phone: string;
  scene: SmsScene;
  platform: "h5" | "pc";
  captcha_id: string;
  captcha_code: string;
}) {
  return request<{ expires_in: number; resend_after: number }>({
    url: "/api/auth/sms/send",
    method: "POST",
    data: payload,
    skipAuth: true,
  });
}

export function resetPasswordBySms(payload: {
  phone: string;
  code: string;
  new_password: string;
}) {
  return request<Record<string, never>>({
    url: "/api/auth/password/reset-by-sms",
    method: "POST",
    data: payload,
    skipAuth: true,
  });
}

export function changePassword(old_password: string, new_password: string) {
  return request<Record<string, never>>({
    url: "/api/auth/change-password",
    method: "POST",
    data: { old_password, new_password },
  });
}

export function fetchMe() {
  return request<LoginUser>({
    url: "/api/auth/me",
    method: "GET",
  });
}

export function logout() {
  return request<Record<string, never>>({
    url: "/api/auth/logout",
    method: "POST",
  });
}
