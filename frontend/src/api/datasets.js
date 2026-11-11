// src/api/datasets.js
import apiClient, { apiBaseURL } from './index';

// 获取数据集列表
export const fetchDatasets = (params) => {
    return apiClient.get('/datasets/', { params });
};

// 上传数据集 (ZIP 文件)
export const uploadDataset = (formData) => {
    return apiClient.post('/datasets/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
};

// 新增：上传数据集 (文件夹)
export const uploadDatasetFolder = (formData) => {
    return apiClient.post('/datasets/upload_folder', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
};


// 删除数据集
export const deleteDataset = (datasetId) => {
    return apiClient.delete(`/datasets/${datasetId}`);
};

export const getDatasetDownloadUrl = (datasetId) => {
    const token = localStorage.getItem('token');
    return `${apiClient.defaults.baseURL}/datasets/${datasetId}/download?token=${token}`;
};

export const downloadDatasetBlob = async (datasetId) => {
    const response = await apiClient.get(`/datasets/${datasetId}/download`, {
        responseType: 'blob',
    });
    return response.data;
}

// 更新数据集的公开状态
export const updateDatasetPublicStatus = (datasetId, isPublic) => {
    return apiClient.patch(`/datasets/${datasetId}/public`, { is_public: isPublic });
};

// 获取数据集内容以供浏览 (现在将返回所有文件类型)
export const browseDataset = (datasetId) => {
    return apiClient.get(`/datasets/${datasetId}/browse_contents`); // <-- 修改为新的浏览路由
};

// 获取指定数据集的图片列表 (仅图片，用于标注工具)
export const fetchImagesByDataset = (datasetId) => {
    return apiClient.get(`/datasets/${datasetId}/images`);
};

export const fetchDatasetSplit = (datasetId) => apiClient.get(`/datasets/${datasetId}/split`);
export const splitDataset = (datasetId, payload) => apiClient.post(`/datasets/${datasetId}/split`, payload);
export const fetchAnnotationStatus = (datasetId) => apiClient.get(`/datasets/${datasetId}/annotation-status`);
export const markImageReviewed = (datasetId, imageId, reviewed = true) => apiClient.post(`/datasets/${datasetId}/images/${imageId}/review`, { reviewed });
export const cloneDataset = (datasetId, name) => apiClient.post(`/datasets/${datasetId}/clone`, { name });
export const checkDatasetReadiness = (datasetId) => apiClient.get(`/datasets/${datasetId}/readiness-check`);
export const exportTrainingPackage = async (datasetId) => {
    const response = await apiClient.post(`/datasets/${datasetId}/export-training-package`, {}, { responseType: 'blob' });
    return response.data;
};
export const exportExperienceTrainingPackage = async (datasetId) => {
    const response = await apiClient.post(`/datasets/${datasetId}/export-experience-training-package`, {}, { responseType: 'blob' });
    return response.data;
};

// 导出标注数据
export const exportAnnotations = async (datasetId, format, includeImages) => { // <-- 接收 includeImages 参数
    const response = await apiClient.post(`/datasets/${datasetId}/export_annotations`, {
        format: format,
        include_images: includeImages // <-- 传递 include_images 参数
    }, {
        responseType: 'blob',
    });
    return response.data;
};

// 新增：获取文件内容 (用于文本文件预览)
export const fetchFileContent = async (filePath) => {
    // 相对地址会交给 Vite 代理转发；生产环境可通过 VITE_API_BASE_URL 使用完整后端地址。
    const baseUrl = apiBaseURL.replace(/\/api\/v1\/?$/, '');
    const fullStaticUrl = `${baseUrl}${filePath}`;

    const response = await fetch(fullStaticUrl, { // 直接使用 fetch API，因为这是静态文件服务，不需要认证头
        method: 'GET',
        headers: {
            // 如果静态文件服务需要认证，这里需要添加 Authorization 头
            // 'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.text(); // 以文本形式返回
};
