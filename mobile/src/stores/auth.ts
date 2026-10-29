import { defineStore } from "pinia";
import {
  login as loginApi,
  loginBySms as loginBySmsApi,
  register as registerApi,
  fetchMe,
  logout as logoutApi,
  type LoginResult,
  type LoginUser,
} from "@/api/auth";
import { tokenStorage } from "@/utils/storage";

interface AuthState {
  token: string;
  user: LoginUser | null;
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    token: tokenStorage.getToken(),
    user: tokenStorage.getUserInfo<LoginUser>(),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    applySession(data: LoginResult) {
      tokenStorage.setTokens(data.access_token, data.refresh_token);
      tokenStorage.setUserInfo(data.user);
      this.token = data.access_token;
      this.user = data.user;
    },
    async login(username: string, password: string) {
      const data = await loginApi(username, password);
      this.applySession(data);
      return data;
    },
    async loginBySms(phone: string, code: string) {
      const data = await loginBySmsApi(phone, code);
      this.applySession(data);
      return data;
    },
    async register(payload: {
      phone: string;
      code: string;
      password: string;
      agreed: boolean;
    }) {
      const data = await registerApi(payload);
      this.applySession(data);
      return data;
    },
    async refreshMe() {
      const user = await fetchMe();
      this.user = user;
      tokenStorage.setUserInfo(user);
      return user;
    },
    async logout() {
      try {
        await logoutApi();
      } catch {
        // 本地仍退出
      }
      this.logoutLocal();
    },
    logoutLocal() {
      tokenStorage.clear();
      this.token = "";
      this.user = null;
    },
    hydrateFromStorage() {
      this.token = tokenStorage.getToken();
      this.user = tokenStorage.getUserInfo<LoginUser>();
    },
  },
});
