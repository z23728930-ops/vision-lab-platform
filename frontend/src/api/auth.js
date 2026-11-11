import apiClient from './index';

// 删除下面这一行，我们不再需要它了
// import { URLSearchParams } from 'url';

export const login = (username, password) => {
    // 直接使用浏览器内置的 URLSearchParams 对象
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    return apiClient.post('/auth/token', params, {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    });
};

export const register = (payload) => {
    return apiClient.post('/auth/register', payload);
};

export const fetchCurrentUser = () => {
    return apiClient.get('/users/me');
}
