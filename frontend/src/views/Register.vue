<template>
  <div class="register-page">
    <div class="register-bg" aria-hidden="true">
      <img src="/images/login-bg-industrial.jpg" alt="" />
      <div class="register-overlay"></div>
    </div>

    <main class="register-shell">
      <section class="register-card">
        <header class="brand">
          <img src="../assets/logo.svg" alt="平台标志" />
          <div>
            <h1>创建实训账号</h1>
            <p>工业视觉 AI 实训导师与智能质检平台</p>
          </div>
        </header>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleRegister"
        >
          <el-form-item label="用户名" prop="username">
            <el-input v-model.trim="form.username" :prefix-icon="User" placeholder="3-32 位字母、数字或下划线" size="large" />
          </el-form-item>

          <el-form-item label="邮箱" prop="email">
            <el-input v-model.trim="form.email" :prefix-icon="Message" placeholder="用于账号识别和通知" size="large" />
          </el-form-item>

          <div class="password-grid">
            <el-form-item label="密码" prop="password">
              <el-input v-model="form.password" :prefix-icon="Lock" type="password" show-password placeholder="至少 6 位" size="large" />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input v-model="form.confirmPassword" :prefix-icon="Lock" type="password" show-password placeholder="再次输入密码" size="large" />
            </el-form-item>
          </div>

          <div class="notification-row">
            <div>
              <strong>接收平台通知</strong>
              <span>接收实训任务与质检结果提醒</span>
            </div>
            <el-switch v-model="form.receive_notifications" />
          </div>

          <el-button class="register-button" type="primary" native-type="submit" :loading="loading">
            创建账号
          </el-button>
        </el-form>

        <footer>
          <span>已有账号？</span>
          <router-link to="/login">返回登录</router-link>
        </footer>
      </section>
    </main>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Lock, Message, User } from '@element-plus/icons-vue';
import { register } from '../api/auth';

const router = useRouter();
const formRef = ref();
const loading = ref(false);

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  receive_notifications: true,
});

const validateConfirmPassword = (_rule, value, callback) => {
  if (!value) callback(new Error('请再次输入密码'));
  else if (value !== form.password) callback(new Error('两次输入的密码不一致'));
  else callback();
};

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_]{3,32}$/, message: '仅支持 3-32 位字母、数字或下划线', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: ['blur', 'change'] },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 72, message: '密码长度应为 6-72 位', trigger: 'blur' },
  ],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: ['blur', 'change'] }],
};

const handleRegister = async () => {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await register({
      username: form.username,
      email: form.email,
      password: form.password,
      receive_notifications: form.receive_notifications,
    });
    ElMessage.success('注册成功，请使用新账号登录');
    await router.push({ name: 'Login', query: { username: form.username } });
  } catch (error) {
    const detail = error.response?.data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join('；')
      : detail;
    ElMessage.error(message || '注册失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.register-page {
  position: relative;
  min-height: 100dvh;
  overflow: hidden;
  background: #eef4fb;
}
.register-bg { position: fixed; inset: 0; }
.register-bg img { width: 100%; height: 100%; object-fit: cover; opacity: 0.34; filter: saturate(0.85); }
.register-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(245, 249, 255, 0.96), rgba(220, 234, 255, 0.78));
}
.register-shell {
  position: relative;
  z-index: 1;
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: 28px 20px;
}
.register-card {
  width: min(100%, 560px);
  padding: 32px;
  border: 1px solid rgba(30, 111, 255, 0.15);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(12px);
  box-shadow: 0 24px 60px rgba(15, 42, 68, 0.14);
}
.register-card::before {
  content: '';
  display: block;
  height: 1px;
  margin: -32px 20px 30px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.95), transparent);
}
.brand { display: flex; align-items: center; gap: 14px; margin-bottom: 24px; }
.brand img { width: 46px; height: 46px; }
.brand h1 { margin: 0; color: #0f2a44; font-size: 24px; letter-spacing: 0; }
.brand p { margin: 5px 0 0; color: #6b7c93; font-size: 13px; }
.password-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.register-card :deep(.el-form-item__label) { color: #314d69; font-weight: 600; }
.register-card :deep(.el-input__wrapper) {
  min-height: 44px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 0 0 1px rgba(30, 111, 255, 0.14) inset;
}
.notification-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 2px 0 20px;
  padding: 14px 16px;
  border: 1px solid rgba(30, 111, 255, 0.12);
  border-radius: 12px;
  background: rgba(238, 244, 251, 0.72);
}
.notification-row strong { display: block; color: #0f2a44; font-size: 14px; }
.notification-row span { display: block; margin-top: 3px; color: #71849a; font-size: 12px; }
.register-button {
  width: 100%;
  height: 46px;
  border: 0;
  border-radius: 12px;
  background: #1e6fff;
  box-shadow: 0 10px 24px rgba(30, 111, 255, 0.28);
  font-weight: 700;
}
footer { display: flex; justify-content: center; gap: 6px; margin-top: 18px; color: #71849a; font-size: 13px; }
footer a { color: #1e6fff; font-weight: 600; text-decoration: none; }
@media (max-width: 600px) {
  .register-card { padding: 24px 20px; }
  .register-card::before { margin: -24px 12px 24px; }
  .password-grid { grid-template-columns: 1fr; gap: 0; }
}
</style>
