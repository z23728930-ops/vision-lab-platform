// src/store/camera.js
import { defineStore } from 'pinia';
import {
    connectCamera as apiConnect,
    disconnectCamera as apiDisconnect,
    fetchCameraParams as apiFetchParams,
    fetchCameraStatus // <-- 新增导入
} from '../api/hardware';

export const useCameraStore = defineStore('camera', {
    state: () => ({
        isConnected: false,
        isConnecting: false,
        cameraId: -1,
        cameraParams: [],
    }),
    actions: {
        async connectCamera(id = 0) {
            if (this.isConnected && this.cameraId === id) {
                console.log("Camera already connected with ID:", id);
                return true;
            }
            if (this.isConnecting) {
                console.log("Camera connection already in progress.");
                return false;
            }

            this.isConnecting = true;
            try {
                if (this.isConnected) {
                    await this.disconnectCamera();
                }
                await apiConnect(id);
                this.isConnected = true;
                this.cameraId = id;
                await this.fetchCameraParams();
                console.log(`Camera connected successfully with ID: ${id}`);
                return true;
            } catch (error) {
                console.error(`Failed to connect camera ${id}:`, error);
                this.isConnected = false;
                this.cameraId = -1;
                this.cameraParams = [];
                throw error;
            } finally {
                this.isConnecting = false;
            }
        },

        async disconnectCamera() {
            if (!this.isConnected) {
                console.log("Camera is already disconnected.");
                return;
            }
            try {
                await apiDisconnect();
                this.isConnected = false;
                this.cameraId = -1;
                this.cameraParams = [];
                console.log("Camera disconnected successfully.");
            } catch (error) {
                console.error("Failed to disconnect camera:", error);
                throw error;
            }
        },

        async fetchCameraParams() {
            if (!this.isConnected) {
                this.cameraParams = [];
                return;
            }
            try {
                const response = await apiFetchParams();
                this.cameraParams = response.data;
            } catch (error) {
                console.error("Failed to fetch camera parameters:", error);
                this.cameraParams = [];
                throw error;
            }
        },

        // --- 新增：检查初始相机状态的Action ---
        async checkInitialStatus() {
            try {
                const response = await fetchCameraStatus();
                this.isConnected = response.data.is_connected;
                this.cameraId = response.data.camera_id;
                console.log(`[CameraStore] Initial camera status checked: Connected = ${this.isConnected}, ID = ${this.cameraId}`);
                // 如果相机是连接状态，尝试获取参数，更新UI
                if (this.isConnected) {
                    await this.fetchCameraParams();
                }
            } catch (error) {
                console.error("[CameraStore] Failed to fetch initial camera status:", error);
                this.isConnected = false;
                this.cameraId = -1;
                this.cameraParams = [];
            }
        }
        // -----------------------------------
    },
});