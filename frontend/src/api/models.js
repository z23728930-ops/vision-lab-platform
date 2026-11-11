import apiClient from './index';

export const fetchModels = (params) => {
    return apiClient.get('/models/', { params });
};

export const uploadModel = (formData) => {
    return apiClient.post('/models/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
};

export const deleteModel = (modelId) => {
    return apiClient.delete(`/models/${modelId}`);
};