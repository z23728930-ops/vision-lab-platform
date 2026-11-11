<template>
  <div>
    <el-card> <!-- 移除 shadow="never"，改为通过CSS控制阴影 -->
      <template #header>
        <div class="card-header">
          <el-icon><Setting /></el-icon> <!-- 新增：设置图标 -->
          <span>个人设置</span>
        </div>
      </template>
      <el-form
          ref="userSettingsFormRef"
          :model="userForm"
          :rules="userRules"
          label-width="120px"
          style="max-width: 650px;"
      >
      <el-form-item label="用户名" prop="username">
        <el-input v-model="userForm.username" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="userForm.email" placeholder="用于接收任务通知，可选" /> <!-- 优化 placeholder -->
      </el-form-item>
      <el-form-item label="新密码" prop="newPassword">
        <el-input v-model="userForm.newPassword" type="password" show-password placeholder="不修改请留空" />
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirmPassword">
        <el-input v-model="userForm.confirmPassword" type="password" show-password placeholder="不修改请留空" />
      </el-form-item>
      <el-form-item label="接收邮件通知">
        <el-switch v-model="userForm.receive_notifications" />
        <span class="notification-hint">是否接收任务完成/失败的邮件通知</span> <!-- 添加类名 -->
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="submitForm" :loading="isSubmitting">保存更改</el-button>
      </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useUserStore } from '../store/user';
import { ElMessage } from 'element-plus';
import { Setting } from '@element-plus/icons-vue'; // 新增：导入 Setting 图标

const userStore = useUserStore();
const userSettingsFormRef = ref(null);
const isSubmitting = ref(false);

const userForm = reactive({
  username: '',
  email: '',
  newPassword: '',
  confirmPassword: '',
  receive_notifications: true,
});

// 验证规则
const userRules = reactive({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应在 3 到 20 个字符之间', trigger: 'blur' },
  ],
  email: [
    { type: 'email', message: '请输入有效的邮箱地址', trigger: ['blur', 'change'] },
  ],
  newPassword: [
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== '' && userForm.confirmPassword !== '' && value !== userForm.confirmPassword) {
          callback(new Error('两次输入的密码不一致！'));
        } else {
          callback();
        }
      },
      trigger: 'blur',
    },
  ],
  confirmPassword: [
    {
      validator: (rule, value, callback) => {
        if (value !== '' && userForm.newPassword !== '' && value !== userForm.newPassword) {
          callback(new Error('两次输入的密码不一致！'));
        } else {
          callback();
        }
      },
      trigger: 'blur',
    },
  ],
});

// 初始化表单数据
onMounted(() => {
  if (userStore.userInfo) {
    userForm.username = userStore.userInfo.username;
    userForm.email = userStore.userInfo.email || '';
    userForm.receive_notifications = userStore.userInfo.receive_notifications;
  } else {
    // 如果 userInfo 尚未加载，则尝试获取
    userStore.getUserInfo().then(() => {
      if (userStore.userInfo) {
        userForm.username = userStore.userInfo.username;
        userForm.email = userStore.userInfo.email || '';
        userForm.receive_notifications = userStore.userInfo.receive_notifications;
      }
    });
  }
});

const submitForm = async () => {
  if (!userSettingsFormRef.value) return;
  await userSettingsFormRef.value.validate(async (valid) => {
    if (valid) {
      isSubmitting.value = true;
      try {
        const updateData = {
          username: userForm.username,
          email: userForm.email === '' ? null : userForm.email, // 如果为空字符串，发送 null
          receive_notifications: userForm.receive_notifications,
        };

        if (userForm.newPassword) {
          updateData.password = userForm.newPassword;
        }

        await userStore.updateUserInfo(updateData); // 调用 store 中的 action

        // 清空密码输入框
        userForm.newPassword = '';
        userForm.confirmPassword = '';

      } catch (error) {
        // 错误信息已在 store 中处理
      } finally {
        isSubmitting.value = false;
      }
    }
  });
};
</script>

<style scoped>
/* 调整卡片整体样式，使其更居中且有更多呼吸空间 */
.el-card {
  margin: 30px auto; /* 上下外边距30px，左右自动居中 */
  max-width: 700px; /* 增加卡片最大宽度 */
  border-radius: 8px; /* 轻微圆角 */
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.08); /* 柔和的阴影 */
  border: none; /* 移除默认边框，让阴影更突出 */
}

/* 卡片头部样式 */
.card-header {
  display: flex; /* 使图标和文本水平对齐 */
  align-items: center; /* 垂直居中对齐 */
  font-size: 22px; /* 更大的标题字体 */
  font-weight: bold;
  color: #333; /* 更深的文本颜色 */
  padding-bottom: 15px; /* 增加底部内边距 */
  border-bottom: 1px solid #ebeef5; /* 添加底部边框作为分隔线 */
  margin-bottom: 25px; /* 标题与表单之间间距 */
}

.card-header .el-icon {
  margin-right: 10px; /* 图标与文本的间距 */
  font-size: 24px; /* 图标大小 */
  color: #1e6fff;
}

/* 调整表单项间距 */
.el-form-item {
  margin-bottom: 25px; /* 增加表单项之间的间距 */
}

/* 统一输入框高度 */
.el-input {
  height: 40px; /* 统一输入框高度，使其更舒适 */
}

/* 接收邮件通知的辅助文本样式 */
.notification-hint {
  margin-left: 10px;
  color: #909399; /* 提示文本颜色 */
  font-size: 13px; /* 稍微小一点的字体 */
  line-height: 1.5; /* 优化行高 */
}

/* 确保 el-switch 和旁边的文本垂直对齐 */
.el-form-item__content {
  display: flex;
  align-items: center;
}

/* 保存按钮样式 */
.el-form-item .el-button {
  margin-top: 15px; /* 按钮与上方元素的间距 */
  width: 140px; /* 按钮宽度 */
  height: 44px; /* 按钮高度 */
  font-size: 16px; /* 按钮字体大小 */
  border-radius: 6px; /* 按钮圆角 */
  letter-spacing: 1px; /* 增加字母间距，提升美感 */
}
</style>