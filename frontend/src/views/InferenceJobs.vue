<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>推理任务列表</span>
        </div>
      </template>
      <el-table :data="jobs" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="job_name" label="任务名称" />
        <el-table-column prop="source_dataset_id" label="源数据集ID" width="120" />
        <el-table-column prop="model_id" label="模型ID" width="100" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度">
          <template #default="scope">
            <el-progress v-if="scope.row.status === 'running'" :percentage="scope.row.results_summary?.progress || 0" />
            <span v-else-if="scope.row.status === 'completed'">100%</span>
            <span v-else>N/A</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="scope">
            <!-- 修正日期显示问题：使用 formatDateTime 辅助函数 -->
            <span v-if="scope.row.created_at">
              {{ formatDateTime(scope.row.created_at) }}
            </span>
            <span v-else>N/A</span>
          </template>
        </el-table-column>
        <el-table-column label="失败原因" min-width="220">
          <template #default="scope">
            <el-tooltip v-if="scope.row.status === 'failed' && failureReason(scope.row)" :content="failureReason(scope.row)" placement="top">
              <span class="failure-reason" @click="showFailureReason(scope.row)">{{ failureReason(scope.row) }}</span>
            </el-tooltip>
            <el-button v-if="scope.row.status === 'failed'" link type="danger" size="small" @click="showFailureReason(scope.row)">
              {{ failureReason(scope.row) ? '查看详情' : '暂无错误详情' }}
            </el-button>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="scope">
            <el-button size="small" :icon="View" @click="handleBrowse(scope.row)" :disabled="scope.row.status !== 'completed'">浏览</el-button>
            <!-- 下载功能通常涉及后端打包，此处仅作占位 -->
            <el-button size="small" :icon="Download" @click="handleDownload(scope.row)" :disabled="scope.row.status !== 'completed'">下载</el-button>
            <el-button size="small" type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="failureDialogVisible" title="推理任务失败原因" width="520px">
      <el-alert v-if="selectedFailureReason" title="任务执行失败" :description="selectedFailureReason" type="error" show-icon />
      <el-empty v-else description="后端没有保存具体错误信息。请重新执行任务并查看后端日志。" :image-size="70" />
      <template #footer><el-button @click="failureDialogVisible = false">关闭</el-button></template>
    </el-dialog>

    <!-- 浏览结果对话框 -->
    <el-dialog v-model="browseDialogVisible" class="browse-dialog" :title="`浏览结果: ${browsingJob?.job_name}`" fullscreen append-to-body>
      <div v-if="browsingError" class="browse-error">
        <el-alert title="加载图片失败" :description="browsingError" type="error" show-icon />
      </div>
      <div v-else-if="browsingLoading" class="browse-loading">
        <el-icon class="is-loading" :size="26"><Loading /></el-icon>
        <span>正在加载图片...</span>
      </div>
      <el-scrollbar v-else-if="browsedImages.length" height="70vh">
        <div class="image-grid">
          <div v-for="(image, index) in browsedImages" :key="index" class="image-item">
            <el-image
                :src="browsingBaseUrl + '/' + image"
                fit="contain"
                style="width: 100%; height: 180px;"
                :preview-src-list="browsedImages.map(img => browsingBaseUrl + '/' + img)"
                :initial-index="index"
                lazy
            /> <!-- 调整高度以匹配样式 -->
            <span class="image-name" :title="image">{{ image }}</span>
          </div>
        </div>
      </el-scrollbar>
      <el-empty v-else description="此推理任务没有找到结果图片"></el-empty>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="browseDialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { fetchInferenceJobs, fetchAllInferenceJobsForAdmin, fetchInferenceJob, deleteInferenceJob, browseInferenceResult, downloadInferenceResultBlob } from '../api/inference';
import { ElMessage, ElMessageBox } from 'element-plus';
import { View, Download, Delete, Loading } from '@element-plus/icons-vue';
import apiClient from '../api'; // 引入 apiClient 用于拼接 URL
import { useUserStore } from '../store/user';

const jobs = ref([]);
const loading = ref(false);
const userStore = useUserStore();
let pollInterval = null;

const browseDialogVisible = ref(false);
const browsingJob = ref(null);
const browsedImages = ref([]); // 存储图片文件名列表
const browsingBaseUrl = ref(''); // 存储图片的基础URL
const browsingLoading = ref(false); // 浏览对话框加载状态
const browsingError = ref(''); // 浏览对话框错误信息
const failureDialogVisible = ref(false);
const selectedFailureReason = ref('');

const failureReason = (job) => {
  const summary = job?.results_summary;
  if (!summary || typeof summary !== 'object') return '';
  return summary.error || summary.failure_reason || summary.message || '';
};

const showFailureReason = (job) => {
  selectedFailureReason.value = failureReason(job);
  failureDialogVisible.value = true;
};

// 新增：日期格式化辅助函数
const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) {
    return 'N/A'; // 处理 null 或空字符串
  }
  // 尝试将 "YYYY-MM-DD HH:MM:SS" 格式转换为 "YYYY-MM-DDTHH:MM:SS"
  // 这是因为 new Date() 对带 'T' 的 ISO 格式支持更好
  const isoFormattedStr = dateTimeStr.replace(' ', 'T');
  const date = new Date(isoFormattedStr);

  // 检查日期对象是否有效
  if (isNaN(date.getTime())) {
    return 'Invalid Date'; // 如果仍然无效，返回提示
  }

  // 使用 toLocaleString() 进行本地化格式显示
  // 您也可以自定义格式，例如：
  // return date.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  return date.toLocaleString();
};


const getJobs = async () => {
  loading.value = true;
  try {
    const response = userStore.isAdmin
      ? await fetchAllInferenceJobsForAdmin()
      : await fetchInferenceJobs();
    jobs.value = response.data;
    startPolling(); // 初始获取后开始轮询
  } catch (e) {
    ElMessage.error("获取任务列表失败");
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const pollRunningJobs = async () => {
  if (userStore.isAdmin) {
    try {
      const response = await fetchAllInferenceJobsForAdmin();
      jobs.value = response.data;
    } catch (e) {
      console.error('Polling all inference jobs failed:', e);
    }
    return;
  }
  // 仅当存在正在运行的任务时才进行轮询
  const runningJobs = jobs.value.filter(job => job.status === 'running');
  if (runningJobs.length === 0) {
    // 如果没有正在运行的任务，则停止轮询
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    return;
  }

  for (const job of runningJobs) {
    try {
      const response = await fetchInferenceJob(job.id);
      const updatedJob = response.data;
      // 在原列表中更新任务，以保持响应式
      const index = jobs.value.findIndex(j => j.id === updatedJob.id);
      if (index !== -1) {
        // 使用 Object.assign 更新对象，保持引用，确保 Vue 响应式更新
        Object.assign(jobs.value[index], updatedJob);

        // 如果任务刚刚完成或失败，刷新整个列表以确保状态最新
        if (updatedJob.status === 'completed' || updatedJob.status === 'failed') {
          await getJobs(); // 重新获取所有任务，包括已完成/失败的
          return; // 刷新后，当前轮询周期结束
        }
      }
    } catch (e) {
      console.error(`Polling job ${job.id} failed:`, e);
    }
  }
};

const startPolling = () => {
  if (pollInterval) clearInterval(pollInterval); // 清除任何现有间隔
  // 首次调用立即执行一次，然后每3秒轮询
  pollRunningJobs();
  pollInterval = setInterval(pollRunningJobs, 3000);
};

const statusTagType = (status) => {
  if (status === 'completed') return 'success';
  if (status === 'running') return 'primary';
  if (status === 'failed') return 'danger';
  return 'info';
};

const handleDelete = async (row) => {
  ElMessageBox.confirm(
      `确定要删除推理任务 "${row.job_name}" 吗？这将同时删除所有结果文件。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
  )
      .then(async () => {
        try {
          await deleteInferenceJob(row.id);
          ElMessage.success("推理任务删除成功！");
          getJobs(); // 刷新列表
        } catch (e) {
          ElMessage.error("删除失败！");
          console.error(e);
        }
      })
      .catch(() => {
        ElMessage.info("取消删除");
      });
};

// --- 修改：处理下载功能 ---
const handleDownload = async (row) => {
  if (row.status !== 'completed') {
    ElMessage.warning('任务未完成，无法下载。');
    return;
  }
  try {
    ElMessage.info(`正在准备下载推理结果 '${row.job_name}'...`);
    const blob = await downloadInferenceResultBlob(row.id); // <-- 调用新的 API 函数
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${row.job_name.replace(/\s/g, '_')}_results.zip`; // 确保文件名有效
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


const handleBrowse = async (row) => {
  if (row.status !== 'completed') {
    ElMessage.warning('任务未完成，无法浏览结果。');
    return;
  }

  browsingJob.value = row;
  browsedImages.value = [];
  browsingBaseUrl.value = '';
  browsingError.value = '';
  browseDialogVisible.value = true;
  browsingLoading.value = true; // 开始加载

  try {
    const response = await browseInferenceResult(row.id);
    browsedImages.value = response.data.images;

    // --- 优化：构建完整的图片基础URL ---
    // apiClient 使用相对代理地址（/api/v1）时不能直接 new URL；
    // 结果静态资源与当前前端页面同源，直接使用 origin 更可靠。
    browsingBaseUrl.value = window.location.origin + response.data.base_url;

  } catch (error) {
    console.error("获取推理结果失败！", error);
    browsingError.value = error.response?.data?.detail || "无法获取图片列表。";
    browsedImages.value = [];
  } finally {
    browsingLoading.value = false; // 停止加载
  }
};

onMounted(() => {
  getJobs();
});

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval);
});
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 浏览对话框样式 */
.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); /* 稍微调整列宽 */
  gap: 15px;
}
.image-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 10px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05); /* 添加一点阴影 */
}
.el-image {
  width: 100%; /* 宽度占满父容器 */
  height: 180px; /* 固定高度 */
  object-fit: contain; /* 确保图片内容完整显示 */
  background-color: #f5f7fa; /* 图片加载前的背景色 */
}
.image-name {
  margin-top: 8px;
  font-size: 13px; /* 字体稍微大一点 */
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  text-align: center;
}
.browse-loading, .browse-error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px; /* 固定高度 */
  flex-direction: column;
  gap: 10px;
}
.failure-reason {
  display: inline-block;
  max-width: 180px;
  overflow: hidden;
  color: #d93025;
  cursor: pointer;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}
.muted { color: #9aa7b8; }
.browse-dialog :deep(.el-dialog__body) { height: calc(100vh - 120px); overflow: auto; padding: 16px 24px; box-sizing: border-box; }
.browse-dialog :deep(.el-scrollbar) { height: 100% !important; }
.browse-dialog :deep(.el-dialog__header) { padding-bottom: 10px; }
.browse-dialog :deep(.el-dialog__footer) { padding-top: 10px; }
</style>
