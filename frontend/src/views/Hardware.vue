<template>
  <div>
    <el-row :gutter="20">
      <!-- 左侧视频流区域 -->
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>实时视频流</span>
              <!-- 新增：单帧采集和连续采集控制 -->
              <div class="header-actions">
                <el-popover placement="top" :width="250" trigger="hover" content="将当前帧保存到指定的数据集">
                  <template #reference>
                    <el-button :icon="Picture" @click="handleSingleCapture" :disabled="!isCameraConnected">单帧采集</el-button>
                  </template>
                </el-popover>
                <el-button v-if="cameraMode === 'device'" :type="isCollecting ? 'warning' : 'success'" :icon="isCollecting ? VideoPause : VideoPlay" @click="toggleContinuousCapture" :disabled="!isCameraConnected">
                  {{ isCollecting ? '停止采集' : '连续采集' }}
                </el-button>
              </div>
            </div>
          </template>
          <div class="video-container">
            <video v-if="cameraMode === 'browser' && browserConnected" ref="browserVideoRef" autoplay muted playsinline class="video-stream-img"></video>
            <img v-else-if="videoStreamUrl" :src="videoStreamUrl" alt="Video Stream" class="video-stream-img"/>
            <div v-else class="video-placeholder">
              <el-icon :size="50" color="#c0c4cc"><VideoCamera /></el-icon>
              <p>相机未连接</p>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧控制区域 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>相机控制</span>
            </div>
          </template>
          <div class="control-panel">
            <el-alert
              v-if="cameraMode === 'browser' && !secureCameraAvailable"
              title="浏览器相机需要 HTTPS"
              description="当前公网 HTTP 页面无法申请摄像头权限，请使用 HTTPS 域名访问；localhost 测试不受影响。"
              type="warning"
              :closable="false"
              show-icon
              style="margin-bottom: 14px"
            />
            <el-form-item label="接入方式">
              <el-radio-group v-model="cameraMode" @change="handleCameraModeChange">
                <el-radio-button label="browser">本机浏览器相机</el-radio-button>
                <el-radio-button label="device">服务器/工业相机</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <!-- ADDED: Input for camera source -->
            <el-form-item v-if="cameraMode === 'device'" label="相机源" style="margin-bottom: 10px;">
              <el-input v-model="cameraSourceInput" placeholder="输入相机ID (0, 1...) 或 IP摄像头URL (http://...)" clearable />
            </el-form-item>

            <el-button
                :type="isCameraConnected ? 'danger' : 'primary'"
                @click="toggleConnection"
                :loading="cameraMode === 'browser' ? browserConnecting : cameraStore.isConnecting"
                :disabled="cameraMode === 'browser' && !secureCameraAvailable"
                style="width: 100%;"
            >
              {{ isCameraConnected ? '断开连接' : '连接相机' }}
            </el-button>

            <!-- 新增：相机标定按钮 -->
            <el-button v-if="cameraMode === 'device'" @click="openCalibrationDrawer" :disabled="!cameraStore.isConnected" style="width: 100%; margin-top: 20px; margin-bottom: 20px;">
              相机标定
            </el-button>

            <template v-if="cameraMode === 'device'">
            <el-divider>参数配置</el-divider>

            <!-- 新增：参数配置加载与保存 -->
            <el-form-item label="配置方案">
              <div class="profile-actions">
                <el-select v-model="selectedProfile" placeholder="加载配置" style="flex-grow: 1; margin-right: 10px;" @change="handleLoadProfile" :disabled="!cameraStore.isConnected">
                  <el-option v-for="profile in profiles" :key="profile" :label="profile" :value="profile" />
                </el-select>
                <el-button :icon="FolderAdd" @click="handleSaveProfile" :disabled="!cameraStore.isConnected">保存</el-button>
              </div>
            </el-form-item>

            <el-form label-width="80px" v-if="cameraStore.isConnected && cameraStore.cameraParams.length">
              <el-form-item
                  v-for="param in cameraStore.cameraParams"
                  :key="param.key"
                  :label="param.name"
              >
                <el-slider
                    v-model="param.value"
                    :min="param.min_value"
                    :max="param.max_value"
                    :step="param.step"
                    show-input
                    :show-input-controls="false"
                    size="small"
                    @change="debouncedUpdateParam(param)"
                />
              </el-form-item>
            </el-form>
            <el-empty v-else-if="cameraStore.isConnected" description="暂无参数可设置"></el-empty>
            <el-empty v-else description="请先连接相机"></el-empty>
            </template>
            <div v-else class="browser-camera-tip">
              摄像头画面仅在当前浏览器中处理；只有点击“单帧采集”后，当前画面才会上传到所选数据集。
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ... 单帧采集对话框和相机标定抽屉保持不变 ... -->
    <el-dialog v-model="singleCaptureDialogVisible" title="单帧采集" width="400px">
      <el-form :model="singleCaptureForm" ref="singleCaptureFormRef" label-width="100px">
        <el-form-item label="选择数据集" prop="datasetId" :rules="[{ required: true, message: '请选择一个数据集', trigger: 'change' }]">
          <el-select v-model="singleCaptureForm.datasetId" placeholder="请选择要存入的数据集" style="width: 100%;">
            <el-option
                v-for="ds in datasets"
                :key="ds.id"
                :label="`${ds.name} (ID: ${ds.id})`"
                :value="ds.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="singleCaptureDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSingleCapture">确认采集</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="calibrationDrawerVisible" title="相机标定向导" direction="rtl" size="50%" @closed="cancelCalibrationProcess">
      <el-steps :active="calibrationStep" finish-status="success" simple style="margin-bottom: 20px">
        <el-step title="捕捉图像" />
        <el-step title="计算参数" />
        <el-step title="查看结果" />
      </el-steps>

      <div v-if="calibrationStep === 0">
        <el-alert title="操作提示" type="info" show-icon :closable="false">
          请将棋盘格标定板放置在摄像头视野内，从不同角度和距离捕捉10-20张清晰的图像。
        </el-alert>
        <div class="calibration-capture">
          <p>已捕捉图像: <strong>{{ capturedFramesCount }}</strong> / 15 (推荐)</p>
          <el-button type="primary" @click="handleCaptureFrame" :loading="isCapturingFrame">捕捉当前帧</el-button>
        </div>
      </div>

      <div v-if="calibrationStep === 1">
        <el-form :model="calibrationForm" label-width="150px">
          <el-form-item label="棋盘格宽度 (内角数)">
            <el-input-number v-model="calibrationForm.pattern_width" :min="2" />
          </el-form-item>
          <el-form-item label="棋盘格高度 (内角数)">
            <el-input-number v-model="calibrationForm.pattern_height" :min="2" />
          </el-form-item>
          <el-form-item label="方格边长 (mm)">
            <el-input-number v-model="calibrationForm.square_size_mm" :min="0.1" :step="0.1" />
          </el-form-item>
        </el-form>
      </div>

      <div v-if="calibrationStep === 2">
        <el-descriptions title="标定结果" :column="1" border>
          <el-descriptions-item label="相机内参矩阵 (Fx, Fy, Cx, Cy)">
            <pre>{{ calibrationResult?.camera_matrix }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="畸变系数 (k1,k2,p1,p2,k3)">
            <pre>{{ calibrationResult?.distortion_coefficients }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="均方根重投影误差 (RMSE)">
            <el-tag type="success">{{ calibrationResult?.rmse?.toFixed(4) }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="drawer-footer">
        <el-button @click="cancelCalibrationProcess">取消</el-button>
        <el-button @click="calibrationStep--" v-if="calibrationStep > 0 && calibrationStep < 2">上一步</el-button>
        <el-button type="primary" @click="calibrationStep++" v-if="calibrationStep < 1" :disabled="capturedFramesCount < 5">下一步</el-button>
        <el-button type="primary" @click="handleRunCalibration" v-if="calibrationStep === 1" :loading="isCalibrating">开始计算</el-button>
        <el-button type="success" @click="calibrationDrawerVisible = false" v-if="calibrationStep === 2">完成</el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onUnmounted, onMounted, reactive, computed, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { VideoCamera, Picture, VideoPlay, VideoPause, FolderAdd } from '@element-plus/icons-vue';
import {
  fetchCameraProfiles,
  saveCameraProfile,
  loadCameraProfile,
  startAcquisition,
  stopAcquisition,
  captureSingleFrame,
  uploadBrowserCapture,
  startCalibration,
  captureCalibrationFrame,
  runCalibration,
  cancelCalibration,
  updateCameraParams as apiUpdateParams // Alias to avoid name conflict with store action
} from '../api/hardware';
import { fetchDatasets } from '../api/datasets';
import emitter from '../utils/eventBus';
import { useCameraStore } from '../store/camera'; // <-- 导入 Camera Store

// 获取 Camera Store 实例
const cameraStore = useCameraStore();

// --- 辅助函数 ---
function debounce(fn, delay) {
  let timeoutId = null;
  return function(...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

// --- 状态定义 ---
// isConnected 和 isConnecting 现在从 cameraStore 中获取
const videoStreamUrl = ref(null);
const browserVideoRef = ref(null);
const browserConnected = ref(false);
const browserConnecting = ref(false);
const cameraMode = ref('browser');
const secureCameraAvailable = computed(() => window.isSecureContext && !!navigator.mediaDevices?.getUserMedia);
const isCameraConnected = computed(() => cameraMode.value === 'browser' ? browserConnected.value : cameraStore.isConnected);
let browserStream = null;
let websocket = null;
const profiles = ref([]);
const selectedProfile = ref('');
const datasets = ref([]);
const isCollecting = ref(false);

// ADDED: Ref for camera source input
const cameraSourceInput = ref('0'); // Default to 0 for convenience (first local camera)

// 单帧采集对话框状态
const singleCaptureDialogVisible = ref(false);
const singleCaptureFormRef = ref(null);
const singleCaptureForm = reactive({
  datasetId: null,
});

// 标定相关状态
const calibrationDrawerVisible = ref(false);
const calibrationStep = ref(0);
const capturedFramesCount = ref(0);
const isCapturingFrame = ref(false);
const isCalibrating = ref(false);
const calibrationForm = reactive({
  pattern_width: 9,
  pattern_height: 6,
  square_size_mm: 25.0,
});
const calibrationResult = ref(null);


// --- API 调用逻辑 ---
const getProfiles = async () => {
  try {
    const response = await fetchCameraProfiles();
    profiles.value = response.data;
  } catch (error) {
    console.error("获取配置列表失败", error);
    profiles.value = [];
  }
}

const getDatasets = async () => {
  try {
    const response = await fetchDatasets();
    datasets.value = response.data;
  } catch(error) {
    console.error("获取数据集列表失败", error)
    datasets.value = [];
    ElMessage.error("获取数据集列表失败！");
  }
}

const toggleConnection = async () => {
  if (cameraMode.value === 'browser') {
    if (browserConnected.value) {
      stopBrowserCamera();
      ElMessage.info('浏览器相机已断开。');
    } else {
      await startBrowserCamera();
    }
    return;
  }
  if (cameraStore.isConnected) {
    await cameraStore.disconnectCamera();
    ElMessage.info('相机已断开。');
    stopWebSocket();
  } else {
    // MODIFIED: Use cameraSourceInput for connection
    const source = cameraSourceInput.value;
    if (!source) {
      ElMessage.warning('请输入相机ID或IP摄像头URL。');
      return;
    }

    // 尝试将输入解析为数字，如果失败则保持为字符串
    let parsedSource = source;
    if (!isNaN(source) && !isNaN(parseFloat(source))) {
      parsedSource = parseInt(source, 10);
    }

    try {
      // Pass the parsed source (number or string) to the store action
      await cameraStore.connectCamera(parsedSource);
      ElMessage.success('相机连接成功！');
      await getProfiles(); // 连接成功后刷新配置文件列表
      startWebSocket(); // 连接成功后启动视频流
    } catch (error) {
      console.error("相机连接失败:", error);
      // 检查错误响应中是否有详细信息
      ElMessage.error(error.response?.data?.detail || '相机连接失败！请检查相机源或网络。');
    }
  }
};

const startBrowserCamera = async () => {
  if (!secureCameraAvailable.value) {
    ElMessage.error('浏览器安全策略要求使用 HTTPS 才能访问摄像头。');
    return;
  }
  browserConnecting.value = true;
  try {
    browserStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' },
      audio: false,
    });
    browserConnected.value = true;
    await nextTick();
    browserVideoRef.value.srcObject = browserStream;
    await browserVideoRef.value.play();
    ElMessage.success('已连接当前设备摄像头');
  } catch (error) {
    browserConnected.value = false;
    const message = error?.name === 'NotAllowedError'
      ? '摄像头权限被拒绝，请在浏览器地址栏中允许摄像头权限。'
      : '无法打开摄像头，请确认设备未被其他程序占用。';
    ElMessage.error(message);
  } finally {
    browserConnecting.value = false;
  }
};

const stopBrowserCamera = () => {
  browserStream?.getTracks().forEach((track) => track.stop());
  browserStream = null;
  if (browserVideoRef.value) browserVideoRef.value.srcObject = null;
  browserConnected.value = false;
};

const handleCameraModeChange = () => {
  stopBrowserCamera();
  stopWebSocket();
};

const captureBrowserFrame = async (datasetId) => {
  const video = browserVideoRef.value;
  if (!video || video.readyState < 2 || !video.videoWidth || !video.videoHeight) {
    throw new Error('摄像头画面尚未准备好');
  }
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9));
  if (!blob) throw new Error('无法生成抓拍图片');
  return uploadBrowserCapture(datasetId, blob);
};

const handleSaveProfile = () => {
  ElMessageBox.prompt('请输入配置名称', '保存参数配置', {
    confirmButtonText: '保存',
    cancelButtonText: '取消',
    inputPattern: /^[a-zA-Z0-9\u4e00-\u9fa5_-]+$/,
    inputErrorMessage: '名称只能包含字母、数字、中文、下划线和连字符',
  }).then(async ({ value }) => {
    try {
      await saveCameraProfile(value);
      ElMessage.success(`配置 "${value}" 保存成功!`);
      await getProfiles();
    } catch(e) {
      ElMessage.error("保存失败！");
    }
  }).catch(() => {});
}

const handleLoadProfile = async (profileName) => {
  if(!profileName) return;
  try {
    await loadCameraProfile(profileName);
    await cameraStore.fetchCameraParams(); // 加载后刷新界面上的滑块值
    ElMessage.success(`配置 "${profileName}" 加载成功!`);
  } catch (e) {
    ElMessage.error("加载配置失败!");
  }
}

const updateCameraParam = async (param) => {
  try {
    // 直接调用后端API更新参数，因为这是单个参数更新，且store中没有批量更新的action
    // 如果需要，可以把这个逻辑封装到 cameraStore 中
    await apiUpdateParams([{ key: param.key, value: param.value }]);
  } catch (error) {
    ElMessage.error(`${param.name} 设置失败!`);
  }
};

const debouncedUpdateParam = debounce(updateCameraParam, 300);

// WebSocket 逻辑 (保持不变，因为它只负责显示视频流，不涉及连接/断开相机)
const startWebSocket = () => {
  // 仅在相机已连接时才尝试启动WebSocket
  if (!cameraStore.isConnected) {
    console.warn("Camera not connected, cannot start WebSocket stream.");
    return;
  }
  // WebSocket URL 应该与后端 /hardware/camera/stream 端点匹配
  // 如果后端 /hardware/camera/stream 需要 camera_source 参数来指定流哪个摄像头，
  // 则需要在这里动态构建 URL。目前后端此路由没有该参数，所以保持固定。
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/hardware/camera/stream`;
  websocket = new WebSocket(wsUrl);

  websocket.onopen = () => console.log('WebSocket connected');
  websocket.onclose = () => {
    console.log('WebSocket disconnected');
    // 当WebSocket断开时，清理视频流URL
    if (videoStreamUrl.value) {
      URL.revokeObjectURL(videoStreamUrl.value);
      videoStreamUrl.value = null;
    }
  };
  websocket.onerror = (error) => {
    console.error('WebSocket Error:', error);
    ElMessage.error('视频流连接失败或中断。');
    stopWebSocket(); // Stop on error
  };

  websocket.onmessage = (event) => {
    if (event.data instanceof Blob) {
      if (videoStreamUrl.value) {
        URL.revokeObjectURL(videoStreamUrl.value);
      }
      videoStreamUrl.value = URL.createObjectURL(event.data);
    }
  };
};

const stopWebSocket = () => {
  if (websocket) {
    websocket.close();
    websocket = null;
  }
  if (videoStreamUrl.value) {
    URL.revokeObjectURL(videoStreamUrl.value);
    videoStreamUrl.value = null;
  }
};

// 采集相关逻辑
const handleSingleCapture = () => {
  if (!datasets.value.length) {
    ElMessage.warning("没有可用的数据集。请先在'数据管理'页面创建一个。");
    return;
  }
  singleCaptureForm.datasetId = null;
  singleCaptureDialogVisible.value = true;
};

const confirmSingleCapture = async () => {
  if (!singleCaptureFormRef.value) return;
  await singleCaptureFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (cameraMode.value === 'browser') {
          await captureBrowserFrame(singleCaptureForm.datasetId);
        } else {
          await captureSingleFrame(singleCaptureForm.datasetId);
        }
        ElMessage.success(`帧已成功采集到数据集ID: ${singleCaptureForm.datasetId} 中！`);
        singleCaptureDialogVisible.value = false;
        emitter.emit('refresh-datasets');
      } catch (e) {
        ElMessage.error(e.response?.data?.detail || "单帧采集失败！");
      }
    }
  });
};

const toggleContinuousCapture = async () => {
  if (isCollecting.value) {
    try {
      await stopAcquisition();
      ElMessage.info("已停止连续采集。");
      isCollecting.value = false;
      emitter.emit('refresh-datasets');
    } catch (e) {
      ElMessage.error("停止采集失败！");
    }
  } else {
    ElMessageBox.prompt('请输入新数据集的名称', '开始连续采集', {
      confirmButtonText: '开始',
      cancelButtonText: '取消',
      inputValidator: (value) => {
        if (!value || value.trim() === '') return '数据集名称不能为空';
        return true;
      }
    }).then(async ({ value: datasetName }) => {
      try {
        await startAcquisition(datasetName);
        ElMessage.success(`开始采集数据到新数据集 "${datasetName}"！`);
        isCollecting.value = true;
        emitter.emit('refresh-datasets');
      } catch (e) {
        ElMessage.error(e.response?.data?.detail || "启动采集失败！");
      }
    }).catch(() => {});
  }
};

// 标定相关方法
const openCalibrationDrawer = async () => {
  try {
    await startCalibration();
    calibrationDrawerVisible.value = true;
    calibrationStep.value = 0;
    capturedFramesCount.value = 0;
    calibrationResult.value = null;
  } catch(e) { ElMessage.error("启动标定模式失败！"); }
};

const handleCaptureFrame = async () => {
  isCapturingFrame.value = true;
  try {
    const response = await captureCalibrationFrame();
    const message = response.data.message;
    const count = parseInt(message.split(': ')[1]);
    capturedFramesCount.value = count;
    ElMessage.success("帧捕捉成功！");
  } catch(e) { ElMessage.error("捕捉失败！"); }
  finally { isCapturingFrame.value = false; }
};

const handleRunCalibration = async () => {
  isCalibrating.value = true;
  try {
    const response = await runCalibration(calibrationForm);
    calibrationResult.value = response.data;
    calibrationStep.value = 2;
    ElMessage.success("标定计算成功！");
  } catch (e) { ElMessage.error(e.response?.data?.detail || "计算失败！"); }
  finally { isCalibrating.value = false; }
};

const cancelCalibrationProcess = async () => {
  try { await cancelCalibration(); } catch (e) {
    console.error("取消标定模式失败:", e);
  }
  calibrationDrawerVisible.value = false;
  calibrationStep.value = 0;
  capturedFramesCount.value = 0;
  calibrationResult.value = null;
};


// 生命周期钩子
onMounted(async () => {
  getDatasets(); // 首次挂载时加载数据集
  // 尝试获取相机参数，如果成功说明相机已连接，并启动WebSocket
  try {
    await cameraStore.fetchCameraParams();
    if (cameraStore.isConnected) {
      ElMessage.info("相机已连接，视频流已自动启动。");
      startWebSocket();
    }
  } catch (error) {
    console.warn("未检测到相机连接，请手动连接。", error);
  }
  getProfiles(); // 获取配置文件列表

  emitter.on('refresh-datasets', getDatasets);
});

onUnmounted(() => {
  // 在这里不再强制断开相机连接，因为状态由 store 管理
  // 只有当用户明确点击断开按钮或应用关闭时才断开
  // cameraStore.disconnectCamera(); // 移除此行
  if (isCollecting.value) {
    stopAcquisition();
  }
  if (calibrationDrawerVisible.value) {
    cancelCalibration();
  }
  stopWebSocket(); // 离开页面时停止视频流，但相机连接保持
  stopBrowserCamera();
  emitter.off('refresh-datasets', getDatasets);
});
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.video-container {
  width: 100%;
  aspect-ratio: 16 / 9;
  background-color: #0b1f35;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 16px;
  overflow: hidden;
}

.video-stream-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.browser-camera-tip {
  margin-top: 18px;
  padding: 14px;
  border: 1px solid rgba(30, 111, 255, 0.15);
  border-radius: 12px;
  background: #f5f9ff;
  color: #60758c;
  font-size: 13px;
  line-height: 1.7;
}

.video-placeholder {
  text-align: center;
  color: #c0c4cc;
}

.profile-actions {
  display: flex;
  width: 100%;
}

.el-slider {
  margin-left: 10px;
}

/* 新增：抽屉的 CSS */
.drawer-footer {
  margin-top: 20px;
  text-align: right;
}

.calibration-capture {
  text-align: center;
  padding: 40px 0;
}

.calibration-capture p {
  font-size: 18px;
  margin-bottom: 20px;
}

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
}
</style>
