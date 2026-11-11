import apiClient from './index';

export const fetchUsers = () => {
    return apiClient.get('/users/');
};

export const createUser = (userData) => {
    return apiClient.post('/users/', userData);
};

export const deleteUser = (userId) => {
    return apiClient.delete(`/users/${userId}`);
};

// 更新用户信息的API函数
export const updateCurrentUser = (userData) => {
    return apiClient.put('/users/me', userData);
};

export const updateUserById = (userId, userData) => {
    return apiClient.put(`/users/${userId}`, userData);
};
