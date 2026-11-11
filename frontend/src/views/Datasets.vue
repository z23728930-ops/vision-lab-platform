<template>
  <div class="datasets-page">
    <!-- 操作区域 -->
    <el-card shadow="hover" class="action-card">
      <div class="card-header">
        <el-radio-group v-model="datasetViewMode" @change="loadDatasets" size="default">
          <el-radio-button :value="'my'">我的数据集</el-radio-button>
          <el-radio-button :value="'all'">所有公开数据集</el-radio-button>
        </el-radio-group>

        <el-button type="primary" :icon="Upload" @click="uploadDialogVisible = true">上传数据集</el-button>
      </div>
    </el-card>

    <!-- 新增的提示信息 -->
    <el-alert
        title="温馨提示"
        description="仅您上传到服务器的数据集可以进行数据标注操作。"
        type="info"
        show-icon
        :closable="false"
        class="annotation-tip"
    />

    <!-- 数据集表格 -->
    <el-card shadow="hover" class="data-table-card">
      <el-table :data="datasets" v-loading="loading" style="width: 100%" row-key="id">
        <el-table-column prop="id" label="ID" width="80"></el-table-column>
        <el-table-column prop="name" label="数据集名称" min-width="150"></el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip min-width="200"></el-table-column>
        <el-table-column label="图片数量" width="100"><template #default="scope"><el-tag :type="datasetImageCount(scope.row) > 0 ? 'success' : 'danger'">{{ datasetImageCount(scope.row) }}</el-tag></template></el-table-column>
        <el-table-column label="标注检查" width="155">
          <template #default="scope">
            <div class="annotation-progress-cell">
              <el-progress :percentage="scope.row.annotation_progress || 0" :stroke-width="7" :show-text="false" />
              <span>{{ scope.row.reviewed_image_count || 0 }}/{{ datasetImageCount(scope.row) }} 已检查</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="推荐模型" width="150"><template #default="scope">{{ recommendedModel(scope.row.name) }}</template></el-table-column>
        <el-table-column label="目录状态" width="110"><template #default="scope"><el-tag :type="scope.row.path_exists ? 'success' : 'danger'">{{ scope.row.path_exists ? '目录存在' : '路径失效' }}</el-tag></template></el-table-column>
        <el-table-column label="推理状态" width="110"><template #default="scope"><el-tag :type="scope.row.ready_for_inference ? 'success' : 'warning'">{{ scope.row.ready_for_inference ? '可推理' : '不可用' }}</el-tag></template></el-table-column>
        <el-table-column label="状态" width="110"><template #default="scope"><el-tag :type="datasetImageCount(scope.row) > 0 ? 'success' : 'warning'">{{ datasetImageCount(scope.row) > 0 ? '可推理' : '空数据集' }}</el-tag></template></el-table-column>
        <el-table-column label="所有者" width="120">
          <template #default="scope">
            <!-- 关键修改：根据 owner_id 判断是否是当前用户 -->
            <span v-if="scope.row.owner_id === userStore.userInfo?.id">
              我
              <el-tag size="small" type="info" effect="plain" style="margin-left: 5px;">({{ scope.row.owner?.username }})</el-tag>
            </span>
            <span v-else-if="scope.row.owner">{{ scope.row.owner.username }}</span>
            <span v-else>未知</span>
          </template>
        </el-table-column>
        <el-table-column label="公开" width="100" align="center">
          <template #default="scope">
            <el-switch
                v-model="scope.row.is_public"
                :disabled="scope.row.owner_id !== userStore.userInfo?.id && !userStore.isAdmin"
                @change="togglePublic(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ new Date(scope.row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="scope">
            <div class="operation-buttons-group">
              <el-button
                  size="small"
                  :icon="View"
                  @click="handleBrowse(scope.row)"
                  :disabled="scope.row.owner_id !== userStore.userInfo?.id && !scope.row.is_public"
                  plain
              >
                浏览
              </el-button>
              <el-button
                  size="small"
                  type="primary"
                  :icon="Edit"
                  @click="handleAnnotate(scope.row)"
                  :disabled="scope.row.owner_id !== userStore.userInfo?.id"
              >
                标注
              </el-button>
              <el-dropdown trigger="click" @command="handleOperationCommand($event, scope.row)">
                <el-button size="small" :icon="MoreFilled" circle />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :icon="Download" :disabled="scope.row.owner_id !== userStore.userInfo?.id && !scope.row.is_public" command="download">下载</el-dropdown-item>
                    <el-dropdown-item :icon="CircleCheck" command="readiness">检测准备检查</el-dropdown-item>
                    <el-dropdown-item :icon="MagicStick" :disabled="scope.row.owner_id !== userStore.userInfo?.id && !scope.row.is_public" command="process">图像预处理</el-dropdown-item>
                    <el-dropdown-item :icon="Scissor" :disabled="scope.row.owner_id !== userStore.userInfo?.id || datasetImageCount(scope.row) < 3" command="split">划分数据集</el-dropdown-item>
                    <el-dropdown-item :icon="MagicStick" :disabled="scope.row.owner_id !== userStore.userInfo?.id || scope.row.annotated_image_count < 3" command="experience-training">导出体验训练包</el-dropdown-item>
                    <el-dropdown-item :icon="Download" :disabled="scope.row.owner_id !== userStore.userInfo?.id || scope.row.annotation_progress < 100" command="training-package">导出训练包</el-dropdown-item>
                    <el-dropdown-item :icon="Share" :disabled="scope.row.owner_id !== userStore.userInfo?.id && !userStore.isAdmin" command="export">导出标注</el-dropdown-item>
                    <el-dropdown-item :icon="Delete" :disabled="scope.row.owner_id !== userStore.userInfo?.id" command="delete" divided>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 上传数据集对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传数据集" width="500px" @close="resetUploadForm">
      <el-form ref="uploadFormRef" :model="uploadForm" label-width="100px">
        <el-form-item label="数据集名称" prop="name" required>
          <el-input v-model="uploadForm.name"></el-input>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="uploadForm.description" type="textarea"></el-input>
        </el-form-item>
        <el-form-item label="是否公开" prop="is_public">
          <el-switch v-model="uploadForm.is_public" />
        </el-form-item>
        <el-form-item label="上传类型" prop="upload_type">
          <el-radio-group v-model="uploadForm.upload_type">
            <el-radio value="zip">ZIP 文件</el-radio>
            <el-radio value="folder">文件夹</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="选择文件" prop="file" required>
          <template v-if="uploadForm.upload_type === 'zip'">
            <el-upload
                ref="uploadRef"
                :auto-upload="false"
                :on-change="handleZipFileChange"
                :limit="1"
                accept=".zip"
            >
              <template #trigger>
                <el-button type="primary">选择 .zip 文件</el-button>
              </template>
            </el-upload>
          </template>
          <!-- 文件夹上传：使用自定义拖拽区域 -->
          <template v-else-if="uploadForm.upload_type === 'folder'">
            <div
                id="customFolderDropZone"
                class="custom-upload-drop-zone"
                @dragover.prevent="handleDragOver"
                @dragleave="handleDragLeave"
                @drop.prevent="handleFolderDrop"
                @click="triggerFolderInput"
            >
              <el-icon class="el-icon--upload"><FolderOpened /></el-icon>
              <div class="el-upload__text">拖拽文件夹至此或 <em>点击选择文件夹</em></div>
              <input
                  type="file"
                  id="folderInput"
                  webkitdirectory
                  directory
                  multiple
                  @change="handleFolderInputChange"
                  style="display: none;"
              />
              <!-- 移除 <template #tip> 标签，让 div.el-upload__tip 直接作为子元素 -->
              <div class="el-upload__tip">
                选择一个文件夹，将上传其所有内容（包括子文件夹）。
                <span v-if="uploadForm.folder_files.length > 0" style="color: #67c23a; margin-left: 10px;">
                    已选择 {{ uploadForm.folder_files.length }} 个文件。
                  </span>
              </div>
            </div>
          </template>
          <template v-else>
            <div style="color: #909399; font-size: 13px;">请选择上传类型</div>
          </template>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUpload" :loading="uploading">确认上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="readinessDialogVisible" title="检测准备检查" width="620px">
      <div v-loading="checkingReadiness" class="readiness-panel">
        <template v-if="readinessResult">
          <div class="readiness-summary">
            <div><span>数据集</span><strong>{{ readinessResult.dataset.name }}</strong></div>
            <div><span>有效图片</span><strong>{{ readinessResult.valid_image_count }}</strong></div>
            <div><span>访问权限</span><strong>{{ readinessResult.permission }}</strong></div>
          </div>
          <div class="readiness-checks">
            <div v-for="item in readinessResult.checks" :key="item.key" class="readiness-item">
              <el-icon :class="item.passed ? 'check-pass' : 'check-fail'"><CircleCheck v-if="item.passed" /><CircleClose v-else /></el-icon>
              <div><strong>{{ item.label }}</strong><span>{{ item.detail }}</span></div>
            </div>
          </div>
          <el-alert :title="readinessResult.ready ? '检测准备检查通过，可以发起正式推理' : '检查未通过，请先处理异常项'" :type="readinessResult.ready ? 'success' : 'error'" :closable="false" show-icon />
        </template>
      </div>
      <template #footer>
        <el-button @click="readinessDialogVisible = false">关闭</el-button>
        <el-button :disabled="!readinessResult" @click="browseCheckedDataset">浏览样本</el-button>
        <el-button type="primary" :disabled="!readinessResult?.ready" @click="startCheckedInference">使用此数据集发起推理</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="splitDialogVisible" title="自动划分数据集" width="560px">
      <el-alert title="推荐使用 80% 训练、10% 验证、10% 测试" description="只生成划分清单，不移动、复制或删除原图片；相同随机种子可复现相同结果。" type="info" :closable="false" show-icon style="margin-bottom: 18px" />
      <el-alert v-if="splittingDataset?.unreviewed_image_count > 0" :title="`还有 ${splittingDataset.unreviewed_image_count} 张图片未检查标注`" description="可以先完成划分，但导出训练包前应完成全部图片检查。无缺陷图片也需要在标注页确认。" type="warning" :closable="false" show-icon style="margin-bottom: 18px" />
      <el-form label-width="110px">
        <el-form-item label="数据集"><strong>{{ splittingDataset?.name }}</strong></el-form-item>
        <el-form-item label="训练集比例"><el-input-number v-model="splitForm.train" :min="1" :max="99" /><span class="ratio-unit">%</span></el-form-item>
        <el-form-item label="验证集比例"><el-input-number v-model="splitForm.val" :min="0" :max="98" /><span class="ratio-unit">%</span></el-form-item>
        <el-form-item label="测试集比例"><el-input-number v-model="splitForm.test" :min="1" :max="99" /><span class="ratio-unit">%</span></el-form-item>
        <el-form-item label="随机种子"><el-input-number v-model="splitForm.seed" :min="0" :max="999999" /></el-form-item>
      </el-form>
      <div v-if="splitResult?.counts" class="split-result">
        <div><span>总图片</span><strong>{{ splitResult.counts.total }}</strong></div>
        <div><span>训练集</span><strong>{{ splitResult.counts.train }}</strong></div>
        <div><span>验证集</span><strong>{{ splitResult.counts.val }}</strong></div>
        <div><span>测试集</span><strong>{{ splitResult.counts.test }}</strong></div>
      </div>
      <template #footer>
        <el-button @click="splitDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="splitting" @click="submitSplit">{{ splitResult?.configured ? '重新划分' : '开始划分' }}</el-button>
      </template>
    </el-dialog>

    <!-- 浏览数据集内容对话框 (修改为通用文件浏览) -->
    <el-dialog v-model="browseDialogVisible" :title="`浏览: ${browsingDataset?.name}`" width="80%" top="5vh">
      <div v-if="browsingError" class="browse-error">
        <el-alert title="加载内容失败" :description="browsingError" type="error" show-icon />
      </div>
      <div v-else-if="isBrowsing" class="browse-loading">
        <el-icon class="is-loading" :size="26"><Loading /></el-icon>
        <span>正在加载内容...</span>
      </div>
      <el-scrollbar v-else-if="browsingFiles.length" height="70vh">
        <div class="browse-content-wrapper">
          <el-tree
              :data="browsingTreeData"
              :props="treeProps"
              node-key="path"
              default-expand-all
              @node-click="handleFileNodeClick"
              class="file-tree"
          >
            <template #default="{ node, data }">
              <span class="custom-tree-node">
                <el-icon style="margin-right: 8px;">
                  <Folder v-if="data.is_directory" />
                  <Picture v-else-if="data.file_type === 'image'" />
                  <Document v-else-if="data.file_type === 'text'" />
                  <Files v-else />
                </el-icon>
                <span>{{ node.label }}</span>
                <span v-if="!data.is_directory && data.file_type !== 'image'" style="margin-left: 10px; color: #909399; font-size: 0.8em;">
                  ({{ data.file_type }})
                </span>
              </span>
            </template>
          </el-tree>

          <div v-if="selectedFileContent" class="file-content-preview">
            <el-divider content-position="left">文件预览: {{ selectedFileContent.name }}</el-divider>
            <div v-if="selectedFileContent.type === 'image'" class="preview-image">
              <el-image :src="selectedFileContent.url" fit="contain" style="max-width: 100%; max-height: 400px;"/>
            </div>
            <div v-else-if="selectedFileContent.type === 'text'" class="preview-text">
              <el-input
                  type="textarea"
                  :rows="15"
                  v-model="selectedFileContent.content"
                  readonly
              ></el-input>
            </div>
            <div v-else class="preview-other">
              <p>不支持直接预览此文件类型。</p>
              <el-button type="primary" :icon="Download" @click="downloadSelectedFile">下载文件</el-button>
            </div>
          </div>
        </div>
      </el-scrollbar>
      <el-empty v-else description="此数据集中没有找到任何文件"></el-empty>
    </el-dialog>

    <!-- 导出标注对话框 -->
    <el-dialog v-model="exportDialogVisible" title="导出标注" width="400px">
      <el-form :model="exportForm" label-width="100px">
        <el-form-item label="选择格式">
          <el-select v-model="exportForm.format" placeholder="请选择导出格式" style="width: 100%;">
            <el-option label="YOLO (.txt)" value="yolo"></el-option>
            <el-option label="Pascal VOC (.xml)" value="pascal_voc"></el-option>
            <el-option label="COCO (.json)" value="coco"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="包含图片">
          <el-switch v-model="exportForm.includeImages" />
          <span style="margin-left: 10px; font-size: 12px; color: #909399;">导出的ZIP包中是否包含图片文件</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitExport" :loading="isExporting">开始导出</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { fetchDatasets, uploadDataset, uploadDatasetFolder, deleteDataset, downloadDatasetBlob, updateDatasetPublicStatus, browseDataset, exportAnnotations, fetchFileContent, fetchDatasetSplit, splitDataset, exportTrainingPackage, exportExperienceTrainingPackage, checkDatasetReadiness } from '../api/datasets';
// import { useProcessingStore } from '../store/processing'; // 不再直接使用，因为处理逻辑已分离
import { useUserStore } from '../store/user';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Upload, Download, Delete, MagicStick, View, Loading, Edit, Share, FolderOpened, Picture, Document, Files, Folder, MoreFilled, Scissor, CircleCheck, CircleClose } from '@element-plus/icons-vue';
import emitter from "../utils/eventBus.js";

const userStore = useUserStore();
const datasetImageCount = (d) => d.image_count ?? d.images_count ?? (Array.isArray(d.images) ? d.images.length : 0);
const recommendedModel = (name = '') => {
  const datasetName = name.toLowerCase();
  if (datasetName === 'qk' || datasetName.startsWith('qk_')) return 'qk';
  if (datasetName === 'coco_for_yolov8n' || datasetName.startsWith('coco_for_yolov8n_')) return 'yolo8n';
  if (datasetName === 'test_312' || datasetName.startsWith('test_312_')) return 'my-test-unet';
  return '请在助手中指定';
};
const router = useRouter();

const datasets = ref([]);
const loading = ref(false);
const splitDialogVisible = ref(false);
const splittingDataset = ref(null);
const splitting = ref(false);
const splitResult = ref(null);
const splitForm = reactive({ train: 80, val: 10, test: 10, seed: 42 });
const readinessDialogVisible = ref(false);
const checkingReadiness = ref(false);
const readinessResult = ref(null);
const checkedDataset = ref(null);

const datasetViewMode = ref('my');

// 上传对话框状态
const uploadDialogVisible = ref(false);
const uploading = ref(false);
const uploadFormRef = ref(null);
const uploadRef = ref(null); // 用于 ZIP 文件上传
const uploadForm = ref({
  name: '',
  description: '',
  file: null, // 用于 ZIP 文件
  folder_files: [], // 用于文件夹上传的文件列表
  is_public: false,
  upload_type: 'zip', // 默认上传类型
});

// 浏览对话框状态
const browseDialogVisible = ref(false);
const isBrowsing = ref(false);
const browsingDataset = ref(null);
const browsingFiles = ref([]); // 存储所有文件信息
const browsingTreeData = ref([]); // 用于 ElTree 的数据
const treeProps = {
  label: 'name',
  children: 'children',
  isLeaf: 'is_leaf', // 标记是否为叶子节点 (由后端 is_directory 决定)
};
const selectedFileContent = ref(null); // 存储当前选中的文件内容或信息
const browsingError = ref('');


// 导出标注相关状态
const exportDialogVisible = ref(false);
const isExporting = ref(false);
const exportForm = reactive({
  datasetId: null,
  format: 'yolo', // 默认导出格式
  includeImages: true, // 默认包含图片
});
const currentExportDataset = ref(null);

const loadDatasets = async () => {
  loading.value = true;
  try {
    const params = {};
    if (datasetViewMode.value === 'all') {
      params.include_public = true;
    }

    const response = await fetchDatasets(params);
    datasets.value = response.data;
  } catch (error) {
    ElMessage.error('获取数据集列表失败！' + (error.response?.data?.detail || error.message));
  } finally {
    loading.value = false;
  }
};

// --- 上传相关方法 ---
// ZIP 文件上传的处理函数
const handleZipFileChange = (file) => {
  uploadForm.value.file = file.raw;
};

// 文件夹拖拽上传的处理函数
const handleFolderDrop = (event) => {
  const dropZone = event.currentTarget;
  dropZone.style.borderColor = '#d9d9d9'; // 恢复默认边框颜色

  const files = event.dataTransfer.files;
  const collectedFiles = [];

  if (files.length > 0) {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      // 检查 webkitRelativePath 是否存在，这是文件夹拖拽的关键
      if (file.webkitRelativePath) {
        collectedFiles.push(file);
      } else {
        // 如果没有 webkitRelativePath，可能是单个文件拖拽，或者浏览器不支持
        console.warn(`文件 ${file.name} 没有 webkitRelativePath，可能不是文件夹内部文件。`);
      }
    }
    uploadForm.value.folder_files = collectedFiles;
    if (collectedFiles.length > 0) {
      ElMessage.success(`已成功拖拽 ${collectedFiles.length} 个文件。`);
    } else {
      uploadForm.value.folder_files = []; // 清空，因为没有有效文件
      ElMessage.warning('拖拽的不是一个文件夹，或文件夹中没有有效文件。');
    }
  } else {
    uploadForm.value.folder_files = [];
    ElMessage.warning('未拖拽任何文件。');
  }
};

// 文件夹点击选择的处理函数 (通过隐藏的 input[type=file] 触发)
const handleFolderInputChange = (event) => {
  const files = event.target.files;
  const collectedFiles = [];

  if (files.length > 0) {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      // webkitRelativePath 在点击选择文件夹时通常也可用
      if (file.webkitRelativePath) {
        collectedFiles.push(file);
      } else {
        console.warn(`文件 ${file.name} 没有 webkitRelativePath，可能不是文件夹内部文件。`);
      }
    }
    uploadForm.value.folder_files = collectedFiles;
    if (collectedFiles.length > 0) {
      ElMessage.success(`已成功选择 ${collectedFiles.length} 个文件。`);
    } else {
      uploadForm.value.folder_files = []; // 清空，因为没有有效文件
      ElMessage.warning('选择的不是一个文件夹，或文件夹中没有有效文件。');
    }
  } else {
    uploadForm.value.folder_files = [];
    ElMessage.warning('未选择任何文件。');
  }
  // 清除 input 的值，以便下次选择相同文件夹也能触发 change 事件
  event.target.value = '';
};

// 拖拽区域的视觉反馈
const handleDragOver = (event) => {
  event.currentTarget.style.borderColor = 'var(--el-color-primary)'; // 拖拽进入时高亮
};

const handleDragLeave = (event) => {
  event.currentTarget.style.borderColor = 'var(--el-border-color)'; // 拖拽离开时恢复
};

// 点击“点击选择文件夹”文本时触发隐藏的 input
const triggerFolderInput = () => {
  document.getElementById('folderInput').click();
};


const resetUploadForm = () => {
  if (uploadFormRef.value) {
    uploadFormRef.value.resetFields();
  }
  if(uploadRef.value) {
    uploadRef.value.clearFiles();
  }
  // 对于自定义文件夹上传，手动清空文件列表和隐藏 input 的值
  uploadForm.value.file = null;
  uploadForm.value.folder_files = [];
  uploadForm.value.is_public = false;
  uploadForm.value.upload_type = 'zip'; // 重置为默认类型

  const folderInput = document.getElementById('folderInput');
  if (folderInput) {
    folderInput.value = ''; // 清除 input 的值
  }
};

const submitUpload = async () => {
  if (!uploadForm.value.name) {
    ElMessage.warning('请填写数据集名称！');
    return;
  }

  let formData = new FormData();
  formData.append('name', uploadForm.value.name);
  formData.append('description', uploadForm.value.description);
  formData.append('is_public', uploadForm.value.is_public);

  uploading.value = true;
  try {
    if (uploadForm.value.upload_type === 'zip') {
      if (!uploadForm.value.file) {
        ElMessage.warning('请选择 .zip 文件！');
        uploading.value = false;
        return;
      }
      formData.append('file', uploadForm.value.file);
      await uploadDataset(formData); // 调用 ZIP 上传 API
    } else if (uploadForm.value.upload_type === 'folder') {
      if (!uploadForm.value.folder_files || uploadForm.value.folder_files.length === 0) {
        ElMessage.warning('请选择一个文件夹或拖拽文件夹！');
        uploading.value = false;
        return;
      }

      // 遍历文件夹中的所有文件，并添加到 FormData
      uploadForm.value.folder_files.forEach((file, index) => {
        // 确保有相对路径，否则不上传此文件
        if (file.webkitRelativePath) {
          formData.append('files', file); // FastAPI 接收 List[UploadFile]
          formData.append('relative_paths', file.webkitRelativePath); // FastAPI 接收 List[str]
        } else {
          console.warn(`文件 [${index}] ${file.name} 没有 webkitRelativePath。此文件不会被上传。`);
        }
      });

      // 检查是否有文件被成功添加到 FormData
      if (Array.from(formData.keys()).filter(key => key === 'files').length === 0) {
        ElMessage.warning('没有找到带有相对路径的有效文件可供上传。');
        uploading.value = false;
        return;
      }

      await uploadDatasetFolder(formData); // 调用文件夹上传 API
    }

    ElMessage.success('上传成功！');
    uploadDialogVisible.value = false;
    loadDatasets(); // 刷新列表
  } catch (error) {
    console.error("上传失败:", error); // 打印详细错误
    ElMessage.error('上传失败！' + (error.response?.data?.detail || error.message || '未知错误'));
  } finally {
    uploading.value = false;
  }
};

const handleDownload = async (row) => {
  try {
    ElMessage.info(`正在准备下载 '${row.name}'...`);
    const blob = await downloadDatasetBlob(row.id);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${row.name.replace(/\s/g, '_')}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    ElMessage.success('下载成功！');
  } catch (error) {
    console.error('Download failed:', error);
    ElMessage.error('下载失败！' + (error.response?.data?.detail || error.message));
  }
};

const handleDelete = (row) => {
  ElMessageBox.confirm(
      `确定要永久删除数据集 "${row.name}" 吗？此操作不可逆，相关文件将从服务器删除。`,
      '警告',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
  ).then(async () => {
    try {
      await deleteDataset(row.id);
      ElMessage.success('删除成功！');
      loadDatasets();
    } catch (error) {
      ElMessage.error('删除失败！' + (error.response?.data?.detail || error.message));
    }
  }).catch(() => {
    // 用户取消
  });
};

const togglePublic = async (row) => {
  try {
    await updateDatasetPublicStatus(row.id, row.is_public);
    ElMessage.success(`数据集 "${row.name}" 的公开状态已更新。`);
  } catch (error) {
    ElMessage.error("状态更新失败！" + (error.response?.data?.detail || error.message));
    row.is_public = !row.is_public;
  }
}

// --- 浏览数据集内容相关方法 (修改) ---
const handleBrowse = async (row) => {
  browsingDataset.value = row;
  browseDialogVisible.value = true;
  isBrowsing.value = true;
  browsingError.value = '';
  browsingFiles.value = [];
  browsingTreeData.value = [];
  selectedFileContent.value = null; // 清空选中文件内容

  try {
    // 调用新的 browseDataset API，它现在返回所有文件类型
    const response = await browseDataset(row.id);
    const baseStaticUrl = response.data.base_url;
    const files = response.data.files; // 后端返回的通用文件列表

    browsingFiles.value = files.map(file => ({
      ...file,
      url: `${baseStaticUrl}/${file.relative_path}`, // 完整可访问 URL
      name: file.name, // 文件名或文件夹名
      path: file.relative_path, // 完整相对路径
      is_directory: file.is_directory,
      file_type: file.file_type, // 后端判断的文件类型 (image, text, other, folder)
      is_leaf: !file.is_directory, // 用于 ElTree
    }));

    // 将扁平化的文件列表转换为树形结构
    browsingTreeData.value = buildFileTree(browsingFiles.value);

  } catch (error) {
    browsingError.value = error.response?.data?.detail || "无法获取文件列表。";
  } finally {
    isBrowsing.value = false;
  }
};

// 辅助函数：将扁平化的文件列表转换为树形结构
const buildFileTree = (files) => {
  const tree = [];
  const pathMap = {}; // 用于快速查找节点

  // 创建所有文件和目录的节点映射
  files.forEach(file => {
    pathMap[file.path] = { ...file, children: [] };
  });

  // 构建树
  files.forEach(file => {
    const parts = file.path.split('/');
    if (parts.length > 1) { // 如果有父目录
      const parentPath = parts.slice(0, -1).join('/');
      if (pathMap[parentPath]) { // 确保父节点存在
        pathMap[parentPath].children.push(pathMap[file.path]);
      } else {
        // 如果父节点不存在（例如，后端只返回了子文件而没有父目录信息，但我们的后端会返回所有）
        // 这通常不应该发生，除非数据不完整
        console.warn(`Parent path ${parentPath} not found for file ${file.path}`);
        tree.push(pathMap[file.path]); // 作为根节点处理，防止丢失
      }
    } else { // 根目录下的文件/文件夹
      tree.push(pathMap[file.path]);
    }
  });

  // 过滤掉作为子节点出现的重复根节点（因为pathMap会将所有路径都添加到tree中，需要过滤）
  const rootNodes = tree.filter(node => {
    // 如果一个节点的父路径不在pathMap中，或者其父节点不是一个目录，则它是一个根节点
    const parts = node.path.split('/');
    if (parts.length === 1) return true; // 顶层文件/文件夹
    const parentPath = parts.slice(0, -1).join('/');
    return !pathMap[parentPath] || !pathMap[parentPath].is_directory;
  });


  // 排序子节点 (文件夹在前，文件在后，然后按名称排序)
  const sortNodes = (nodes) => {
    nodes.sort((a, b) => {
      if (a.is_directory && !b.is_directory) return -1;
      if (!a.is_directory && b.is_directory) return 1;
      return a.name.localeCompare(b.name);
    });
    nodes.forEach(node => {
      if (node.children && node.children.length > 0) {
        sortNodes(node.children);
      }
    });
  };
  sortNodes(rootNodes); // 对根节点进行排序

  return rootNodes;
};

// 点击文件树节点
const handleFileNodeClick = async (data) => {
  if (data.is_directory) {
    selectedFileContent.value = null; // 点击目录不预览
    return;
  }

  selectedFileContent.value = {
    name: data.name,
    url: data.url,
    type: data.file_type,
    content: null, // 文本内容
  };

  if (data.file_type === 'text') {
    try {
      const content = await fetchFileContent(data.url);
      selectedFileContent.value.content = content;
    } catch (error) {
      selectedFileContent.value.content = `无法加载文本内容: ${error.message}`;
      ElMessage.error('加载文本文件失败！');
    }
  } else if (data.file_type === 'image') {
    // 图片类型已经在 selectedFileContent.url 中，直接显示
  } else {
    // 其他文件类型，提供下载链接
  }
};

// 下载选中的文件 (用于非图片/文本文件)
const downloadSelectedFile = () => {
  if (selectedFileContent.value && selectedFileContent.value.url) {
    const link = document.createElement('a');
    link.href = selectedFileContent.value.url;
    link.download = selectedFileContent.value.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
};


// --- 处理数据集的逻辑已分离到 ImageProcessingCenter.vue ---
const handleProcess = (row) => {
  // 跳转到新的图像预处理中心页面
  router.push({ name: 'ImageProcessingCenter', params: { datasetId: row.id } });
};

const handleAnnotate = (row) => {
  router.push({ name: 'AnnotationTool', params: { datasetId: row.id } });
};

const handleReadinessCheck = async (row) => {
  checkedDataset.value = row;
  readinessResult.value = null;
  readinessDialogVisible.value = true;
  checkingReadiness.value = true;
  try {
    const response = await checkDatasetReadiness(row.id);
    readinessResult.value = response.data;
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '检测准备检查失败');
  } finally {
    checkingReadiness.value = false;
  }
};

const browseCheckedDataset = () => {
  readinessDialogVisible.value = false;
  handleBrowse(checkedDataset.value);
};

const startCheckedInference = () => {
  const model = readinessResult.value?.recommended_model;
  router.push({
    name: 'Models',
    query: {
      startInference: '1',
      datasetId: readinessResult.value.dataset.id,
      modelId: model?.id,
      datasetType: readinessResult.value.permission === '公共只读' ? 'public_datasets' : 'my_datasets',
    },
  });
};

// --- 导出标注相关方法 ---
const handleExportAnnotations = (row) => {
  currentExportDataset.value = row;
  exportForm.datasetId = row.id;
  exportDialogVisible.value = true;
};

const handleSplit = async (row) => {
  splittingDataset.value = row;
  splitResult.value = null;
  Object.assign(splitForm, { train: 80, val: 10, test: 10, seed: 42 });
  splitDialogVisible.value = true;
  try {
    const response = await fetchDatasetSplit(row.id);
    splitResult.value = response.data;
    if (response.data.configured && response.data.ratios) {
      Object.assign(splitForm, {
        train: Math.round(response.data.ratios.train * 100),
        val: Math.round(response.data.ratios.val * 100),
        test: Math.round(response.data.ratios.test * 100),
        seed: response.data.seed,
      });
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '读取划分信息失败');
  }
};

const submitSplit = async () => {
  const totalRatio = splitForm.train + splitForm.val + splitForm.test;
  if (totalRatio !== 100) {
    ElMessage.warning(`当前比例合计为 ${totalRatio}%，必须等于 100%`);
    return;
  }
  splitting.value = true;
  try {
    const response = await splitDataset(splittingDataset.value.id, {
      train_ratio: splitForm.train / 100,
      val_ratio: splitForm.val / 100,
      test_ratio: splitForm.test / 100,
      seed: splitForm.seed,
    });
    splitResult.value = response.data;
    ElMessage.success('数据集划分完成');
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '数据集划分失败');
  } finally {
    splitting.value = false;
  }
};

const handleTrainingPackageExport = async (row) => {
  try {
    ElMessage.info('正在整理YOLO训练包，请稍候...');
    const blob = await exportTrainingPackage(row.id);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${row.name.replace(/\s/g, '_')}_YOLO_training.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    ElMessage.success('训练包导出成功');
  } catch (error) {
    let message = '训练包导出失败';
    if (error.response?.data instanceof Blob) {
      try {
        const body = JSON.parse(await error.response.data.text());
        message = body.detail || message;
      } catch (_) {}
    }
    ElMessage.error(message);
  }
};

const handleExperienceTrainingExport = async (row) => {
  try {
    await ElMessageBox.confirm(
        '体验训练包只使用少量已标注图片，生成的模型会严重过拟合，仅用于观察训练过程，不能用于最后质检。是否继续？',
        '导出体验训练包',
        { confirmButtonText: '继续导出', cancelButtonText: '取消', type: 'warning' }
    );
    ElMessage.info('正在生成小样本体验训练包...');
    const blob = await exportExperienceTrainingPackage(row.id);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${row.name.replace(/\s/g, '_')}_YOLO_experience_training.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    ElMessage.success('体验训练包导出成功');
  } catch (error) {
    if (error === 'cancel' || error === 'close') return;
    let message = '体验训练包导出失败';
    if (error.response?.data instanceof Blob) {
      try {
        const body = JSON.parse(await error.response.data.text());
        message = body.detail || message;
      } catch (_) {}
    }
    ElMessage.error(message);
  }
};

const submitExport = async () => {
  if (!exportForm.datasetId || !exportForm.format) {
    ElMessage.warning('请选择数据集和导出格式！');
    return;
  }

  isExporting.value = true;
  try {
    ElMessage.info(`正在准备导出标注数据 (${exportForm.format})...`);
    const blob = await exportAnnotations(exportForm.datasetId, exportForm.format, exportForm.includeImages);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    const filename = `${currentExportDataset.value.name.replace(/\s/g, '_')}_${exportForm.format}_annotations.zip`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    ElMessage.success('标注数据导出成功！');
    exportDialogVisible.value = false;
  } catch (error) {
    console.error('导出标注失败:', error);
    ElMessage.error('导出标注失败！' + (error.response?.data?.detail || error.message));
  } finally {
    isExporting.value = false;
  }
};

// --- 处理下拉菜单命令的函数 ---
const handleOperationCommand = (command, row) => {
  switch (command) {
    case 'download':
      handleDownload(row);
      break;
    case 'readiness':
      handleReadinessCheck(row);
      break;
    case 'process':
      handleProcess(row); // 调用新的跳转逻辑
      break;
    case 'split':
      handleSplit(row);
      break;
    case 'training-package':
      handleTrainingPackageExport(row);
      break;
    case 'experience-training':
      handleExperienceTrainingExport(row);
      break;
    case 'export':
      handleExportAnnotations(row);
      break;
    case 'delete':
      handleDelete(row);
      break;
    default:
      break;
  }
};


onMounted(() => {
  loadDatasets();
  emitter.on('refresh-datasets', loadDatasets);
});

onUnmounted(() => {
  emitter.off('refresh-datasets', loadDatasets);
});
</script>

<style scoped>
/* 页面整体布局和美化 */
.datasets-page {
  padding: 20px 24px;
  background-color: var(--color-bg);
  min-height: calc(100dvh - 60px);
}

.ratio-unit { margin-left: 8px; color: #6b7c93; }
.split-result { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 8px; }
.split-result div { display: flex; flex-direction: column; gap: 6px; padding: 14px; text-align: center; background: #f5f9ff; border: 1px solid rgba(30, 111, 255, 0.15); border-radius: 12px; }
.split-result span { color: #6b7c93; font-size: 13px; }
.split-result strong { color: #0f2a44; font-size: 22px; }
.annotation-progress-cell { display: grid; gap: 5px; }
.annotation-progress-cell span { font-size: 12px; color: #6b7c93; }
.readiness-panel { min-height: 260px; }
.readiness-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 18px; }
.readiness-summary div { display: flex; flex-direction: column; gap: 6px; padding: 14px; background: #f5f9ff; border-radius: 12px; }
.readiness-summary span, .readiness-item span { color: #6b7c93; font-size: 13px; }
.readiness-summary strong { color: #0f2a44; }
.readiness-checks { display: grid; gap: 10px; margin-bottom: 18px; }
.readiness-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-bottom: 1px solid #edf2f7; }
.readiness-item > div { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.check-pass { color: #2f9e6b; font-size: 20px; }
.check-fail { color: #e45656; font-size: 20px; }

/* 卡片样式 */
.action-card, .data-table-card {
  margin-bottom: 20px;
  border-radius: 10px; /* 稍微大一点的圆角 */
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08); /* 更明显的柔和阴影 */
  border: none; /* 移除默认边框 */
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 25px; /* 增加内边距 */
  border-bottom: 1px solid #ebeef5;
  margin-bottom: -1px;
  background-color: #fff; /* 确保头部背景是白色 */
  border-top-left-radius: 10px; /* 配合卡片圆角 */
  border-top-right-radius: 10px;
}
.card-header .el-button {
  margin-left: 20px; /* 调整上传按钮与单选组的间距 */
}

/* 新增的提示样式 */
.annotation-tip {
  margin-bottom: 20px; /* 与下方表格卡片保持间距 */
  border-radius: 8px; /* 提示框圆角 */
}

/* 表格样式 */
.el-table {
  --el-table-header-bg-color: #f8f9fb; /* 表头背景色更浅 */
  --el-table-header-text-color: #505050; /* 表头文字颜色更深 */
  --el-table-row-hover-bg-color: #f0f4f8; /* 行悬停背景色 */
  border-radius: 10px; /* 表格圆角 */
  overflow: hidden; /* 确保圆角生效 */
}

.el-table :deep(.el-table__header-wrapper) th {
  font-weight: bold; /* 表头字体加粗 */
  color: var(--el-table-header-text-color);
  background-color: var(--el-table-header-bg-color);
}

.el-table :deep(.el-table__cell) {
  padding: 12px 0; /* 调整单元格垂直内边距 */
}

/* 操作列按钮组的布局 */
.operation-buttons-group {
  display: flex;
  gap: 6px; /* 按钮之间的间距 */
  justify-content: center; /* 居中对齐按钮 */
  align-items: center;
}

/* 调整按钮大小和风格 */
.operation-buttons-group .el-button {
  padding: 6px 10px; /* 调整按钮内边距 */
  height: auto; /* 自动高度 */
  font-size: 13px; /* 调整字体大小 */
}
.operation-buttons-group .el-button.is-plain {
  border-color: #dcdfe6; /* 朴素按钮边框颜色 */
  color: #606266; /* 朴素按钮文字颜色 */
}
.operation-buttons-group .el-button.is-plain:hover {
  background-color: #ecf5ff;
  border-color: #1e6fff;
  color: #1e6fff;
}

/* 下拉菜单触发器按钮 */
.operation-buttons-group .el-dropdown .el-button.is-circle {
  width: 28px; /* 调整圆形按钮大小 */
  height: 28px;
  min-width: unset; /* 移除最小宽度限制 */
  padding: 0; /* 移除内边距 */
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 针对el-dropdown-item的样式调整 */
.el-dropdown-menu__item {
  font-size: 14px;
}

/* 上传对话框样式 */
/* 自定义拖拽区域样式，模仿 el-upload-dragger */
.custom-upload-drop-zone {
  border: 1px dashed var(--el-border-color);
  border-radius: var(--el-border-radius-base);
  box-sizing: border-box;
  width: 100%;
  height: 180px; /* 与 el-upload-dragger 类似的高度 */
  text-align: center;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: border-color var(--el-transition-duration-fast) ease-in-out;
}

.custom-upload-drop-zone:hover {
  border-color: var(--el-color-primary);
}

.custom-upload-drop-zone .el-icon--upload {
  font-size: 67px;
  color: var(--el-text-color-placeholder);
  margin-bottom: 16px;
}

.custom-upload-drop-zone .el-upload__text {
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.custom-upload-drop-zone .el-upload__text em {
  color: var(--el-color-primary);
  font-style: normal;
}

.custom-upload-drop-zone .el-upload__tip {
  margin-top: 10px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

/* 覆盖 el-upload-dragger 的样式，确保自定义区域看起来一致 */
.el-upload-dragger {
  padding: 20px; /* 增加拖拽区域内边距 */
}


/* 浏览对话框布局 */
.browse-content-wrapper {
  display: flex;
  height: 70vh; /* 确保容器有固定高度 */
  border: 1px solid #ebeef5; /* 添加边框 */
  border-radius: 8px;
  overflow: hidden; /* 确保子元素不溢出 */
  background-color: #fff;
}

.file-tree {
  flex-shrink: 0; /* 不收缩 */
  width: 300px; /* 固定宽度 */
  border-right: 1px solid #eee;
  padding-right: 10px;
  overflow-y: auto; /* 允许树形结构滚动 */
  padding: 15px; /* 树形结构内边距 */
}

.file-content-preview {
  flex-grow: 1; /* 占据剩余空间 */
  padding: 15px 20px; /* 预览区域内边距 */
  overflow-y: auto; /* 允许预览内容滚动 */
}

.custom-tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  font-size: 14px;
  padding-right: 8px;
}
.custom-tree-node .el-icon {
  color: #1e6fff;
}

.preview-image, .preview-text, .preview-other {
  margin-top: 15px;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 8px; /* 预览框圆角 */
  background-color: #fcfcfc;
}

.preview-image .el-image {
  display: block;
  margin: auto;
  border-radius: 4px; /* 图片圆角 */
}

.preview-text textarea {
  font-family: 'Consolas', 'Monaco', 'Andale Mono', 'Ubuntu Mono', monospace; /* 等宽字体，适合代码和文本 */
  font-size: 13px;
  line-height: 1.5;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  background-color: #f9f9f9;
}

/* 统一加载和错误提示样式 */
.browse-loading, .browse-error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  flex-direction: column;
  gap: 10px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
</style>
