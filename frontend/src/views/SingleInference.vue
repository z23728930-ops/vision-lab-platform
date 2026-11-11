<template>
  <!-- 新增一个 div 作为唯一的根节点，包裹所有内容 -->
  <div>
    <el-row :gutter="20">
      <!-- 左侧控制与上传 -->
      <el-col :span="8">
        <el-card>
          <template #header>控制面板</template>
          <el-form label-position="top">
            <el-form-item label="选择模型">
              <el-select v-model="selectedModel" placeholder="请选择模型" style="width: 100%;">
                <el-option v-for="model in models" :key="model.id" :label="model.name" :value="model.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="上传图片">
              <el-upload
                  drag
                  action="#"
                  :show-file-list="false"
                  :before-upload="handleBeforeUpload"
                  style="width: 100%;"
              >
                <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                <div class="el-upload__text">拖拽文件至此或 <em>点击上传</em></div>
              </el-upload>
            </el-form-item>
            <el-button type="primary" @click="startInference" :loading="isInferencing" :disabled="!selectedModel || !originalImageFile" style="width: 100%;">
              开始推理
            </el-button>
          </el-form>
        </el-card>
      </el-col>
      <!-- 右侧结果展示 -->
      <el-col :span="16">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card>
              <template #header>原图</template>
              <el-image :src="originalImageUrl" fit="contain" style="height: 400px; width: 100%;" />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card>
              <template #header>推理结果</template>
              <el-image :src="maskImageUrl" fit="contain" style="height: 400px; width: 100%;" />
            </el-card>
          </el-col>
        </el-row>
      </el-col>
    </el-row>
  </div> <!-- 结束唯一的根节点 div -->
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import { fetchModels } from '../api/models';
import apiClient from '../api'; // 用于拼接URL

const models = ref([]);
const selectedModel = ref(null);
const isInferencing = ref(false);

const originalImageFile = ref(null);
const originalImageUrl = ref('');
const maskImageUrl = ref('');

const getModels = async () => {
  const response = await fetchModels();
  models.value = response.data;
};

const handleBeforeUpload = (rawFile) => {
  originalImageFile.value = rawFile;
  originalImageUrl.value = URL.createObjectURL(rawFile);
  maskImageUrl.value = ''; // 清空上次结果
  return false; // 阻止自动上传
};

const startInference = async () => {
  isInferencing.value = true;
  maskImageUrl.value = ''; // 清空
  try {
    const formData = new FormData();
    formData.append('model_id', selectedModel.value);
    formData.append('image', originalImageFile.value);

    const response = await apiClient.post('/inference/single', formData, {
      headers: {'Content-Type': 'multipart/form-data'}
    });

    // 后端返回的是相对URL，我们需要拼接上baseURL
    const baseUrl = apiClient.defaults.baseURL.replace('/api/v1', '');
    maskImageUrl.value = baseUrl + response.data.mask_image_url;

  } catch(e) {
    ElMessage.error("推理失败！");
  } finally {
    isInferencing.value = false;
  }
};

onMounted(getModels);
</script>