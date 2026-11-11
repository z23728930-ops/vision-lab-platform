<template>
  <div class="dashboard-container">

    <!-- Hero banner -->
    <div class="hero-banner">
      <img :src="slides[0].src" :alt="slides[0].title" class="hero-img" />
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <h2 class="hero-title">{{ slides[0].title }}</h2>
        <p class="hero-desc">{{ slides[0].text }}</p>
      </div>
    </div>

    <!-- Stats row -->
    <div class="stats-row">
      <div v-for="stat in statCards" :key="stat.label" class="stat-card">
        <div class="stat-icon-wrap" :style="{ background: stat.iconBg }">
          <el-icon :style="{ color: stat.iconColor }"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-value" :class="{ 'is-loading': loadingStats }">
            <el-skeleton v-if="loadingStats" animated :rows="0" style="width:60px;display:inline-block" />
            <span v-else>{{ stat.value }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Welcome card -->
    <div class="welcome-card">
      <div class="welcome-glow"></div>
      <div class="welcome-content">
        <div class="welcome-text">
          <h3 class="welcome-title">欢迎回来，{{ userStore.userInfo?.username }}</h3>
          <p class="welcome-desc">系统概览已刷新，关键指标与实训入口随时可用。</p>
        </div>
        <div class="welcome-actions">
          <el-button type="primary" :icon="Upload" @click="goTo('Datasets')">上传数据集</el-button>
          <el-button v-if="userStore.isAdmin" :icon="User" @click="goTo('UserManagement')">用户管理</el-button>
        </div>
      </div>
      <div v-if="userStore.isAdmin" class="welcome-badge">
        <el-icon><Key /></el-icon>
        管理员
      </div>
    </div>

    <!-- Quick actions -->
    <div class="qa-section">
      <h3 class="qa-title">快捷操作</h3>
      <div class="qa-grid">
        <button class="qa-tile" @click="goTo('Datasets')">
          <div class="qa-icon-wrap" style="background:#e8f1ff">
            <el-icon style="color:#1e6fff;font-size:22px"><Upload /></el-icon>
          </div>
          <span class="qa-label">上传数据集</span>
        </button>
        <button class="qa-tile" @click="goTo('InferenceJobs')">
          <div class="qa-icon-wrap" style="background:#e8f7ef">
            <el-icon style="color:#2f9e6b;font-size:22px"><DataLine /></el-icon>
          </div>
          <span class="qa-label">查看推理任务</span>
        </button>
        <button class="qa-tile" @click="goTo('Hardware')">
          <div class="qa-icon-wrap" style="background:#fef5e7">
            <el-icon style="color:#c08000;font-size:22px"><VideoCamera /></el-icon>
          </div>
          <span class="qa-label">硬件控制</span>
        </button>
        <button class="qa-tile" @click="goTo('TrainingMentor')">
          <div class="qa-icon-wrap" style="background:#f0f0ff">
            <el-icon style="color:#5555e6;font-size:22px"><Reading /></el-icon>
          </div>
          <span class="qa-label">AI实训导师</span>
        </button>
        <button class="qa-tile" @click="goTo('IndustryCases')">
          <div class="qa-icon-wrap" style="background:#fff0f5">
            <el-icon style="color:#d05070;font-size:22px"><Collection /></el-icon>
          </div>
          <span class="qa-label">工业案例</span>
        </button>
        <button class="qa-tile" @click="goTo('AiAssistant')">
          <div class="qa-icon-wrap" style="background:#f0fff5">
            <el-icon style="color:#2f9e6b;font-size:22px"><ChatDotRound /></el-icon>
          </div>
          <span class="qa-label">AI质检助手</span>
        </button>
      </div>
    </div>

    <!-- Notifications -->
    <div class="notif-section">
      <h3 class="notif-title">系统通知</h3>
      <div class="notif-list">
        <el-empty v-if="notifications.length === 0" description="暂无新通知" :image-size="50" />
        <transition-group name="notif" tag="div" class="notif-inner">
          <el-alert
            v-for="(n, i) in notifications"
            :key="i"
            :title="n.title"
            :type="n.type"
            :description="n.description"
            show-icon
            :closable="true"
            @close="removeNotification(i)"
          />
        </transition-group>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '../store/user';
import { useCameraStore } from '../store/camera';
import { ElMessage, ElNotification } from 'element-plus';
import {
  Upload, VideoPlay, Camera, Setting, Collection, Monitor,
  DataLine, Reading, ChatDotRound, Key, User,
  Folder, Cpu, List, Finished, VideoCamera
} from '@element-plus/icons-vue';
import emitter from '../utils/eventBus.js';
import { fetchDatasets } from '../api/datasets';
import { fetchInferenceJobs } from '../api/inference';
import { fetchModels } from '../api/models';

const userStore = useUserStore();
const cameraStore = useCameraStore();
const router = useRouter();

const loadingStats = ref(false);
const stats = reactive({ totalDatasets: 0, totalModels: 0, runningJobs: 0, completedJobs: 0 });
const notifications = ref([]);

const slides = [
  { src: '/images/carousel-factory.jpg', title: '智能工厂 AI 视觉检测', text: '连接真实产线与视觉模型，完成智能质检实训闭环。' }
];

const statCards = computed(() => [
  { label: '实训项目数', value: stats.totalDatasets, icon: Collection, iconBg: '#e8f1ff', iconColor: '#1e6fff' },
  { label: '模型精度', value: stats.totalModels + ' 套', icon: Cpu, iconBg: '#e8f7ef', iconColor: '#2f9e6b' },
  { label: '检测记录', value: stats.runningJobs + stats.completedJobs, icon: List, iconBg: '#fef5e7', iconColor: '#c08000' },
  { label: '设备状态', value: cameraStore.isConnected ? '在线' : '离线', icon: Monitor, iconBg: '#f0f0ff', iconColor: '#1e6fff' },
]);

const goTo = (routeName) => router.push({ name: routeName });

const loadDashboardStats = async () => {
  loadingStats.value = true;
  try {
    const [ds, mo, jo] = await Promise.allSettled([
      fetchDatasets(),
      fetchModels(),
      fetchInferenceJobs(),
    ]);
    if (ds.status === 'fulfilled') stats.totalDatasets = ds.value.data.length;
    if (mo.status === 'fulfilled') stats.totalModels = mo.value.data.length;
    if (jo.status === 'fulfilled') {
      const jobs = jo.value.data;
      stats.runningJobs  = jobs.filter(j => j.status === 'running').length;
      stats.completedJobs = jobs.filter(j => j.status === 'completed').length;
    }
  } catch (e) {
    ElMessage.error('加载统计数据失败');
  } finally {
    loadingStats.value = false;
  }
};

const addNotification = (title, description, type = 'info') => {
  notifications.value.unshift({ title, description, type });
  if (notifications.value.length > 5) notifications.value.pop();
};

const removeNotification = (i) => notifications.value.splice(i, 1);

const handleGlobalEvent = (e) => {
  loadDashboardStats();
  if (!e?.type) return;
  const map = {
    'dataset-uploaded':        { t: 'success', title: '新数据集上传', desc: (n) => `数据集 "${n.name}" 已成功上传。` },
    'dataset-deleted':          { t: 'warning', title: '数据集已删除', desc: (n) => `数据集 "${n.name}" 已被删除。` },
    'inference-job-completed':  { t: 'success', title: '推理任务完成', desc: (n) => `任务 "${n.job_name}" 已成功完成。` },
    'inference-job-failed':     { t: 'error',   title: '推理任务失败', desc: (n) => `任务 "${n.job_name}" 执行失败。` },
    'model-uploaded':          { t: 'success', title: '新模型上传', desc: (n) => `模型 "${n.name}" 已成功上传。` },
  };
  const m = map[e.type];
  if (!m) return;
  addNotification(m.title, m.desc(e), m.t);
  if (e.type === 'inference-job-completed') {
    ElNotification({ title: '任务完成', message: m.desc(e), type: 'success', duration: 4500 });
  }
  if (e.type === 'inference-job-failed') {
    ElNotification({ title: '任务失败', message: m.desc(e), type: 'error', duration: 4500 });
  }
};

onMounted(() => {
  loadDashboardStats();
  emitter.on('system-update', handleGlobalEvent);
});
onUnmounted(() => {
  emitter.off('system-update', handleGlobalEvent);
});
</script>

<style scoped>
/* ─── Layout ─── */
.dashboard-container {
  padding: 0 4px 8px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ─── Hero ─── */
.hero-banner {
  position: relative;
  height: 340px;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 16px 40px rgba(15, 42, 68, 0.16);
}
.hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    rgba(11, 31, 53, 0.55) 0%,
    rgba(15, 42, 68, 0.30) 100%
  );
}
.hero-content {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 48px 40px 36px;
  color: #fff;
}
.hero-title {
  margin: 0 0 10px;
  font-size: 2rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.02em;
}
.hero-desc {
  margin: 0;
  font-size: 1rem;
  color: rgba(220, 235, 255, 0.88);
  max-width: 60ch;
}

/* ─── Stats ─── */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid rgba(30, 111, 255, 0.1);
  box-shadow: 0 2px 12px rgba(15, 42, 68, 0.06);
  transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1),
              box-shadow 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(30, 111, 255, 0.14);
}
.stat-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon-wrap .el-icon { font-size: 22px; }
.stat-body { min-width: 0; }
.stat-label { font-size: 0.8rem; color: #6b7c93; font-weight: 500; margin-bottom: 4px; }
.stat-value { font-size: 1.5rem; font-weight: 700; color: #0f2a44; font-variant-numeric: tabular-nums; }

/* ─── Welcome ─── */
.welcome-card {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  background: linear-gradient(135deg, #1e6fff 0%, #3d86ff 100%);
  border: none !important;
  box-shadow: 0 12px 36px rgba(30, 111, 255, 0.28);
}
.welcome-card:hover { transform: none; }
.welcome-glow {
  position: absolute;
  top: -40px;
  right: -40px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  filter: blur(40px);
  pointer-events: none;
}
.welcome-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 28px;
}
.welcome-text { flex: 1; min-width: 0; }
.welcome-title { margin: 0 0 6px; font-size: 1.25rem; font-weight: 700; color: #fff; }
.welcome-desc  { margin: 0; font-size: 0.9rem; color: rgba(220, 235, 255, 0.82); }
.welcome-actions { display: flex; gap: 10px; flex-shrink: 0; }
.welcome-actions .el-button {
  border-radius: 999px !important;
  font-weight: 600;
}
.welcome-actions .el-button--primary {
  background: rgba(255,255,255,0.18) !important;
  border-color: rgba(255,255,255,0.45) !important;
  color: #fff !important;
  box-shadow: none !important;
}
.welcome-actions .el-button--primary:hover {
  background: rgba(255,255,255,0.32) !important;
}
.welcome-badge {
  position: absolute;
  top: 16px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.78rem;
  font-weight: 700;
  color: rgba(255,255,255,0.75);
}

/* ─── Quick actions ─── */
.qa-section { }
.qa-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f2a44;
  margin: 0 0 14px;
}
.qa-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}
.qa-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 18px 12px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid rgba(30, 111, 255, 0.1);
  box-shadow: 0 2px 12px rgba(15, 42, 68, 0.06);
  cursor: pointer;
  transition:
    transform 0.22s cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 0.22s cubic-bezier(0.16, 1, 0.3, 1),
    border-color 0.2s ease;
  font-family: inherit;
  color: inherit;
}
.qa-tile:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(30, 111, 255, 0.14);
  border-color: rgba(30, 111, 255, 0.28);
}
.qa-tile:active { transform: scale(0.96); }
.qa-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.qa-label { font-size: 0.8rem; font-weight: 600; color: #0f2a44; text-align: center; }

/* ─── Notifications ─── */
.notif-section { }
.notif-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f2a44;
  margin: 0 0 14px;
}
.notif-list { }
.notif-inner { display: flex; flex-direction: column; gap: 8px; }
.notif-enter-active { transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.notif-leave-active { transition: all 0.25s ease; }
.notif-enter-from { opacity: 0; transform: translateY(-8px); }
.notif-leave-to  { opacity: 0; transform: translateX(12px); }

/* ─── Responsive ─── */
@media (max-width: 1100px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .qa-grid    { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 640px) {
  .stats-row { grid-template-columns: 1fr; }
  .qa-grid    { grid-template-columns: repeat(2, 1fr); }
  .hero-title { font-size: 1.5rem; }
  .hero-content { padding: 32px 20px 24px; }
  .welcome-content { flex-direction: column; align-items: flex-start; }
}
</style>
