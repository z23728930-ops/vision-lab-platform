// defect-detection-frontend/src/api/inference.js

import apiClient from './index';

// 获取所有推理任务列表
export const fetchInferenceJobs = () => {
    return apiClient.get('/inference/jobs');
};

export const fetchAllInferenceJobsForAdmin = () => {
    return apiClient.get('/inference/admin/jobs');
};

// 获取单个推理任务的状态
export const fetchInferenceJob = (jobId) => {
    return apiClient.get(`/inference/jobs/${jobId}`);
};

// 创建推理任务
export const createInferenceJob = (data) => {
    return apiClient.post('/inference/jobs', data);
};

// 删除推理任务（包括结果文件）
export const deleteInferenceJob = (jobId) => {
    return apiClient.delete(`/inference/jobs/${jobId}`);
};

// 浏览推理结果
export const browseInferenceResult = (jobId) => {
    return apiClient.get(`/inference/jobs/${jobId}/browse`);
};

// --- 新增：下载推理任务结果 ---
export const downloadInferenceResultBlob = async (jobId) => {
    const response = await apiClient.get(`/inference/jobs/${jobId}/download`, {
        responseType: 'blob', // 关键！以二进制流形式接收
    });
    return response.data;
};
