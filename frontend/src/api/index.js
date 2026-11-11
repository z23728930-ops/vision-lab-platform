import axios from 'axios';
import { useUserStore } from '../store/user';

const apiBaseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const apiClient = axios.create({
    baseURL: apiBaseURL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// 请求拦截器：在每个请求发送前，自动附上Token
apiClient.interceptors.request.use(
    (config) => {
        // Pinia store 必须在拦截器函数内部获取，以避免初始化顺序问题
        const userStore = useUserStore();
        const token = userStore.token;
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export default apiClient;
export { apiBaseURL };