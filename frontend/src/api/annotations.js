// src/api/annotations.js
import apiClient from './index';

// 获取指定图片的所有标注
export const fetchAnnotationsByImage = (imageId) => {
    return apiClient.get(`/annotations/images/${imageId}/annotations`);
};

// 创建单个标注
export const createAnnotation = (annotationData) => {
    return apiClient.post('/annotations/', annotationData);
};

// 批量创建标注
export const createBatchAnnotations = (annotationsList) => {
    return apiClient.post('/annotations/batch', { annotations: annotationsList });
};

// 更新单个标注
export const updateAnnotation = (annotationId, annotationData) => {
    return apiClient.put(`/annotations/${annotationId}`, annotationData);
};

// 批量更新标注 (如果后端支持，目前后端只支持单条PUT)
// export const updateBatchAnnotations = (annotationsList) => {
//     return apiClient.put('/annotations/batch', { annotations: annotationsList });
// };

// 删除单个标注
export const deleteAnnotation = (annotationId) => {
    return apiClient.delete(`/annotations/${annotationId}`);
};

// 批量删除标注
export const deleteBatchAnnotations = (annotationIds) => {
    return apiClient.post('/annotations/delete-batch', annotationIds); // 注意：FastAPI 接收 List[int] 作为请求体
};