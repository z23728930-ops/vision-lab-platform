<script setup>
import { ref, reactive, onMounted, computed,watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {ArrowLeft, Plus, Close, Rank, QuestionFilled, Loading, Picture // 引入Loading和Picture图标
} from '@element-plus/icons-vue';
import { useProcessingStore } from '../store/processing'; // 继续使用处理任务的store
import { previewProcessingImage } from '../api/processing';
import { useUserStore } from '../store/user'; // 如果需要用户权限判断
import { fetchDatasets } from '../api/datasets';

// 引入拖拽库，适配Vue 3的vuedraggable
import draggable from 'vuedraggable/src/vuedraggable';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const processingStore = useProcessingStore();

const datasetId = ref(route.params.datasetId);
const datasetName = ref(''); // 存储数据集名称
const sourceDataset = ref(null);
const loadingDataset = ref(true);

const processingForm = reactive({
  output_name: '',
  steps: []
});
const processing = ref(false); // 控制"开始处理"按钮的加载状态

// 用于预览的图片相关
const previewImageFile = ref(null); // 用户上传的预览图片文件
const previewImageUrl = ref(''); // 预览图片的URL
const originalPreviewUrl = ref(''); // 原始图片URL (如果从数据集选择)
const processedPreviewUrl = ref(''); // 处理后图片URL
const previewLoading = ref(false);
const previewError = ref('');
const previewMode = ref('compare'); // 'compare', 'single-step', 'full-chain'

// 当前选中的步骤，用于在右侧显示详情
const selectedStepIndex = ref(0); // 默认选中第一个步骤

// 预处理操作列表 (与你现有代码中的 availableOperations 相同)
const availableOperations = [
  {
    value: 'grayscale',
    label: '灰度化',
    params: [],
    description: '将彩色图像转换为灰度图像，去除颜色信息，只保留亮度信息。',
    example: {
      original: '/src/assets/sample_fig/apple.jpg',
      processed: '/src/assets/sample_fig/apple_Grayscale.jpeg'
    }
  },
  {
    value: 'gaussian_blur',
    label: '高斯模糊',
    params: [{
      name: 'kernel_size',
      type: 'number',
      default: 5,
      label: '核大小',
      min: 1,
      step: 2,
      description: '模糊核的大小，必须是奇数。'
    }],
    description: '使用高斯函数对图像进行平滑处理，常用于减少图像噪声。核大小越大，模糊效果越明显。',
    example: {
      original: '/src/assets/sample_fig/city.jpg',
      processed: '/src/assets/sample_fig/city_GaussianBlur_k9.jpeg'
    }
  },
  {
    value: 'median_blur',
    label: '中值滤波',
    params: [{
      name: 'kernel_size',
      type: 'number',
      default: 5,
      label: '核大小',
      min: 1,
      step: 2,
      description: '中值滤波核的大小，必须是奇数。'
    }],
    description: '一种非线性数字滤波技术，常用于去除图像或信号中的椒盐噪声。',
    example: {
      original: '/src/assets/sample_fig/sky.jpg',
      processed: '/src/assets/sample_fig/sky_MedianBlur_k7.jpeg'
    }
  },
  {
    value: 'flip',
    label: '翻转',
    params: [{
      name: 'code',
      type: 'select',
      label: '方向',
      default: 0,
      options: [
        {value: 0, label: '垂直翻转'},
        {value: 1, label: '水平翻转'},
        {value: -1, label: '水平垂直翻转'}
      ],
      description: '0为垂直翻转，1为水平翻转，-1为水平垂直翻转。'
    }],
    description: '根据指定方向翻转图像。',
    example: {
      original: '/src/assets/sample_fig/sky.jpg',
      processed: '/src/assets/sample_fig/sky_FlipH.jpeg'
    }
  },
  {
    value: 'resize',
    label: '调整大小',
    params: [
      {
        name: 'width',
        type: 'number',
        label: '宽度 (px)',
        default: 512,
        min: 32,
        max: 4096,
        description: '调整后的图像宽度。工业检测建议使用 512 或 640。'
      },
      {
        name: 'height',
        type: 'number',
        label: '高度 (px)',
        default: 512,
        min: 32,
        max: 4096,
        description: '调整后的图像高度。工业检测建议使用 512 或 640。'
      }
    ],
    description: '将图像调整为模型输入尺寸。尺寸过小会丢失缺陷细节；qk 模型建议使用 512 × 512。',
    example: {
      original: '/src/assets/sample_fig/city.jpg',
      processed: '/src/assets/sample_fig/city_Resize_600x400.jpeg'
    }
  },
  {
    value: 'rotate',
    label: '旋转',
    params: [{
      name: 'angle',
      type: 'select',
      label: '角度 (顺时针)',
      default: 90,
      options: [
        {value: 90, label: '90°'},
        {value: 180, label: '180°'},
        {value: 270, label: '270°'}
      ],
      description: '图像顺时针旋转的角度。'
    }],
    description: '将图像按指定角度顺时针旋转。',
    example: {
      original: '/src/assets/sample_fig/sky.jpg',
      processed: '/src/assets/sample_fig/sky_Rotate90.jpeg'
    }
  },
  {
    value: 'brightness_contrast',
    label: '亮度对比度',
    params: [
      {
        name: 'alpha',
        type: 'number',
        label: '对比度 (Alpha)',
        default: 1.0,
        min: 0,
        step: 0.1,
        description: '对比度调整因子，大于1增加对比度，小于1降低。'
      },
      {
        name: 'beta',
        type: 'number',
        label: '亮度 (Beta)',
        default: 0,
        description: '亮度调整值，正值增加亮度，负值降低。'
      }
    ],
    description: '调整图像的亮度和对比度。Alpha值控制对比度（大于1增加，小于1降低），Beta值控制亮度（正值增加，负值降低）。',
    example: {
      original: '/src/assets/sample_fig/apple.jpg',
      processed: '/src/assets/sample_fig/apple_BC_a1.5_b30.jpeg'
    }
  },
  {
    value: 'invert_colors',
    label: '反色',
    params: [],
    description: '将图像的颜色反转，例如黑色变为白色，白色变为黑色。',
    example: {
      original: '/src/assets/sample_fig/city.jpg',
      processed: '/src/assets/sample_fig/city_Invert.jpeg'
    }
  },
  {
    value: 'sharpen',
    label: '锐化',
    params: [],
    description: '增强图像的边缘和细节，使图像看起来更清晰。',
    example: {
      original: '/src/assets/sample_fig/apple.jpg',
      processed: '/src/assets/sample_fig/apple_Sharpen.jpeg'
    }
  },
  {
    value: 'canny_edge',
    label: 'Canny 边缘检测',
    params: [
      {
        name: 'threshold1',
        type: 'number',
        label: '阈值1',
        default: 100,
        min: 0,
        description: '第一个滞后阈值。'
      },
      {
        name: 'threshold2',
        type: 'number',
        label: '阈值2',
        default: 200,
        min: 0,
        description: '第二个滞后阈值。'
      }
    ],
    description: '一种多级边缘检测算法，用于从各种图像中提取广泛有用的信息，并显著减少需要处理的数据量。',
    example: {
      original: '/src/assets/sample_fig/apple.jpg',
      processed: '/src/assets/sample_fig/apple_Canny_t150_t2150.jpeg'
    }
  },
  {
    value: 'threshold',
    label: '二值化',
    params: [
      {
        name: 'thresh',
        type: 'number',
        label: '阈值',
        default: 127,
        min: 0,
        max: 255,
        description: '用于区分前景和背景的阈值。'
      },
      {
        name: 'maxval',
        type: 'number',
        label: '最大值',
        default: 255,
        min: 0,
        max: 255,
        description: '当像素值大于阈值时赋予的最大值。'
      },
      {
        name: 'type',
        type: 'select',
        label: '类型',
        default: 'binary',
        options: [
          { value: 'binary', label: '二值化' },
          { value: 'binary_inv', label: '反色二值化' },
          { value: 'trunc', label: '截断' },
          { value: 'tozero', label: '取零' },
          { value: 'tozero_inv', label: '反色取零' }
        ],
        description: '二值化处理的类型。'
      }
    ],
    description: '将图像转换为二值图像，即图像中的像素点只有两个值：0和255（通常是黑和白）。',
    example: {
      original: '/src/assets/sample_fig/city.jpg',
      processed: '/src/assets/sample_fig/city_Threshold_binary_t100.jpeg'
    }
  },
];

// 计算属性：获取当前选中步骤的详细信息
const currentStepDetail = computed(() => {
  if (processingForm.steps.length > 0 && selectedStepIndex.value !== null && selectedStepIndex.value < processingForm.steps.length) {
    const step = processingForm.steps[selectedStepIndex.value];
    const op = availableOperations.find(o => o.value === step.type);
    return op || null;
  }
  return null;
});

const getOperationParams = (type) => {
  const op = availableOperations.find(o => o.value === type);
  return op ? op.params : [];
};

const getDefaultStepConfig = (type = 'grayscale') => {
  const defaultOp = availableOperations.find(op => op.value === type);
  const params = {};
  if (defaultOp && defaultOp.params) {
    defaultOp.params.forEach(param => {
      if (param.type === 'select' && (param.default === null || param.default === undefined) && param.options && param.options.length > 0) {
        params[param.name] = param.options[0].value;
      } else if (param.default !== undefined) {
        params[param.name] = param.default;
      }
    });
  }
  return { type, params };
};

const addProcessingStep = () => {
  processingForm.steps.push(getDefaultStepConfig());
  selectedStepIndex.value = processingForm.steps.length - 1; // 选中新添加的步骤
};

const removeProcessingStep = (index) => {
  processingForm.steps.splice(index, 1);
  if (selectedStepIndex.value >= processingForm.steps.length) {
    selectedStepIndex.value = Math.max(0, processingForm.steps.length - 1); // 调整选中索引
  }
  if (processingForm.steps.length === 0) {
    selectedStepIndex.value = null; // 没有步骤时清空选中
  }
  updatePreview(); // 步骤删除后更新预览
};

const onOperationChange = (step) => {
  const newConfig = getDefaultStepConfig(step.type);
  step.params = newConfig.params;
  // 触发预览更新
  updatePreview();
};

const handleStepClick = (index) => {
  selectedStepIndex.value = index;
};

// 处理预览图片上传
const handlePreviewImageChange = (file) => {
  if (previewImageUrl.value) URL.revokeObjectURL(previewImageUrl.value);
  previewImageFile.value = file.raw;
  if (previewImageFile.value) {
    previewImageUrl.value = URL.createObjectURL(previewImageFile.value);
    originalPreviewUrl.value = previewImageUrl.value; // 原始预览图就是上传的图
    updatePreview(); // 触发预览更新
  }
};

const updatePreview = async () => {
  if (!previewImageFile.value) {
    processedPreviewUrl.value = '';
    previewError.value = '请先上传一张预览图片。';
    return;
  }

  previewLoading.value = true;
  previewError.value = '';
  processedPreviewUrl.value = ''; // 清空之前的预览

  try {
    if (processingForm.steps.length === 0) {
      processedPreviewUrl.value = '';
      previewError.value = '没有处理步骤，无法生成预览。';
      return;
    }

    const steps = previewMode.value === 'single-step'
      ? [processingForm.steps[selectedStepIndex.value]].filter(Boolean)
      : processingForm.steps;
    if (!steps.length) {
      previewError.value = '请选择一个步骤以查看单步预览。';
      return;
    }
    const response = await previewProcessingImage(previewImageFile.value, steps);
    if (processedPreviewUrl.value) URL.revokeObjectURL(processedPreviewUrl.value);
    processedPreviewUrl.value = URL.createObjectURL(response.data);

  } catch (err) {
    previewError.value = '预览生成失败: ' + (err.response?.data?.detail || err.message);
    processedPreviewUrl.value = '';
  } finally {
    previewLoading.value = false;
  }
};


const submitProcessingJob = async () => {
  if (!processingForm.output_name) {
    ElMessage.warning('请输入输出数据集名称！');
    return;
  }
  if (processingForm.steps.length === 0) {
    ElMessage.warning('请至少添加一个处理步骤！');
    return;
  }
  for (const step of processingForm.steps) {
    const opParams = getOperationParams(step.type);
    for (const param of opParams) {
      // 检查必填参数，对于数字和选择类型，如果default为null/undefined，则用户必须填写
      if ((param.type === 'number' || param.type === 'select') &&
          (param.default === null || param.default === undefined) &&
          (step.params[param.name] === null || step.params[param.name] === undefined || step.params[param.name] === '')) {
        ElMessage.warning(`请为步骤 "${availableOperations.find(op => op.value === step.type)?.label || step.type}" 的参数 "${param.label}" 填写有效值！`);
        return;
      }
      // 额外检查数字类型是否为有效数字
      if (param.type === 'number' && typeof step.params[param.name] !== 'number') {
        ElMessage.warning(`请为步骤 "${availableOperations.find(op => op.value === step.type)?.label || step.type}" 的参数 "${param.label}" 填写有效的数字！`);
        return;
      }
    }
  }

  processing.value = true;
  try {
    await processingStore.startJob({
      source_dataset_id: datasetId.value,
      output_name: processingForm.output_name,
      processing_steps: processingForm.steps
    });
    ElMessage.success('处理任务已成功提交！您可以在任务中心查看进度。');
    router.push({ name: 'Datasets' }); // 返回数据集列表页
  } catch (error) {
    console.error("Failed to submit processing job:", error);
    ElMessage.error("提交处理任务失败：" + (error.response?.data?.detail || error.message));
  } finally {
    processing.value = false;
  }
};

const goBack = () => {
  router.back(); // 返回上一页
};

const fetchDatasetDetail = async (id) => {
  try {
    // 预处理允许使用自己的数据集或公共数据集（例如公共 qk）
    const response = await fetchDatasets({ include_public: true });
    const dataset = response.data?.find(item => Number(item.id) === Number(id));
    if (dataset) {
      return dataset;
    } else {
      throw new Error('未找到指定的数据集');
    }
  } catch (error) {
    throw error;
  }
};

onMounted(async () => {
  if (!datasetId.value) {
    ElMessage.error('未指定数据集ID！');
    router.push({ name: 'Datasets' });
    return;
  }
  try {
    loadingDataset.value = true;
    const dataset = await fetchDatasetDetail(datasetId.value);
    sourceDataset.value = dataset;
    datasetName.value = dataset.name;
    processingForm.output_name = `${datasetName.value}_processed`;
    addProcessingStep(); // 默认添加一个步骤
  } catch (error) {
    ElMessage.error('获取数据集详情失败！' + (error.response?.data?.detail || error.message));
    router.push({ name: 'Datasets' });
  } finally {
    loadingDataset.value = false;
  }
});

// 监听预览模式和步骤变化，更新预览
watch([previewMode, () => processingForm.steps, selectedStepIndex], () => {
  updatePreview();
}, { deep: true }); // 深度监听 steps 数组内部变化

</script>

<template>
  <div class="image-processing-page">
    <el-page-header @back="goBack" class="page-header">
      <template #content>
        <span class="text-large font-600 mr-3"> 图像预处理中心 </span>
        <span class="text-sm mr-2">
          <el-tag size="small" type="info">数据集: {{ datasetName || '加载中...' }}</el-tag>
        </span>
      </template>
    </el-page-header>

    <el-alert
        v-if="sourceDataset?.is_public && sourceDataset?.owner_id !== userStore.userInfo?.id"
        title="正在使用公共数据集"
        description="预览不会保存图片；应用到整个数据集后，系统会新建一个归你所有的数据集，原公共数据集不会被修改。"
        type="info"
        :closable="false"
        show-icon
        style="margin: 0 0 12px"
    />

    <div class="content-wrapper">
      <!-- 左侧：预处理步骤配置区 -->
      <div class="left-panel" style="height: 540px">
      <el-card class="left-panel" shadow="hover">
        <template #header>
          <div class="card-header-title">
            <span>处理配置</span>
          </div>
        </template>
        <!-- el-card__body 默认插槽内容，现在作为flex容器，其自身将处理滚动 -->
        <!-- Fixed top section: Output Dataset Name -->
        <div class="fixed-form-top-section">
          <el-form :model="processingForm" label-position="top">
            <el-form-item label="输出数据集名称" required>
              <el-input v-model="processingForm.output_name" placeholder="请输入处理后的数据集名称"></el-input>
            </el-form-item>
          </el-form>
          <el-divider content-position="left">处理步骤链</el-divider>
        </div>

        <!-- Scrollable middle section: Processing Steps Chain and Add Button -->
        <div class="processing-steps-scroll-container">
          <draggable
              v-model="processingForm.steps"
              item-key="id"
              class="processing-steps-list"
              handle=".drag-handle"
              tag="div"
          >
            <template #item="{ element: step, index }">
              <el-card
                  :class="['processing-step-card', { 'is-selected': selectedStepIndex === index }]"
                  shadow="hover"
                  @click="handleStepClick(index)"
              >
                <template #header>
                  <div class="step-card-header">
                    <el-icon class="drag-handle"><Rank /></el-icon>
                    <el-select
                        v-model="step.type"
                        placeholder="选择操作"
                        style="width: 160px;"
                        @change="onOperationChange(step)"
                        @click.stop
                    >
                      <el-option
                          v-for="op in availableOperations"
                          :key="op.value"
                          :label="op.label"
                          :value="op.value"
                      />
                    </el-select>
                    <el-button
                        type="danger"
                        :icon="Close"
                        circle
                        size="small"
                        @click.stop="removeProcessingStep(index)"
                        class="remove-step-btn"
                    ></el-button>
                  </div>
                </template>
                <div class="params-container">
                  <div v-for="param in getOperationParams(step.type)" :key="param.name" class="param-item">
                    <span class="param-label">{{ param.label }}:</span>
                    <el-input-number
                        v-if="param.type === 'number'"
                        v-model="step.params[param.name]"
                        :placeholder="param.default"
                        :step="param.step || 1"
                        :min="param.min"
                        :max="param.max"
                        controls-position="right"
                        size="small"
                        style="width: 100px;"
                        @click.stop
                        @change="updatePreview"
                    />
                    <el-select
                        v-else-if="param.type === 'select'"
                        v-model="step.params[param.name]"
                        :placeholder="param.default"
                        size="small"
                        style="width: 100px;"
                        @click.stop
                        @change="updatePreview"
                    >
                      <el-option
                          v-for="option in param.options"
                          :key="option.value"
                          :label="option.label"
                          :value="option.value"
                      />
                    </el-select>
                  </div>
                </div>
              </el-card>
            </template>
          </draggable>
          <el-button :icon="Plus" @click="addProcessingStep" style="width: 100%; margin-top: 15px;" plain>添加处理步骤</el-button>
        </div>

        <!-- Fixed bottom section: Action Buttons -->
        <div class="footer-actions">
          <el-button @click="goBack">取消</el-button>
          <el-button type="primary" @click="submitProcessingJob" :loading="processing">应用到整个数据集</el-button>
        </div>
      </el-card>
      </div>

      <!-- 右侧：预览与信息区 -->
      <div class="right-panel" style="height: 540px">

      <el-card class="right-panel" shadow="hover">
        <template #header>
          <div class="card-header-title">
            <span>预览与详情</span>
            <el-radio-group v-model="previewMode" size="small">
              <el-radio-button value="compare">对比预览</el-radio-button>
              <el-radio-button value="full-chain">完整链条</el-radio-button>
              <el-radio-button value="single-step">单步效果</el-radio-button>
            </el-radio-group>
          </div>
        </template>
        <!-- el-card__body 默认插槽内容，所有内容都在这个可滚动容器内 -->
        <el-divider content-position="left">操作详情</el-divider>
        <div class="operation-detail-area">
          <div v-if="currentStepDetail">
            <h3>{{ currentStepDetail.label }}</h3>
            <p class="description">{{ currentStepDetail.description }}</p>
            <div v-if="currentStepDetail.params && currentStepDetail.params.length > 0" class="param-details">
              <h4>参数说明：</h4>
              <ul>
                <li v-for="param in currentStepDetail.params" :key="param.name">
                  <strong>{{ param.label }} ({{ param.name }}):</strong> {{ param.description || '无描述' }}
                  <span v-if="param.default !== undefined"> (默认值: {{ param.default }})</span>
                  <span v-if="param.min !== undefined && param.max !== undefined"> (范围: {{ param.min }} - {{ param.max }})</span>
                </li>
              </ul>
            </div>
            <div v-if="currentStepDetail.example" class="example-images">
              <h4>效果示例：</h4>
              <div class="comparison-display">
                <div class="image-box">
                  <span class="image-label">示例原始图</span>
                  <el-image :src="currentStepDetail.example.original" fit="contain" class="example-image-display">
                    <template #error>
                      <div class="image-slot">
                        <el-icon><Picture /></el-icon>
                        <span>加载失败</span>
                      </div>
                    </template>
                  </el-image>
                </div>
                <div class="image-box">
                  <span class="image-label">示例处理后</span>
                  <el-image :src="currentStepDetail.example.processed" fit="contain" class="example-image-display">
                    <template #error>
                      <div class="image-slot">
                        <el-icon><Picture /></el-icon>
                        <span>加载失败</span>
                      </div>
                    </template>
                  </el-image>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="请在左侧选择一个处理步骤查看详情"></el-empty>
        </div>

        <el-divider content-position="left">预览效果</el-divider>
        <div class="preview-area">
          <div class="preview-image-upload">
            <el-upload
                class="image-uploader"
                :auto-upload="false"
                :show-file-list="false"
                :on-change="handlePreviewImageChange"
                accept="image/*"
            >
              <img v-if="previewImageUrl" :src="previewImageUrl" class="uploaded-image-thumbnail" />
              <div v-else class="image-upload-placeholder">
                <el-icon class="image-uploader-icon"><Plus /></el-icon>
                <span>上传图片预览</span>
                <small>支持 JPG / PNG</small>
              </div>
            </el-upload>
            <span v-if="previewImageFile" class="preview-filename">预览图：{{ previewImageFile.name }}</span>
          </div>

          <div class="image-comparison-container">
            <div v-if="previewLoading" class="preview-loading">
              <el-icon class="is-loading" :size="30"><Loading /></el-icon>
              <span>正在生成预览...</span>
            </div>
            <div v-else-if="previewError" class="preview-error">
              <el-alert :title="previewError" type="warning" show-icon :closable="false" />
            </div>
            <div v-else-if="!originalPreviewUrl && !processedPreviewUrl" class="preview-placeholder">
              <p>请上传图片以查看预览效果。</p>
            </div>
            <div v-else class="comparison-display">
              <div class="image-box">
                <span class="image-label">原始图片</span>
                <el-image :src="originalPreviewUrl" fit="contain" class="preview-image-display">
                  <template #error>
                    <div class="image-slot">
                      <el-icon><Picture /></el-icon>
                      <span>加载失败</span>
                    </div>
                  </template>
                </el-image>
              </div>
              <div class="image-box">
                <span class="image-label">处理效果</span>
                <el-image :src="processedPreviewUrl" fit="contain" class="preview-image-display">
                  <template #error>
                    <div class="image-slot">
                      <el-icon><Picture /></el-icon>
                      <span>加载失败</span>
                    </div>
                  </template>
                </el-image>
              </div>
            </div>
          </div>
        </div>
      </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Base layout for the entire page */
.image-processing-page {
  padding: 5px;
  background-color: #f5f9ff;
  min-height: 100vh; /* Ensure it takes full viewport height */
  display: flex;
  flex-direction: column; /* Arrange header and content vertically */
}

/* Page Header - Fixed at top */
.page-header {
  background-color: #fff;
  padding: 15px 20px;
  margin-bottom: 10px;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  flex-shrink: 0; /* Prevents header from shrinking */
}
.page-header .text-large {
  font-size: 1.5em;
  font-weight: 600;
  color: #333;
}
.page-header .el-tag {
  margin-left: 10px;
}

/* Main content area - Takes remaining height, contains left and right panels */
.content-wrapper {
  display: flex;
  gap: 20px;
  flex-grow: 1; /* Allows content wrapper to expand and fill available vertical space */
  min-height: 0; /* Crucial for flex children to correctly calculate their heights */
}

/* Left and Right Panels - Both should fill available height */
.left-panel,
.right-panel {
  flex-grow: 1; /* Allows panels to grow and fill height */
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  display: flex; /* Make the card itself a flex container */
  flex-direction: column; /* Arrange header and body vertically */
  min-height: 0; /* Crucial for internal flex children sizing */
}

/* Card Header - Fixed height within the card */
.card-header-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1.1em;
  font-weight: bold;
  color: #333;
}

/* --- Left Panel Specific Styles --- */

/* el-card content area */
.left-panel :deep(.el-card__content) {
  display: flex;
  flex-direction: column; /* Arrange its children vertically */
  flex-grow: 1; /* Allows the body to take up remaining space within the card */
  padding: 20px; /* Default Element Plus card body padding */
  /* We will manage internal spacing using margins/paddings of its direct children */
}

/* Fixed top section in left panel (Output Dataset Name) */
.fixed-form-top-section {
  flex-shrink: 0; /* Prevents this section from shrinking */
  /* No extra margin needed as el-form-item and el-divider have their own */
}

/* Scrollable middle section in left panel (Processing Steps and Add Button) */
.processing-steps-scroll-container {
  flex-grow: 1; /* Allows this section to take all remaining space */
  overflow-y: auto; /* Enables vertical scrolling */
  padding-bottom: 15px; /* Space for the "Add Step" button at the bottom of the scrollable area */
  /* Add a small right padding to account for scrollbar, if needed, but usually not with 'auto' */
  padding-right: 10px; /* Account for scrollbar width */
  margin-right: -10px; /* Pull back to align content */
  height: 200px;
}

.processing-steps-list {
  min-height: 100px; /* Ensures some minimum height even with few steps, reducing whitespace */
  padding: 5px 0; /* Small vertical padding for the draggable list */
}

.processing-step-card {
  margin-bottom: 10px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  transition: all 0.2s ease-in-out;
  cursor: pointer;
}
.processing-step-card:hover {
  border-color: var(--el-color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.processing-step-card.is-selected {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-5);
  background-color: var(--el-color-primary-light-9);
}

.step-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  /* El-card__header has default padding, we need to adjust content inside */
  padding: 0; /* Remove default padding from template content */
  margin: -10px -10px 0 -10px; /* Pull content into the card header's default padding */
}
.drag-handle {
  cursor: grab;
  color: #909399;
  margin-right: 10px;
  font-size: 16px;
  padding: 10px; /* Increase clickable area */
}
.drag-handle:active {
  cursor: grabbing;
}
.remove-step-btn {
  margin-left: auto; /* Push to the right */
}

.params-container {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 5px 0;
  justify-content: flex-start;
}
.param-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  flex-basis: calc(50% - 5px); /* Two columns layout */
  min-width: 150px;
}
.param-label {
  color: #606266;
  white-space: nowrap;
}

/* Fixed bottom section in left panel (Action Buttons) */
.footer-actions {
  flex-shrink: 0; /* Prevents this section from shrinking */
  margin-top: 20px; /* Space from the scrollable area above */
  padding-top: 15px; /* Internal padding for the border */
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* --- Right Panel Specific Styles --- */

/* Target the el-card__body for flex layout and scrolling */
.right-panel :deep(.el-card__body) {
  display: flex;
  flex-direction: column; /* Arrange its children vertically */
  flex-grow: 1; /* Allows the body to take up remaining space within the card */
  overflow-y: auto; /* Enables vertical scrolling for the entire right panel content */
  padding: 20px; /* Default Element Plus card body padding */
  /* Add a small right padding to account for scrollbar, if needed */
  padding-right: 10px; /* Account for scrollbar width */

}

/* Content sections within the right panel body */
.operation-detail-area,
.preview-area {
  flex-shrink: 0; /* Prevents these sections from shrinking when content is small */
  /* They will take their natural height. If content overflows, the parent el-card__body will scroll. */
}

.operation-detail-area {
  padding: 15px;
  background-color: #fcfcfc;
  border-radius: 8px;
  border: 1px solid #eee;
  margin-bottom: 20px; /* Space between detail and preview */
}
.operation-detail-area h3 {
  margin-top: 0;
  color: var(--el-color-primary);
  font-size: 1.3em;
  margin-bottom: 10px;
}
.operation-detail-area .description {
  font-size: 14px;
  line-height: 1.6;
  color: #606266;
  margin-bottom: 15px;
}
.operation-detail-area h4 {
  margin-top: -10px;
  margin-bottom: 8px;
  color: #404040;
  font-size: 1.1em;
}
.param-details ul {
  list-style: disc;
  padding-left: 20px;
  margin: 0;
}
.param-details li {
  font-size: 13px;
  line-height: 1.5;
  color: #707070;
  margin-bottom: 5px;
}
.example-images {
  margin-top: 0px;
}

.preview-area {
  padding: 10px 0;
  text-align: center;
}

.preview-image-upload {
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.image-uploader {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  width: 220px;
  height: 178px;
  transition: var(--el-transition-duration-fast);
}
.image-uploader :deep(.el-upload) {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.image-uploader:hover {
  border-color: var(--el-color-primary);
}
.image-upload-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #606266;
  line-height: 1.4;
  white-space: nowrap;
}
.image-upload-placeholder small {
  color: #909399;
  font-size: 12px;
}
.image-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 32px;
  height: 32px;
}
.uploaded-image-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
.preview-filename {
  margin-top: 10px;
  font-size: 13px;
  color: #606266;
}

.image-comparison-container {
  min-height: 250px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f9f9f9;
  border-radius: 8px;
  border: 1px solid #eee;
  padding: 15px;
  position: relative;
}

.preview-loading, .preview-error, .preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
  color: #909399;
  font-size: 14px;
}
.preview-loading .el-icon {
  margin-bottom: 10px;
}
.preview-error .el-alert {
  width: 80%;
}

.comparison-display {
  display: flex;
  gap: 20px;
  justify-content: center;
  align-items: flex-start;
  width: 100%;
  flex-wrap: wrap;
}
.image-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  width: calc(50% - 10px);
  min-width: 280px;
}
.image-label {
  font-weight: bold;
  color: #505050;
}
.preview-image-display, .example-image-display {
  width: 100%;
  max-width: 400px;
  height: 250px;
  object-fit: contain;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background-color: #fff;
}

.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.image-slot .el-icon {
  font-size: 30px;
  margin-bottom: 5px;
}
</style>
