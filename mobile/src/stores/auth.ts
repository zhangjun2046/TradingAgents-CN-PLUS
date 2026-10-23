import { defineStore } from "pinia";
import { login as loginApi, type LoginUser } from "@/api/auth";
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
    async login(username: string, password: string) {
      const data = await loginApi(username, password);
      tokenStorage.setTokens(data.access_token, data.refresh_token);
      tokenStorage.setUserInfo(data.user);
      this.token = data.access_token;
      this.user = data.user;
      return data;
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
