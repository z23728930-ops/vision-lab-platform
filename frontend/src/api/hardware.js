//src/api/hardware.js
import apiClient, { apiBaseURL } from './index';

// MODIFIED: connectCamera now accepts cameraSource and sends it in the request body
export const connectCamera = (cameraSource) => {
    // 后端期望在请求体中接收 camera_source
    return apiClient.post('/hardware/camera/connect', { camera_source: cameraSource });
};

export const getCameraStreamUrl = (modelId = null, inferenceParams = null) => {
    const absoluteApiBaseURL = apiBaseURL.startsWith('http')
        ? apiBaseURL
        : `${window.location.origin}${apiBaseURL}`;
    let url = `${absoluteApiBaseURL}/hardware/camera/stream`;
    const params = new URLSearchParams();
    if (modelId !== null) {
        params.append('model_id', modelId);
    }
    if (inferenceParams !== null) {
        params.append('inference_params', JSON.stringify(inferenceParams)); // 将对象转换为JSON字符串
    }
    if (params.toString()) {
        url += `?${params.toString()}`;
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return url.replace(/^https?:/, protocol);
};


export const disconnectCamera = () => {
    return apiClient.post('/hardware/camera/disconnect');
};
export const fetchCameraStatus = () => {
    return apiClient.get('/hardware/camera/status');
};

export const fetchCameraParams = () => {
    return apiClient.get('/hardware/camera/parameters');
};

export const updateCameraParams = (params) => {
    return apiClient.put('/hardware/camera/parameters', { parameters: params });
};

// --- 以下是本步骤新增的函数 ---

// 获取所有参数配置文件的列表
export const fetchCameraProfiles = () => {
    return apiClient.get('/hardware/camera/profiles');
};

// 保存当前参数为指定名称的配置文件
export const saveCameraProfile = (profileName) => {
    return apiClient.post(`/hardware/camera/profiles/${profileName}/save`);
};

// 加载指定名称的配置文件并应用到相机
export const loadCameraProfile = (profileName) => {
    return apiClient.post(`/hardware/camera/profiles/${profileName}/load`);
};

// 开始连续采集
export const startAcquisition = (datasetName) => {
    // 使用 URLSearchParams 来确保正确编码，而不是手动拼接字符串
    const params = new URLSearchParams();
    params.append('dataset_name', datasetName);
    return apiClient.post(`/hardware/acquisition/start?${params.toString()}`);
};

export const stopAcquisition = () => {
    return apiClient.post('/hardware/acquisition/stop');
};

//单帧采集
export const captureSingleFrame = (datasetId) => {
    // datasetId 应该是一个数字，它在URL路径中会被自动处理
    return apiClient.post(`/hardware/acquisition/capture-single/${datasetId}`);
};

export const uploadBrowserCapture = (datasetId, blob) => {
    const formData = new FormData();
    formData.append('file', blob, 'browser-capture.jpg');
    return apiClient.post(`/hardware/browser-capture/${datasetId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
};

export const startCalibration = () => apiClient.post('/hardware/calibration/start');
export const captureCalibrationFrame = () => apiClient.post('/hardware/calibration/capture');
export const runCalibration = (params) => apiClient.post('/hardware/calibration/run', null, { params });
export const cancelCalibration = () => apiClient.post('/hardware/calibration/cancel');
