import { request } from "./request";

export interface LoginUser {
  id: string;
  username: string;
  email?: string;
  name?: string;
  is_admin?: boolean;
}

export interface LoginResult {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: LoginUser;
}

/** 最简用户名密码登录（P3.1；P3.2 将扩展验证码登录等） */
export function login(username: string, password: string) {
  return request<LoginResult>({
    url: "/api/auth/login",
    method: "POST",
    data: { username, password },
    skipAuth: true,
  });
}
