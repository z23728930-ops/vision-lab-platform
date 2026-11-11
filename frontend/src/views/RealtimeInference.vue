<!-- src/views/RealtimeInference.vue -->
<template>
  <div>
    <el-row :gutter="20">
      <!-- 左侧控制面板 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>在线推理控制</span>
            </div>
          </template>
          <el-form label-position="top">
            <el-form-item label="选择模型">
              <el-select v-model="selectedModelId" placeholder="请选择一个 YOLO 模型" style="width: 100%;" :disabled="isStreaming">
                <el-option
                    v-for="model in yoloModels"
                    :key="model.id"
                    :label="`${model.name} (ID: ${model.id})`"
                    :value="model.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="推理参数 (JSON)">
              <el-input
                  v-model="inferenceParamsJson"
                  type="textarea"
                  :rows="4"
                  placeholder='例如: {"image_size": 640, "conf_threshold": 0.25, "iou_threshold": 0.7}'
                  :disabled="isStreaming"
              ></el-input>
            </el-form-item>
            <el-form-item>
              <el-button
                  :type="isStreaming ? 'danger' : 'primary'"
                  @click="toggleStream"
                  :loading="isConnectingStream"
                  :disabled="!selectedModelId || !cameraStore.isConnected"
                  style="width: 100%;"
              >
                {{ isStreaming ? '停止在线推理' : '开始在线推理' }}
              </el-button>
            </el-form-item>
            <el-alert v-if="!cameraStore.isConnected" title="相机未连接" type="warning" show-icon :closable="false" style="margin-top: 10px;">
              请前往 "硬件控制" 页面连接相机。
            </el-alert>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧视频流显示 -->
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>实时推理视频流</span>
            </div>
          </template>
          <div class="video-container">
            <img v-if="videoStreamUrl" :src="videoStreamUrl" alt="实时推理视频流" class="video-stream-img"/>
            <div v-else class="video-placeholder">
              <el-icon :size="50" color="#c0c4cc"><VideoCamera /></el-icon>
              <p v-if="!cameraStore.isConnected">相机未连接</p>
              <p v-else-if="!selectedModelId">请选择模型并点击“开始在线推理”</p>
              <p v-else>等待视频流...</p>
            </div>
            <div v-if="isStreaming && streamError" class="stream-error-overlay">
              <el-alert title="视频流错误" :description="streamError" type="error" show-icon :closable="false" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { VideoCamera } from '@element-plus/icons-vue';
import { fetchModels } from '../api/models';
import { getCameraStreamUrl } from '../api/hardware';
import { useCameraStore } from '../store/camera';

// 获取 Camera Store 实例
const cameraStore = useCameraStore();

// 状态
const models = ref([]);
const yoloModels = computed(() => models.value.filter(m => m.model_type === 'yolo'));
const selectedModelId = ref(null);
const inferenceParamsJson = ref('{\n  "image_size": 640,\n  "conf_threshold": 0.25,\n  "iou_threshold": 0.7\n}');

const isStreaming = ref(false);
const isConnectingStream = ref(false);
const videoStreamUrl = ref(null);
let websocket = null;

const streamError = ref(null);

// --- 新增标志位 ---
const isUserInitiatedClose = ref(false);

// 方法
const getModels = async () => {
  try {
    const response = await fetchModels();
    models.value = response.data;
  } catch (error) {
    ElMessage.error('获取模型列表失败！');
    console.error('Failed to fetch models:', error);
  }
};

const startStream = () => {
  if (!selectedModelId.value) {
    ElMessage.warning('请先选择一个模型！');
    return;
  }
  if (!cameraStore.isConnected) {
    ElMessage.warning('相机未连接，无法开始实时推理！请前往 "硬件控制" 页面连接相机。');
    return;
  }

  isConnectingStream.value = true;
  streamError.value = null; // 清空之前的错误

  let parsedParams = {};
  try {
    parsedParams = JSON.parse(inferenceParamsJson.value);
  } catch (e) {
    ElMessage.error('推理参数不是有效的JSON格式！');
    isConnectingStream.value = false;
    return;
  }

  const wsUrl = getCameraStreamUrl(selectedModelId.value, parsedParams);
  websocket = new WebSocket(wsUrl);

  websocket.onopen = () => {
    console.log('WebSocket for real-time inference connected');
    isConnectingStream.value = false;
    isStreaming.value = true;
    isUserInitiatedClose.value = false; // 确保连接成功后重置标志
    ElMessage.success('实时推理视频流已启动！');
  };

  websocket.onmessage = (event) => {
    if (event.data instanceof Blob) {
      if (videoStreamUrl.value) {
        URL.revokeObjectURL(videoStreamUrl.value);
      }
      videoStreamUrl.value = URL.createObjectURL(event.data);
    } else if (typeof event.data === 'string') {
      try {
        const message = JSON.parse(event.data);
        if (message.error) {
          streamError.value = message.error;
          ElMessage.error(`视频流错误: ${message.error}`);
          stopStream(); // 收到错误后停止流
        }
      } catch (e) {
        console.warn("Received non-JSON string message:", event.data);
      }
    }
  };

  websocket.onclose = (event) => {
    console.log('WebSocket for real-time inference disconnected', event.code, event.reason);
    isStreaming.value = false;
    isConnectingStream.value = false;
    if (videoStreamUrl.value) {
      URL.revokeObjectURL(videoStreamUrl.value);
      videoStreamUrl.value = null;
    }

    // --- 关键修改：根据标志位判断是否显示错误或正常关闭提示 ---
    if (isUserInitiatedClose.value) {
      // 用户主动关闭，显示正常关闭提示
      ElMessage.info('实时推理视频流已停止。');
      streamError.value = null; // 清除任何错误状态
    } else if (event.code !== 1000) {
      // 非用户主动关闭，且不是正常关闭码 (1000)，则显示错误
      streamError.value = `视频流已断开: ${event.reason || '未知错误'} (Code: ${event.code})`;
      ElMessage.error(streamError.value);
    } else {
      // 正常关闭码 (1000)，但不是用户主动关闭（例如，后端主动断开），不显示错误，也不显示“已停止”提示
      streamError.value = null;
    }
    isUserInitiatedClose.value = false; // 无论如何，在处理完关闭事件后重置标志
  };

  websocket.onerror = (error) => {
    console.error('WebSocket for real-time inference error:', error);
    streamError.value = '连接错误，请检查相机状态或后端日志。';
    ElMessage.error('实时推理视频流连接失败！');
    // 当发生错误时，调用 stopStream，这会设置 isUserInitiatedClose 为 true，
    // 从而在 onclose 中避免再次显示错误。
    stopStream();
  };
};

const stopStream = () => {
  if (websocket) {
    isUserInitiatedClose.value = true; // 在关闭前设置标志
    websocket.close();
    websocket = null;
  }
  isStreaming.value = false;
  isConnectingStream.value = false;
  if (videoStreamUrl.value) {
    URL.revokeObjectURL(videoStreamUrl.value);
    videoStreamUrl.value = null;
  }
  // 注意：这里不再直接显示“已停止”的提示，因为我们将其移到了 onclose 中，
  // 这样可以确保在 WebSocket 真正关闭后才提示，避免时序问题。
};

const toggleStream = () => {
  if (isStreaming.value) {
    stopStream();
  } else {
    startStream();
  }
};

// 生命周期钩子
onMounted(async () => {
  await getModels();
});

onUnmounted(() => {
  stopStream();
});
</script>

<style scoped>
.card-header {
  font-size: 16px;
  font-weight: 500;
}

.video-container {
  width: 100%;
  aspect-ratio: 16 / 9; /* 保持视频比例 */
  background-color: #000;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative; /* 用于错误信息叠加 */
}

.video-stream-img {
  width: 100%;
  height: 100%;
  object-fit: contain; /* 确保图片完整显示在容器内 */
}

.video-placeholder {
  text-align: center;
  color: #c0c4cc;
}

.stream-error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(255, 0, 0, 0.2); /* 半透明红色背景 */
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  box-sizing: border-box;
}
</style>