<template>
  <el-container class="layout">
    <!-- Sidebar -->
    <el-aside :width="collapsed ? '72px' : '220px'" class="sidebar">
      <!-- Logo -->
      <div class="logo">
        <img src="../assets/logo.svg" class="logo-img" alt="logo" />
        <span v-if="!collapsed" class="logo-text">工业视觉质检</span>
      </div>
      <!-- Nav -->
      <el-menu
        :default-active="activeMenu"
        class="nav"
        :collapse="collapsed"
        background-color="#0F2A44"
        text-color="rgba(214,228,245,0.70)"
        active-text-color="#ffffff"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>系统总览</template>
        </el-menu-item>
        <el-menu-item index="/hardware">
          <el-icon><VideoCamera /></el-icon>
          <template #title>硬件控制</template>
        </el-menu-item>
        <el-menu-item index="/datasets">
          <el-icon><Folder /></el-icon>
          <template #title>数据管理</template>
        </el-menu-item>
        <el-menu-item index="/models">
          <el-icon><Cpu /></el-icon>
          <template #title>模型管理</template>
        </el-menu-item>
        <el-menu-item index="/training-mentor">
          <el-icon><Reading /></el-icon>
          <template #title>AI实训导师</template>
        </el-menu-item>
        <el-menu-item index="/industry-cases">
          <el-icon><Collection /></el-icon>
          <template #title>工业场景案例</template>
        </el-menu-item>
        <el-menu-item index="/feedback">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>用户评价</template>
        </el-menu-item>
        <el-menu-item index="/assistant">
          <el-icon><ChatLineSquare /></el-icon>
          <template #title>AI质检助手</template>
        </el-menu-item>
        <el-sub-menu index="/inference">
          <template #title>
            <el-icon><Operation /></el-icon>
            <span>推理中心</span>
          </template>
          <el-menu-item index="/inference/inference-jobs">推理任务</el-menu-item>
          <el-menu-item index="/inference/single-inference">单图推理</el-menu-item>
          <el-menu-item index="/inference/realtime-inference">在线推理</el-menu-item>
        </el-sub-menu>
        <el-menu-item v-if="userStore.isAdmin" index="/user-management">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- Content shell -->
    <div class="shell">
      <!-- Header -->
      <header class="header">
        <!-- Left -->
        <div class="header-left">
          <el-icon class="toggle-icon" @click="collapsed = !collapsed">
            <Expand v-if="collapsed" /><Fold v-else />
          </el-icon>
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item v-for="item in crumbs" :key="item.path" :to="item.path">
              <span v-if="item.last">{{ item.title }}</span>
              <a v-else>{{ item.title }}</a>
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <!-- Right -->
        <div class="header-right">
          <div class="camera-tag" :class="cameraStore.isConnected ? 'online' : 'offline'">
            <el-icon><VideoCamera /></el-icon>
            <span>相机{{ cameraStore.isConnected ? '已连接' : '未连接' }}</span>
          </div>
          <el-dropdown @command="onCommand" trigger="click">
            <div class="user-pill">
              <el-avatar size="small" :icon="UserFilled" />
              <span class="user-name">{{ userStore.userInfo?.username }}</span>
              <el-icon class="chevron"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">个人设置</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- Main -->
      <el-main class="main">
        <router-view v-slot="{ Component, route }">
          <PageTransitionWrapper :component="Component" :page-key="route.fullPath" />
        </router-view>
      </el-main>
    </div>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useUserStore } from '../store/user';
import { useCameraStore } from '../store/camera';
import { useRoute, useRouter } from 'vue-router';
import PageTransitionWrapper from '../components/PageTransitionWrapper.vue';
import {
  DataAnalysis, VideoCamera, Folder, Cpu, UserFilled, ArrowDown,
  Fold, Expand, Reading, Collection, ChatDotRound, ChatLineSquare,
  Operation, User
} from '@element-plus/icons-vue';

const collapsed = ref(false);
const userStore = useUserStore();
const cameraStore = useCameraStore();
const route = useRoute();
const router = useRouter();

const activeMenu = computed(() => route.path);

const crumbs = computed(() => {
  const items = [{ path: '/dashboard', title: '系统总览', last: route.path === '/dashboard' }];
  route.matched.forEach(m => {
    if (m.path === '/' || m.components?.default?.name === 'MainLayout') return;
    if (m.meta?.title && !m.meta.hiddenBreadcrumb) {
      items.push({ path: route.fullPath, title: m.meta.title, last: true });
    }
  });
  return items;
});

const onCommand = (cmd) => {
  if (cmd === 'logout') {
    userStore.logout();
    if (cameraStore.isConnected) cameraStore.disconnectCamera();
  } else if (cmd === 'settings') {
    router.push('/user-settings');
  }
};
</script>

<style scoped>
.layout {
  display: flex;
  height: 100dvh;
  background: #f0f6ff;
}

/* Sidebar */
.sidebar {
  background: #0f2a44;
  border-radius: 0 24px 24px 0;
  margin: 12px 0 12px 12px;
  overflow: hidden;
  box-shadow: 0 20px 48px rgba(15, 42, 68, 0.18);
  transition: width 0.28s cubic-bezier(0.16, 1, 0.3, 1);
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 64px;
  padding: 0 20px;
  overflow: hidden;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.logo-img { width: 32px; height: 32px; flex-shrink: 0; }
.logo-text {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
  letter-spacing: -0.01em;
}

.nav {
  border-right: none;
  background: transparent !important;
  padding: 12px 10px;
}
.nav :deep(.el-menu-item),
.nav :deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  border-radius: 10px;
  margin: 3px 0;
  transition:
    background-color 0.2s ease,
    color 0.2s ease;
}
.nav :deep(.el-menu-item:hover) {
  background: rgba(186, 214, 255, 0.14) !important;
}
.nav :deep(.el-menu-item.is-active) {
  background: #1e6fff !important;
  color: #fff !important;
}
.nav :deep(.el-sub-menu .el-menu) {
  background: transparent !important;
}

/* Shell */
.shell {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* Header */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  margin: 12px 12px 0;
  padding: 0 20px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(30, 111, 255, 0.10);
  border-radius: 0 0 16px 16px;
  box-shadow: 0 8px 24px rgba(15, 42, 68, 0.06);
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.toggle-icon {
  font-size: 18px;
  color: #0f2a44;
  cursor: pointer;
  transition: color 0.2s ease;
}
.toggle-icon:hover { color: #1e6fff; }
.breadcrumb { font-size: 15px; }

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.camera-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.camera-tag.online {
  background: #e8f7ef;
  border: 1px solid rgba(47, 158, 107, 0.3);
  color: #2f9e6b;
}
.camera-tag.offline {
  background: var(--color-surface-2, #f7faff);
  border: 1px solid var(--color-border);
  color: #6b7c93;
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--color-primary-subtle, #e8f1ff);
  border: 1px solid rgba(30, 111, 255, 0.15);
  transition: background-color 0.2s ease;
}
.user-pill:hover { background: #d6e5ff; }
.user-name { font-size: 14px; font-weight: 600; color: #0f2a44; }
.chevron { font-size: 12px; color: #6b7c93; }

/* Main */
.main {
  flex: 1;
  min-height: 0;
  background: #f0f6ff;
  overflow-y: auto;
  padding: 0;
}
</style>
