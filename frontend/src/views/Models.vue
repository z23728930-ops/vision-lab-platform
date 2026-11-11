<template>
  <div>
    <!-- 操作区域 -->
    <el-card shadow="never" class="action-card">
      <el-button type="primary" :icon="Upload" @click="uploadDialogVisible = true">上传模型</el-button>
      <!-- 禁用条件：当没有模型或没有数据集时，不能发起推理 -->
      <el-button type="success" :icon="MagicStick" @click="inferenceDialogVisible = true" :disabled="!models.length || (!myDatasets.length && !publicDatasets.length)">
        发起推理
      </el-button>
    </el-card>
    <el-alert title="本地训练模型上传" description="请上传本小组训练得到的最佳权重文件，并使用“小组名称_模型类型”命名。普通学生只能删除自己上传的模型。" type="info" show-icon :closable="false" style="margin-top: 14px" />

    <!-- 模型表格 -->
    <el-card shadow="never" style="margin-top: 20px;">
      <el-table :data="models" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80"></el-table-column>
        <el-table-column label="任务类型" width="120"><template #default="scope"><el-tag>{{ taskType(scope.row.model_type) }}</el-tag></template></el-table-column>
        <el-table-column label="适用数据集" width="180"><template #default="scope">{{ compatibleDataset(scope.row.name) }}</template></el-table-column>
        <el-table-column label="文件状态" width="110"><template #default="scope"><el-tag :type="scope.row.file_exists ? 'success' : 'danger'">{{ scope.row.file_exists ? '文件可用' : '文件缺失' }}</el-tag></template></el-table-column>
        <el-table-column prop="name" label="模型名称"></el-table-column>
        <el-table-column prop="model_type" label="模型类型" width="150"></el-table-column>
        <el-table-column prop="version" label="版本" width="120"></el-table-column>
        <el-table-column label="上传者" width="130"><template #default="scope">{{ scope.row.uploaded_by_username || `用户 ${scope.row.uploaded_by_id}` }}</template></el-table-column>
        <el-table-column prop="description" label="描述"></el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button size="small" type="danger" :icon="Delete" :disabled="!canDeleteModel(scope.row)" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <div style="height: 400px;">
    <!-- 上传模型对话框 -->
    <el-dialog
        v-model="uploadDialogVisible"
        title="上传新模型"
        custom-class="my-custom-dialog"
        top="15vh"
        @close="resetUploadForm"
    >
      <el-form ref="uploadFormRef" :model="uploadForm" label-width="100px" :rules="uploadRules">
        <el-form-item label="模型名称" prop="name">
          <el-input v-model="uploadForm.name" placeholder="例如：第一组_YOLO_铸件缺陷"></el-input>
        </el-form-item>
        <el-form-item label="模型类型" prop="model_type">
          <el-select v-model="uploadForm.model_type" placeholder="请选择模型类型" style="width: 100%;">
            <el-option
                v-for="item in supportedModelTypes"
                :key="item.value"
                :label="item.label"
                :value="item.value"
            ></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="版本" prop="version">
          <el-input v-model="uploadForm.version"></el-input>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="uploadForm.description" type="textarea" placeholder="填写训练数据集、缺陷类别、训练轮数和主要指标"></el-input>
        </el-form-item>
        <el-form-item label="选择文件" prop="file" required>
          <el-upload ref="uploadRef" :auto-upload="false" :on-change="handleFileChange" :limit="1" accept=".pt, .pth, .tar, .pth.tar, .onnx">
            <template #trigger><el-button type="primary">选择模型文件</el-button></template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUpload" :loading="uploading">确认上传</el-button>
      </template>
    </el-dialog>

    <!-- 发起推理对话框 -->
    <el-dialog
        v-model="inferenceDialogVisible"
        title="发起推理任务"
        custom-class="my-custom-dialog"
    >
      <el-form :model="inferenceForm" label-width="120px" :rules="inferenceRules" ref="inferenceFormRef">
        <el-form-item label="任务名称" prop="job_name">
          <el-input v-model="inferenceForm.job_name" placeholder="为这次推理任务命名"></el-input>
        </el-form-item>
        <el-form-item label="选择模型" prop="model_id">
          <el-select v-model="inferenceForm.model_id" placeholder="请选择一个模型" style="width: 100%;">
            <el-option v-for="model in models" :key="model.id" :disabled="model.file_exists === false" :label="`${model.name} (ID: ${model.id})${model.file_exists === false ? ' - 文件缺失' : ''}`" :value="model.id"></el-option>
          </el-select>
        </el-form-item>

        <!-- 新增：数据集类型选择 -->
        <el-form-item label="数据集类型" prop="dataset_type">
          <el-radio-group v-model="inferenceForm.dataset_type" @change="handleDatasetTypeChange">
            <el-radio label="my_datasets">我的数据集</el-radio>
            <el-radio label="public_datasets">公开数据集</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="选择数据集" prop="source_dataset_id">
          <el-select v-model="inferenceForm.source_dataset_id" placeholder="请选择要推理的数据集" style="width: 100%;">
            <el-option
                v-for="dataset in filteredDatasets"
                :key="dataset.id"
                :disabled="dataset.ready_for_inference === false"
                :label="`${dataset.name} (ID: ${dataset.id})${dataset.ready_for_inference === false ? ' - 不可推理' : ''}`"
                :value="dataset.id"
            ></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="推理参数(JSON)">
          <!-- 推理参数 JSON 输入框，使用 type="textarea" 和 rows="8" -->
          <el-input v-model="inferenceForm.inference_params_str" type="textarea" :rows="8" placeholder='例如: {"image_size": 512, "threshold": 0.5}'></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inferenceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitInference" :loading="isInferencing">开始推理</el-button>
      </template>
    </el-dialog>
  </div>
  </div>
</template>

<script setup>
import {ref, onMounted, onUnmounted, computed} from 'vue';
import {fetchModels, uploadModel, deleteModel} from '../api/models';
import {fetchDatasets} from '../api/datasets'; // 确保这个 fetchDatasets 函数可以接受参数
import {createInferenceJob} from '../api/inference';
import {ElMessage, ElMessageBox} from 'element-plus';
import {Upload, Delete, MagicStick} from '@element-plus/icons-vue';
import emitter from '../utils/eventBus';
import {useUserStore} from '../store/user'; // 导入 user store
import {useRoute, useRouter} from 'vue-router';

const userStore = useUserStore();
const route = useRoute();
const router = useRouter();
const canDeleteModel = (model) => userStore.isAdmin || model.uploaded_by_id === userStore.userInfo?.id;

// 状态
const models = ref([]);
const taskType = (type = '') => ['yolo', 'faster_rcnn'].includes(type.toLowerCase()) ? '目标检测' : type.toLowerCase() === 'unet_cbam' ? '图像分割' : '待确认';
const compatibleDataset = (name = '') => ({ qk: 'qk', yolo8n: 'coco_for_yolov8n', 'my-test-unet': 'test_312' }[name.toLowerCase()] || '请在助手中指定');
const myDatasets = ref([]); // 存储当前用户的数据集 (包括私有和用户自己公开的)
const publicDatasets = ref([]); // 存储公开数据集 (其他用户创建并公开的)
const loading = ref(false);
const uploadDialogVisible = ref(false);
const uploading = ref(false);
const uploadFormRef = ref(null);
const uploadRef = ref(null);
const uploadForm = ref({name: '', model_type: '', version: '', description: '', file: null});

const inferenceDialogVisible = ref(false);
const isInferencing = ref(false);
const inferenceFormRef = ref(null);
const inferenceForm = ref({
  job_name: '',
  model_id: null,
  source_dataset_id: null,
  inference_params_str: JSON.stringify({image_size: 512, threshold: 0.5}, null, 2),
  dataset_type: 'my_datasets', // 默认选择“我的数据集”
});

// 支持的模型类型列表，实际项目中建议从后端获取
const supportedModelTypes = ref([
  {label: 'U-Net with CBAM', value: 'unet_cbam'},
  {label: 'YOLO', value: 'yolo'},
  {label: 'Faster-RCNN', value: 'faster_rcnn'},
  // 添加更多后端支持的模型类型
]);


// 验证规则
const uploadRules = {
  name: [{required: true, message: '请输入模型名称', trigger: 'blur'}],
  // 模型类型验证：确保在 'change' 事件时触发
  model_type: [{required: true, message: '请选择模型类型', trigger: 'change'}],
  version: [{required: true, message: '请输入模型版本', trigger: 'blur'}], // 添加版本必填验证
};
const inferenceRules = {
  job_name: [{required: true, message: '请输入任务名称', trigger: 'blur'}],
  model_id: [{required: true, message: '请选择模型', trigger: 'change'}],
  source_dataset_id: [{required: true, message: '请选择数据集', trigger: 'change'}],
  // 数据集类型验证：确保在 'change' 事件时触发
  dataset_type: [{required: true, message: '请选择数据集类型', trigger: 'change'}],
}

// 计算属性：根据选择的数据集类型过滤数据集列表
const filteredDatasets = computed(() => {
  if (inferenceForm.value.dataset_type === 'my_datasets') {
    return myDatasets.value;
  } else if (inferenceForm.value.dataset_type === 'public_datasets') {
    return publicDatasets.value;
  }
  return [];
});

// 方法：获取模型列表
const getModels = async () => {
  loading.value = true;
  try {
    const response = await fetchModels();
    models.value = response.data;
  } catch (error) {
    ElMessage.error('获取模型列表失败！');
  } finally {
    loading.value = false;
  }
};

// 方法：获取数据集列表，并根据用户ID和公开状态进行分类
const getDatasetsForSelect = async () => {
  try {
    const currentUserId = userStore.userInfo?.id;

    // 1. 获取当前用户拥有的所有数据集 (假设 fetchDatasets() 默认返回当前用户拥有的数据集)
    const myDatasetsResponse = await fetchDatasets();
    myDatasets.value = myDatasetsResponse.data;

    // 2. 获取所有公开数据集 (包括当前用户自己的公开数据集，以及其他用户的公开数据集)
    const allPublicAndMyDatasetsResponse = await fetchDatasets({include_public: true});
    const allDatasetsIncludingPublic = allPublicAndMyDatasetsResponse.data;

    // 3. 从所有数据集中过滤出“其他用户的公开数据集”
    // 这里的逻辑是：它是公开的 AND 它的拥有者不是当前用户
    publicDatasets.value = allDatasetsIncludingPublic.filter(dataset =>
        dataset.is_public && dataset.owner_id !== currentUserId
    );

    // 确保当前选中的数据集ID在切换类型后仍然有效
    // 如果当前选中的数据集ID不在当前类型的数据集中，则清空
    if (inferenceForm.value.source_dataset_id) {
      const selectedDatasetExistsInCurrentFilter = filteredDatasets.value.some(d => d.id === inferenceForm.value.source_dataset_id);
      if (!selectedDatasetExistsInCurrentFilter) {
        inferenceForm.value.source_dataset_id = null;
      }
    }

  } catch (error) {
    console.error("Failed to fetch datasets for select dropdown.", error);
    ElMessage.error("获取数据集列表失败！");
  }
};

// 方法：处理数据集类型切换时清空已选数据集ID
const handleDatasetTypeChange = () => {
  inferenceForm.value.source_dataset_id = null;
};

const applyInferencePreset = () => {
  if (route.query.startInference !== '1') return;
  const datasetId = Number(route.query.datasetId);
  const modelId = Number(route.query.modelId);
  const datasetType = route.query.datasetType === 'public_datasets' ? 'public_datasets' : 'my_datasets';
  inferenceForm.value.dataset_type = datasetType;
  inferenceForm.value.source_dataset_id = datasetId || null;
  inferenceForm.value.model_id = modelId || null;
  inferenceForm.value.job_name = `${userStore.userInfo?.username || '小组'}_${datasetType === 'public_datasets' ? '正式检测' : '检测任务'}`;
  inferenceDialogVisible.value = true;
  router.replace({ name: 'Models' });
};


const handleFileChange = (file) => {
  uploadForm.value.file = file.raw;
};
const resetUploadForm = () => {
  uploadFormRef.value?.resetFields();
  uploadRef.value?.clearFiles();
  uploadForm.value.file = null;
};

const submitUpload = async () => {
  await uploadFormRef.value.validate(async (valid) => {
    if (valid && uploadForm.value.file) {
      const formData = new FormData();
      Object.keys(uploadForm.value).forEach(key => {
        if (key !== 'file') formData.append(key, uploadForm.value[key]);
      });
      formData.append('file', uploadForm.value.file);

      uploading.value = true;
      try {
        await uploadModel(formData);
        ElMessage.success('模型上传成功！');
        uploadDialogVisible.value = false;
        getModels();
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '模型上传失败！');
      } finally {
        uploading.value = false;
      }
    } else {
      ElMessage.warning('请填写必填项并选择文件！');
    }
  });
};

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要删除模型 "${row.name}" 吗？`, '警告', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await deleteModel(row.id);
      ElMessage.success('删除成功！');
      getModels();
    } catch (error) {
      ElMessage.error('删除失败！');
    }
  }).catch(() => {
  });
};

const submitInference = async () => {
  await inferenceFormRef.value.validate(async (valid) => {
    if (valid) {
      let params = {};
      try {
        params = JSON.parse(inferenceForm.value.inference_params_str);
      } catch (e) {
        ElMessage.error("推理参数不是有效的JSON格式！");
        return;
      }

      isInferencing.value = true;
      try {
        await createInferenceJob({
          job_name: inferenceForm.value.job_name,
          model_id: inferenceForm.value.model_id,
          source_dataset_id: inferenceForm.value.source_dataset_id,
          inference_params: params,
        });
        ElMessage.success("推理任务已成功提交！结果将在后台生成。");
        inferenceDialogVisible.value = false;
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || "提交推理任务失败！");
      } finally {
        isInferencing.value = false;
      }
    }
  });
};

// 生命周期钩子：组件挂载和卸载时获取数据并监听事件
onMounted(async () => {
  await Promise.all([getModels(), getDatasetsForSelect()]);
  applyInferencePreset();

  // 监听 'refresh-datasets' 事件，当数据集更新时刷新下拉列表
  emitter.on('refresh-datasets', getDatasetsForSelect);
});

onUnmounted(() => {
  // 在组件卸载时取消监听，防止内存泄漏
  emitter.off('refresh-datasets', getDatasetsForSelect);
});
</script>

<style scoped>
.action-card {
  margin-bottom: 20px;
}

/* 针对自定义对话框的样式调整 */
.my-custom-dialog {
  width: 40% !important; /* 调整对话框宽度，使其看起来更协调 */
  max-width: 600px; /* 限制最大宽度 */
  min-width: 400px; /* 限制最小宽度 */
}

/* 深度选择器调整 Element Plus 对话框内部元素样式 */
/* 调整对话框主体内容区域的 padding，使其更紧凑 */
:deep(.el-dialog__body) {
  padding: 20px 25px;
  /* 修改点1: 设置对话框内容区域的最大高度 */
  /* 如果内容较少，它会拉伸到这个高度，如果超出，则会出现滚动条 */
  max-height: 100%; /* 增加高度，使其更饱满 */
  overflow-y: auto; /* 当内容超出最大高度时，显示垂直滚动条 */
}

/* 调整对话框头部 padding */
:deep(.el-dialog__header) {
  padding: 20px 25px 10px;
}

/* 调整对话框底部 footer padding */
:deep(.el-dialog__footer) {
  padding: 10px 25px 20px;
}

/* 调整对话框遮罩层颜色 */
/* el-overlay 是 Element Plus 动态添加到 body 下的全局元素，必须使用 :deep() 才能在 scoped 样式中生效 */
:deep(.el-overlay) {
  background-color: rgba(0, 0, 0, 0.6) !important; /* 设置为半透明黑色 */
  /* z-index 通常不需要在这里设置，Element Plus 会自动管理 */
}

/* 解决推理参数 JSON 输入框高度问题 */
/* 针对 el-textarea 内部的 textarea 元素 */
:deep(.el-form-item__content .el-textarea__inner) {
  min-height: 140px !important; /* 修改点2: 增加最小高度，配合 rows="8" */
  height: auto !important; /* 允许高度根据内容自适应，但至少是 min-height */
  resize: vertical; /* 允许用户垂直拖动调整大小 */
}
</style>
