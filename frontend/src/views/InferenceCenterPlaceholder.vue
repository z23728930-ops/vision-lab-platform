<!-- src/views/InferenceCenterPlaceholder.vue -->
<template>
  <div class="inference-center-container">
    <!-- 这里可以放置推理中心页面的通用布局或标题 -->
    <!-- <h2 style="margin-bottom: 20px;">推理中心</h2> -->
    <router-view></router-view>
  </div>
</template>

<script setup>
// 如果需要，可以在这里添加脚本逻辑
</script>

<style scoped>
.inference-center-container {
  /* 根据需要添加样式 */
  height: 100%; /* 确保容器有高度 */
  width: 100%; /* 确保容器有宽度 */
  /* 可以添加 padding 等 */
}
</style>