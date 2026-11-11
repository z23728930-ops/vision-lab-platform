<template>
  <div class="page-transition-wrapper">
    <!-- 旧页面：只有在有旧组件且正在动画时才渲染并绝对定位 -->
    <div v-if="oldComponent" class="page-transition-item old-page" ref="oldEl">
      <component :is="oldComponent" />
    </div>

    <!-- 新页面：
         - 在动画期间（oldComponent 存在时）绝对定位。
         - 动画结束后（oldComponent 为 null 时）恢复正常文档流，撑开父元素。
    -->
    <div
        :class="['page-transition-item', 'new-page', { 'is-animating': oldComponent }]"
        ref="newEl"
    >
      <component :is="newComponent" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';
import { gsap } from 'gsap';

// props 接收 router-view 传递的 Component 和 key
const props = defineProps({
  component: Object, // 当前路由组件的 VNode (虚拟DOM节点)
  pageKey: [String, Number] // 路由的 key (通常是 route.fullPath)，用于触发组件切换
});

// 用于存储旧组件和新组件的 VNode
const oldComponent = ref(null);
const newComponent = ref(null);

// 用于获取旧页面和新页面 DOM 元素的引用
const oldEl = ref(null);
const newEl = ref(null);

// 监听 pageKey 的变化来触发动画
watch(() => props.pageKey, (newPageKey, oldPageKey) => {
  // 如果 key 没有变化（例如，只是路由参数变化但组件实例复用），只更新新组件
  if (newPageKey === oldPageKey) {
    newComponent.value = props.component;
    oldComponent.value = null; // 确保旧组件被清除，让新组件恢复正常流
    return;
  }

  // 存储当前显示中的组件作为旧组件
  // 只有当 newComponent 已经有值时，才将其视为旧组件进行动画
  if (newComponent.value) {
    oldComponent.value = newComponent.value;
  } else {
    // 首次加载时，没有旧组件，直接跳过旧组件的动画
    oldComponent.value = null;
  }
  newComponent.value = props.component;

  // 使用 nextTick 确保 DOM 已经更新：
  // 1. 旧组件可能仍然在 DOM 中（如果 oldComponent.value 不为 null）
  // 2. 新组件已经渲染到 DOM 中
  nextTick(() => {
    const animationDuration = 0.8; // 定义动画持续时间，方便统一修改

    // 确保旧页面元素存在且可见，然后执行离开动画
    if (oldEl.value) {
      gsap.to(oldEl.value, {
        x: -50, // 旧页面向左滑动 50px
        opacity: 0, // 旧页面淡出
        duration: animationDuration, // 动画持续时间 0.4 秒
        ease: "power3.inOut", // 缓动函数
        onComplete: () => {
          // 动画完成后，将旧组件的引用设为 null，让 Vue 销毁其 DOM 元素
          // 这也会导致 new-page 移除 'is-animating' 类，从而恢复正常文档流
          oldComponent.value = null;
        }
      });
    }

    // 确保新页面元素存在，然后执行进入动画
    if (newEl.value) {
      // 初始状态：新页面从右侧 50px 处开始，透明度为0
      // 目标状态：回到原位 (x: 0)，透明度为1
      gsap.fromTo(newEl.value,
          { x: 50, opacity: 0 },
          { x: 0, opacity: 1, duration: animationDuration, ease: "power3.inOut" }
      );
    }
  });
}, { immediate: true }); // immediate: true 确保组件首次挂载时也会触发进入动画
</script>

<style scoped>
.page-transition-wrapper {
  position: relative; /* 确保子元素能绝对定位 */
  width: 100%;
  /* 关键：min-height 确保 wrapper 至少占满父元素高度，并能被内容撑开 */
  min-height: 100%;
  /* flex-grow: 1; 如果父元素是 flex 容器，这会让它占据可用空间 */
  flex-grow: 1; /* 确保 PageTransitionWrapper 在 main-content (display:flex) 中占据所有可用垂直空间 */
}

.page-transition-item {
  width: 100%;
  box-sizing: border-box; /* 确保 padding 包含在 width/height 内 */
  padding: 16px;
  background-color: #f5f9ff;
  /* 默认情况下，新页面是正常文档流元素，撑开父元素 */
}

/* 只有在动画期间，旧页面和新页面才需要绝对定位 */
.page-transition-item.old-page,
.page-transition-item.is-animating {
  position: absolute;
  top: 0;
  left: 0;
}
</style>