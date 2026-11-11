<template>
  <div class="page">
    <div class="assistant-card">
      <!-- Header -->
      <div class="card-head">
        <div class="card-title">AI质检助手</div>
        <div class="card-subtitle">输入质检需求，助手帮你规划推理任务</div>
      </div>

      <!-- Hint -->
      <div class="hint-card">
        <el-icon style="color:#1e6fff;flex-shrink:0"><InfoFilled /></el-icon>
        <span>试试输入：使用 qk 模型检测 qk 数据集，置信度设为 0.6（当前示例数据和模型已验证可用）</span>
      </div>

      <!-- Messages -->
      <div class="messages">
        <div v-if="messages.length === 0" class="messages-empty">
          <el-icon class="empty-icon"><ChatDotRound /></el-icon>
          <p>发送消息开始对话</p>
        </div>
        <transition-group name="msg" tag="div" class="messages-list">
          <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
            <div class="msg-avatar">
              <el-avatar size="22" :icon="m.role === 'user' ? UserFilled : ChatLineSquare" />
            </div>
            <div class="msg-bubble">
              <div class="msg-label">{{ m.role === 'user' ? '我' : '助手' }}</div>
              <div class="msg-text">{{ m.text }}</div>
            </div>
          </div>
        </transition-group>
      </div>

      <!-- Input -->
      <div class="input-row">
        <el-input
          v-model="input"
          type="textarea"
          :rows="3"
          placeholder="输入质检需求，例如：使用 qk 模型检测 qk 数据集"
          resize="none"
          @keyup.ctrl.enter="send"
        />
        <div class="input-actions">
          <el-button @click="clear" :disabled="messages.length === 0">清空</el-button>
          <el-button type="primary" :loading="sending" @click="send" :disabled="!input.trim()">发送</el-button>
        </div>
      </div>

      <!-- Job status -->
      <template v-if="job">
        <el-divider />
        <div class="job-block">
          <el-alert
            :title="`任务 ${job.id}：${statusText(job.status)}`"
            :type="job.status === 'failed' ? 'error' : job.status === 'completed' ? 'success' : 'info'"
            show-icon
          />
          <div class="job-actions">
            <el-button size="small" @click="refreshJob">刷新状态</el-button>
            <el-button v-if="job?.status === 'completed'" size="small" type="primary" plain @click="downloadReport">
              下载CSV报告
            </el-button>
            <el-button v-if="job?.status === 'completed'" size="small" plain @click="loadReport">
              查看结构化报告
            </el-button>
          </div>
        </div>
      </template>

      <!-- Stats -->
      <template v-if="stats">
        <el-divider />
        <div class="stats-block">
          <div class="stats-title">检测摘要</div>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-val">{{ stats.images_processed }}</div>
              <div class="stat-key">已处理图片</div>
            </div>
            <div class="stat-item">
              <div class="stat-val">{{ stats.result_image_count }}</div>
              <div class="stat-key">结果图片</div>
            </div>
            <div class="stat-item">
              <div class="stat-val">{{ stats.progress }}%</div>
              <div class="stat-key">进度</div>
            </div>
            <div v-if="stats.error" class="stat-item stat-error">
              <div class="stat-val">{{ stats.error }}</div>
              <div class="stat-key">失败原因</div>
            </div>
          </div>
        </div>
      </template>

      <!-- Report -->
      <template v-if="report">
        <el-divider />
        <div class="report-block">
          <div class="report-title">结构化报告：{{ report.job_name }}</div>
          <div class="report-status">任务状态：{{ statusText(report.status) }}</div>
          <div class="report-files">
            <div class="files-label">结果文件（ {{ report.result_files.length }} ）</div>
            <div class="files-list">
              <el-tag v-for="f in report.result_files.slice(0, 20)" :key="f.relative_path" size="small" effect="plain">{{ f.name }}</el-tag>
            </div>
          </div>
        </div>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue';
import { ElMessage } from 'element-plus';
import { ChatDotRound, ChatLineSquare, UserFilled, InfoFilled } from '@element-plus/icons-vue';
import {
  sendAssistantMessage,
  fetchAssistantJobStatus,
  fetchAssistantJobStats,
  downloadAssistantReport,
  fetchAssistantReportJson
} from '../api/assistant';

const input = ref('');
const sending = ref(false);
const messages = ref([]);
const job = ref(null);
const stats = ref(null);
const report = ref(null);
let timer = null;

const statusText = (s) => ({ pending: '等待执行', running: '正在推理', completed: '已完成', failed: '失败' }[s] || s);

async function send() {
  if (!input.value.trim() || sending.value) return;
  const text = input.value.trim();
  messages.value.push({ role: 'user', text });
  input.value = '';
  sending.value = true;
  try {
    const { data } = await sendAssistantMessage(text);
    messages.value.push({ role: 'assistant', text: data.reply });
    if (data.job_id) {
      job.value = { id: data.job_id, status: data.status };
      startPolling();
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '助手请求失败');
  } finally {
    sending.value = false;
  }
}

async function refreshJob() {
  if (!job.value) return;
  try {
    const { data } = await fetchAssistantJobStatus(job.value.id);
    job.value = data;
    const s = await fetchAssistantJobStats(job.value.id);
    stats.value = s.data;
  } catch {
    ElMessage.error('无法获取任务状态');
  }
}

function startPolling() {
  clearInterval(timer);
  timer = setInterval(async () => {
    await refreshJob();
    if (['completed', 'failed'].includes(job.value?.status)) clearInterval(timer);
  }, 2000);
}

function clear() {
  messages.value = [];
  job.value = null;
  stats.value = null;
  report.value = null;
  clearInterval(timer);
}

async function loadReport() {
  try {
    report.value = (await fetchAssistantReportJson(job.value.id)).data;
  } catch {
    ElMessage.error('结构化报告读取失败');
  }
}

async function downloadReport() {
  try {
    const blob = await downloadAssistantReport(job.value.id);
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `inference_${job.value.id}_report.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch {
    ElMessage.error('报告下载失败');
  }
}

onBeforeUnmount(() => clearInterval(timer));
</script>

<style scoped>
.page { padding: 20px 24px; background: var(--color-bg); min-height: 100%; }

.assistant-card {
  background: #fff;
  border-radius: 20px;
  border: 1px solid rgba(30, 111, 255, 0.1);
  box-shadow: 0 2px 12px rgba(15, 42, 68, 0.07);
  padding: 28px 32px;
  max-width: 960px;
  margin: 0 auto;
}

.card-head { margin-bottom: 20px; }
.card-title { font-size: 1.375rem; font-weight: 700; color: #0f2a44; letter-spacing: -0.01em; margin-bottom: 4px; }
.card-subtitle { font-size: 0.85rem; color: #6b7c93; }

/* Hint */
.hint-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 12px;
  background: #e8f1ff;
  border: 1px solid rgba(30, 111, 255, 0.15);
  font-size: 0.82rem;
  color: #4a607a;
  margin-bottom: 20px;
}

/* Messages */
.messages {
  min-height: 280px;
  max-height: 380px;
  overflow-y: auto;
  margin-bottom: 16px;
  background: #f0f6ff;
  border-radius: 16px;
  padding: 16px;
}
.messages-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 260px;
  gap: 10px;
  color: #9bafc8;
}
.empty-icon { font-size: 36px; }
.messages-list { display: flex; flex-direction: column; gap: 12px; }

.msg { display: flex; gap: 10px; align-items: flex-start; }
.msg.user { flex-direction: row-reverse; }
.msg-avatar { flex-shrink: 0; }
.msg.user .msg-avatar .el-avatar { background: #1e6fff; }
.msg.assistant .msg-avatar .el-avatar { background: #2f9e6b; }
.msg-bubble {
  max-width: 76%;
  padding: 10px 14px;
  border-radius: 14px;
  line-height: 1.6;
}
.msg.user .msg-bubble { background: #1e6fff; color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .msg-bubble { background: #fff; color: #0f2a44; border-bottom-left-radius: 4px; box-shadow: 0 1px 6px rgba(15,42,68,0.08); }
.msg-label { font-size: 0.72rem; font-weight: 700; opacity: 0.6; margin-bottom: 3px; text-transform: uppercase; letter-spacing: 0.06em; }
.msg-text { white-space: pre-wrap; font-size: 0.875rem; }

/* Transitions */
.msg-enter-active { transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.msg-enter-from { opacity: 0; transform: translateY(8px); }

/* Input */
.input-row { }
.input-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px; }

/* Job */
.job-block { display: flex; flex-direction: column; gap: 12px; }
.job-actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* Stats */
.stats-block { }
.stats-title { font-size: 0.9rem; font-weight: 700; color: #0f2a44; margin-bottom: 14px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stat-item {
  background: #f0f6ff;
  border-radius: 12px;
  padding: 14px 16px;
  text-align: center;
}
.stat-val { font-size: 1.5rem; font-weight: 700; color: #0f2a44; font-variant-numeric: tabular-nums; margin-bottom: 3px; }
.stat-key { font-size: 0.75rem; color: #6b7c93; font-weight: 500; }
.stat-error .stat-val { font-size: 0.875rem; color: #e85d5d; }

/* Report */
.report-block { }
.report-title { font-size: 0.9rem; font-weight: 700; color: #0f2a44; margin-bottom: 6px; }
.report-status { font-size: 0.82rem; color: #6b7c93; margin-bottom: 12px; }
.files-label { font-size: 0.78rem; font-weight: 600; color: #6b7c93; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.06em; }
.files-list { display: flex; flex-wrap: wrap; gap: 6px; }
</style>
