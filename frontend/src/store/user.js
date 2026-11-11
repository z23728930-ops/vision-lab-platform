// src/store/user.js
import { defineStore } from 'pinia';
import { login as apiLogin, fetchCurrentUser } from '../api/auth';
import { updateCurrentUser } from '../api/users'; // <-- 新增导入
import router from '../router';
import { ElMessage } from 'element-plus'; // <-- 新增导入 ElMessage

export const useUserStore = defineStore('user', {
    state: () => ({
        token: localStorage.getItem('token') || null,
        userInfo: null,
    }),
    getters: {
        isLoggedIn: (state) => !!state.token,
        isAdmin: (state) => state.userInfo?.role === 'admin',
    },
    actions: {
        async login(username, password) {
            try {
                const response = await apiLogin(username, password);
                const token = response.data.access_token;
                this.token = token;
                localStorage.setItem('token', token);

                await this.getUserInfo(); // 登录成功后获取用户信息

                await router.push('/dashboard');
                return true;
            } catch (error) {
                console.error('Login failed:', error);
                // 可以在这里处理登录失败的提示
                throw error; // 重新抛出错误，让调用者（Login.vue）处理
            }
        },
        async getUserInfo() {
            if (this.isLoggedIn) {
                try {
                    const response = await fetchCurrentUser();
                    this.userInfo = response.data;
                } catch (error) {
                    console.error("Failed to fetch user info:", error);
                    // 如果获取用户信息失败，并且不是登录页，则强制登出
                    if (router.currentRoute.value.name !== 'Login') {
                        ElMessage.error("会话已过期，请重新登录。");
                        this.logout();
                    }
                    throw error; // 抛出错误，以便路由守卫可以捕获
                }
            }
        },
        // --- 新增：更新当前用户信息 action ---
        async updateUserInfo(userData) {
            try {
                const response = await updateCurrentUser(userData);
                this.userInfo = response.data; // 更新 store 中的用户信息
                ElMessage.success('个人信息更新成功！');
                return true;
            } catch (error) {
                console.error("Failed to update user info:", error);
                ElMessage.error(error.response?.data?.detail || '更新失败');
                throw error; // 抛出错误以便组件处理
            }
        },
        // ------------------------------------
        logout() {
            this.token = null;
            this.userInfo = null;
            localStorage.removeItem('token');
            router.push('/login');
        },
    },
});