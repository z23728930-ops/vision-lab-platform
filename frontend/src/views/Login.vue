<template>
  <div class="login-page" @scroll.passive="onScroll">

    <!-- Background layer -->
    <div class="login-bg" :style="{ transform: `translateY(${scrollY * 0.28}px) scale(1.08)` }">
      <img src="/images/login-bg-industrial.jpg" alt="" class="login-scene" />
      <div class="login-gradient"></div>
      <div class="orb orb-a"></div>
      <div class="orb orb-b"></div>
      <div class="orb orb-c"></div>
    </div>

    <!-- Cards stack -->
    <div class="login-shell" :style="{ transform: `translateY(${scrollY * -0.08}px)` }">
      <!-- Layered glass panels -->
      <div class="glass-layer layer-3"></div>
      <div class="glass-layer layer-2"></div>
      <div class="glass-layer layer-1"></div>
      <div class="float-card float-left"></div>
      <div class="float-card float-right"></div>

      <!-- Main card -->
      <div class="login-card">
        <!-- Brand -->
        <div class="brand">
          <img src="../assets/logo.svg" alt="logo" class="brand-logo" />
          <div>
            <h1>工业视觉智能质检平台</h1>
            <p>面向智能制造人才培养的工业视觉 AI 实训导师</p>
          </div>
        </div>

        <!-- Form -->
        <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" @submit.prevent="handleLogin">
          <div class="field">
            <label class="field-label">用户名</label>
            <el-input
              v-model="loginForm.username"
              placeholder="输入用户名"
              size="large"
              :prefix-icon="UserIcon"
            />
          </div>
          <div class="field">
            <label class="field-label">密码</label>
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="输入密码"
              show-password
              size="large"
              :prefix-icon="LockIcon"
            />
          </div>
          <el-button
            type="primary"
            native-type="submit"
            class="login-btn"
            size="large"
            :loading="loading"
          >
            登 录
          </el-button>
          <div class="register-entry">
            <span>还没有账号？</span>
            <router-link to="/register">创建普通用户账号</router-link>
          </div>
        </el-form>
      </div>
    </div>

    <!-- Feature strip -->
    <div class="feature-strip">
      <div class="feature-card">
        <div class="feature-dot" style="background:#1e6fff"></div>
        <div>
          <div class="feature-title">智能工厂视觉检测</div>
          <div class="feature-desc">产线采集、缺陷标注、模型推理与质检报告形成完整实训闭环。</div>
        </div>
      </div>
      <div class="feature-card">
        <div class="feature-dot" style="background:#2f9e6b"></div>
        <div>
          <div class="feature-title">教学导向的工业场景</div>
          <div class="feature-desc">覆盖 PCB、金属零件、包装检测等典型智能制造质检任务。</div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useUserStore } from '../store/user';
import { ElMessage } from 'element-plus';
import { User, Lock } from '@element-plus/icons-vue';

const UserIcon = User;
const LockIcon = Lock;
const route = useRoute();
const userStore = useUserStore();
const loginFormRef = ref(null);
const loading = ref(false);
const scrollY = ref(0);

const loginForm = reactive({
  username: typeof route.query.username === 'string' ? route.query.username : '',
  password: '',
});

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
};

const onScroll = (e) => {
  scrollY.value = e.target.scrollTop || 0;
};

const handleLogin = async () => {
  if (!loginFormRef.value) return;
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        await userStore.login(loginForm.username, loginForm.password);
        ElMessage.success('登录成功');
      } catch (error) {
        let msg = error.response?.data?.detail || error.message;
        if (msg === 'Incorrect username or password') msg = '用户名或密码不正确';
        else if (msg === 'Network Error') msg = '网络连接失败，请检查网络';
        ElMessage.error(msg || '登录失败，请重试');
      } finally {
        loading.value = false;
      }
    }
  });
};
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100dvh;
  overflow: auto;
  background: linear-gradient(160deg, #f0f6ff 0%, #e0ebff 48%, #d4e4ff 100%);
}

/* Background */
.login-bg {
  position: fixed;
  inset: -8%;
  z-index: 0;
  will-change: transform;
}
.login-scene {
  position: absolute;
  right: -6%;
  top: 8%;
  width: 62%;
  height: 84%;
  object-fit: cover;
  border-radius: 32px;
  filter: blur(2px) saturate(0.92);
  opacity: 0.40;
}
.login-gradient {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 22%, rgba(30, 111, 255, 0.16), transparent 28%),
    radial-gradient(circle at 82% 78%, rgba(61, 134, 255, 0.12), transparent 32%),
    linear-gradient(180deg, rgba(240, 246, 255, 0.58), rgba(228, 235, 255, 0.72));
}
.orb {
  position: absolute;
  border-radius: 50%;
  background: rgba(30, 111, 255, 0.18);
  filter: blur(8px);
}
.orb-a { width: 180px; height: 180px; left: 10%; top: 18%; }
.orb-b { width: 90px; height: 90px; right: 18%; top: 16%; background: rgba(255, 255, 255, 0.55); }
.orb-c { width: 140px; height: 140px; left: 28%; bottom: 12%; }

/* Shell */
.login-shell {
  position: relative;
  z-index: 1;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 64px 24px 24px;
  will-change: transform;
}

/* Layered glass */
.glass-layer {
  position: absolute;
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 24px 60px rgba(15, 42, 68, 0.08);
  pointer-events: none;
}
.layer-1 { width: min(92vw, 920px); height: 460px; }
.layer-2 { width: min(86vw, 860px); height: 500px; transform: rotate(-2deg); opacity: 0.65; }
.layer-3 { width: min(80vw, 800px); height: 540px; transform: rotate(3deg); opacity: 0.40; }

.float-card {
  position: absolute;
  width: 140px;
  height: 140px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.35);
  border: 1px solid rgba(30, 111, 255, 0.15);
  backdrop-filter: blur(12px);
}
.float-left { left: calc(50% - 480px); top: 18%; }
.float-right { right: calc(50% - 470px); bottom: 20%; width: 160px; height: 120px; }

/* Card */
.login-card {
  position: relative;
  z-index: 2;
  width: min(92vw, 440px);
  padding: 36px 36px 28px;
  border-radius: 24px !important;
  background: rgba(255, 255, 255, 0.62) !important;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(30, 111, 255, 0.15) !important;
  box-shadow: 0 24px 60px rgba(15, 42, 68, 0.12);
}
.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 28px;
  right: 28px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.95), transparent);
}

/* Brand */
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 28px;
}
.brand-logo {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
}
.brand h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #0f2a44;
  letter-spacing: -0.01em;
}
.brand p {
  margin: 5px 0 0;
  font-size: 12px;
  color: #6b7c93;
}

/* Fields */
.field {
  margin-bottom: 16px;
}
.field-label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  color: #4a607a;
  margin-bottom: 7px;
  letter-spacing: 0.02em;
}
.login-card :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.88) !important;
  border-radius: 12px !important;
  box-shadow: 0 0 0 1px rgba(30, 111, 255, 0.12) inset !important;
  transition: box-shadow 0.2s ease !important;
}
.login-card :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 2px rgba(30, 111, 255, 0.3) inset !important;
}
.login-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(30, 111, 255, 0.55) inset !important;
}
.login-card :deep(.el-input__inner) {
  color: #0f2a44 !important;
}
.login-card :deep(.el-input__inner::placeholder) {
  color: #9bafc8 !important;
}

/* Button */
.login-btn {
  width: 100%;
  height: 46px;
  margin-top: 8px;
  border: none !important;
  border-radius: 24px !important;
  background: linear-gradient(90deg, #1e6fff, #3d86ff) !important;
  box-shadow: 0 8px 22px rgba(30, 111, 255, 0.28);
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.04em;
  transition:
    background 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.15s ease;
}
.login-btn:hover {
  background: linear-gradient(90deg, #1558d6, #1e6fff) !important;
  box-shadow: 0 12px 28px rgba(30, 111, 255, 0.38);
}
.login-btn:active { transform: scale(0.97); }
.register-entry {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 16px;
  color: #6b7c93;
  font-size: 13px;
}
.register-entry a {
  color: #1e6fff;
  font-weight: 600;
  text-decoration: none;
}
.register-entry a:hover { color: #1558d6; }

/* Feature strip */
.feature-strip {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  max-width: 920px;
  margin: 0 auto 80px;
  padding: 0 24px 40px;
}
.feature-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 20px 22px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(30, 111, 255, 0.12);
  backdrop-filter: blur(12px);
}
.feature-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
.feature-title { font-size: 0.875rem; font-weight: 700; color: #0f2a44; margin-bottom: 4px; }
.feature-desc  { font-size: 0.8rem; color: #6b7c93; line-height: 1.6; margin: 0; }

@media (max-width: 960px) {
  .login-scene { width: 100%; right: 0; opacity: 0.26; }
  .float-card { display: none; }
  .feature-strip { grid-template-columns: 1fr; }
  .layer-2, .layer-3 { display: none; }
}
</style>
