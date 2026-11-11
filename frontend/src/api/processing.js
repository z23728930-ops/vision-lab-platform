import apiClient from './index';

// 创建预处理任务
export const createProcessingJob = (data) => {
    return apiClient.post('/processing/jobs', data);
};

// 单图预览：只返回处理后的图片，不创建数据集
export const previewProcessingImage = (file, steps) => {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('steps', JSON.stringify(steps));
    return apiClient.post('/processing/preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
    });
};

// 查询预处理任务状态
export const fetchProcessingJobStatus = (jobId) => {
    return apiClient.get(`/processing/jobs/${jobId}`);
};
