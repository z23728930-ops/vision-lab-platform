<template>
  <div class="user-management-page">
    <el-card shadow="never" class="user-list-card">
      <template #header>
        <div class="card-header">
          <span>用户列表</span>
          <el-button type="primary" :icon="Plus" @click="handleAddUser">添加新用户</el-button>
        </div>
      </template>
      <el-table :data="users" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" show-overflow-tooltip /> <!-- 新增 -->
        <el-table-column prop="role" label="角色" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.role === 'admin' ? '' : 'success'">
              {{ scope.row.role }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="接收通知" width="100"> <!-- 新增 -->
          <template #default="scope">
            <el-switch v-model="scope.row.receive_notifications" disabled /> <!-- 暂时禁用，编辑时才允许修改 -->
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间">
          <template #default="scope">{{ new Date(scope.row.created_at).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180"> <!-- 调整宽度 -->
          <template #default="scope">
            <el-button
                size="small"
                :icon="Edit"
                @click="handleEditUser(scope.row)"
                :disabled="scope.row.id === userStore.userInfo?.id"
            >编辑</el-button> <!-- 新增编辑按钮 -->
            <el-button
                size="small"
                type="danger"
                :icon="Delete"
                @click="handleDeleteUser(scope.row)"
                :disabled="scope.row.id === userStore.userInfo?.id"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑用户对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="640px" top="8vh" class="user-edit-dialog" @close="resetForm">
      <div class="dialog-scroll-body">
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" :disabled="isEditMode && userForm.id === userStore.userInfo?.id" /> <!-- 管理员不能修改自己的用户名 -->
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="userForm.password" type="password" show-password placeholder="新增用户必填，编辑用户不修改请留空" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" placeholder="可选，用于接收通知" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" style="width: 100%;" :disabled="isEditMode && userForm.id === userStore.userInfo?.id"> <!-- 管理员不能修改自己的角色 -->
            <el-option label="user" value="user"></el-option>
            <el-option label="admin" value="admin"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="接收通知">
          <el-switch v-model="userForm.receive_notifications" />
        </el-form-item>
      </el-form>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="isSubmitting">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue';
import { useUserStore } from '../store/user';
import { fetchUsers, createUser, deleteUser, updateUserById } from '../api/users'; // 新增导入 updateUserById
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Delete, Edit } from '@element-plus/icons-vue'; // 新增导入 Edit 图标

const userStore = useUserStore();
const users = ref([]);
const loading = ref(false);
const dialogVisible = ref(false);
const isSubmitting = ref(false);
const userFormRef = ref(null);

const userForm = reactive({
  id: null, // 用于编辑模式
  username: '',
  password: '',
  email: '',
  role: 'user',
  receive_notifications: true,
});

const isEditMode = computed(() => userForm.id !== null);
const dialogTitle = computed(() => isEditMode.value ? '编辑用户' : '添加新用户');

const userRules = computed(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应在 3 到 20 个字符之间', trigger: 'blur' },
  ],
  password: [
    { required: !isEditMode.value, message: '请输入密码', trigger: 'blur' }, // 新增用户时密码必填
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' },
  ],
  email: [
    { type: 'email', message: '请输入有效的邮箱地址', trigger: ['blur', 'change'] },
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' },
  ],
}));

const getUsers = async () => {
  loading.value = true;
  try {
    const response = await fetchUsers();
    users.value = response.data;
  } catch (e) { ElMessage.error("获取用户列表失败"); }
  finally { loading.value = false; }
};

const handleAddUser = () => {
  // 重置表单为添加模式的默认值
  Object.assign(userForm, {
    id: null,
    username: '',
    password: '',
    email: '',
    role: 'user',
    receive_notifications: true,
  });
  dialogVisible.value = true;
};

const handleEditUser = (row) => {
  // 填充表单为编辑模式
  Object.assign(userForm, {
    id: row.id,
    username: row.username,
    email: row.email || '', // 确保 email 是字符串，避免 null
    role: row.role,
    receive_notifications: row.receive_notifications,
    password: '', // 编辑时不显示旧密码，让用户选择是否修改
  });
  dialogVisible.value = true;
};

const resetForm = () => { userFormRef.value?.resetFields(); };

const submitForm = async () => {
  await userFormRef.value.validate(async (valid) => {
    if (valid) {
      isSubmitting.value = true;
      try {
        const userData = {
          username: userForm.username,
          email: userForm.email === '' ? null : userForm.email, // 如果为空字符串，发送 null
          role: userForm.role,
          receive_notifications: userForm.receive_notifications,
        };

        if (userForm.password) { // 只有当用户输入了密码时才发送
          userData.password = userForm.password;
        }

        if (isEditMode.value) {
          await updateUserById(userForm.id, userData);
          ElMessage.success("用户更新成功！");
        } else {
          await createUser(userData);
          ElMessage.success("用户创建成功！");
        }
        dialogVisible.value = false;
        getUsers();
      } catch (e) { ElMessage.error(e.response?.data?.detail || "操作失败"); }
      finally { isSubmitting.value = false; }
    }
  });
};

const handleDeleteUser = (row) => {
  ElMessageBox.confirm(`确定要删除用户 "${row.username}" 吗？`, '警告', {
    type: 'warning'
  }).then(async () => {
    try {
      await deleteUser(row.id);
      ElMessage.success("删除成功");
      getUsers();
    } catch (e) { ElMessage.error(e.response?.data?.detail || "删除失败"); }
  }).catch(() => {});
};

onMounted(getUsers);
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-management-page {
  min-height: calc(100vh - 112px);
}

.user-list-card {
  min-height: calc(100vh - 112px);
}

.user-list-card :deep(.el-card__body) {
  min-height: calc(100vh - 210px);
}

.user-edit-dialog :deep(.el-dialog__body) {
  max-height: calc(80vh - 150px);
  min-height: 300px;
  overflow-y: auto;
  padding: 24px 36px 16px;
}

.user-edit-dialog :deep(.el-dialog__footer) {
  padding-top: 12px;
  border-top: 1px solid #edf2f7;
}

.user-edit-dialog :deep(.el-dialog__header) {
  padding: 24px 36px 16px;
  margin-right: 0;
}

.dialog-scroll-body {
  min-height: 0;
}

@media (max-height: 700px) {
  .user-edit-dialog :deep(.el-dialog__body) {
    max-height: calc(84vh - 150px);
    min-height: 240px;
  }
}

@media (max-width: 680px) {
  .user-edit-dialog {
    width: calc(100vw - 32px) !important;
  }

  .user-edit-dialog :deep(.el-dialog__header),
  .user-edit-dialog :deep(.el-dialog__body) {
    padding-left: 22px;
    padding-right: 22px;
  }
}
</style>
