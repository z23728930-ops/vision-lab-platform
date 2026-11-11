import apiClient from './index';

export const sendAssistantMessage = (message) => apiClient.post('/assistant/chat', { message });
export const fetchAssistantJobStatus = (jobId) => apiClient.get(`/inference/jobs/${jobId}`);
export const fetchAssistantJobStats = (jobId) => apiClient.get(`/inference/jobs/${jobId}/stats`);
export const downloadAssistantReport = async (jobId) => (await apiClient.get(`/inference/jobs/${jobId}/report.csv`, { responseType: 'blob' })).data;
export const fetchAssistantReportJson = (jobId) => apiClient.get(`/inference/jobs/${jobId}/report.json`);
export const browseAssistantResult = (jobId) => apiClient.get(`/inference/jobs/${jobId}/browse`);
export const downloadAssistantResult = async (jobId) => (await apiClient.get(`/inference/jobs/${jobId}/download`, { responseType: 'blob' })).data;
