<template>
  <el-container class="app-layout">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="app-aside">
      <div class="app-logo">
        <el-icon :size="24" color="#409eff"><Monitor /></el-icon>
        <span class="app-logo__text">驾驶员监测系统</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        router
        class="app-menu"
        background-color="#1d2535"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>数据看板</span>
        </el-menu-item>
        <el-menu-item index="/drivers">
          <el-icon><User /></el-icon>
          <span>驾驶员管理</span>
        </el-menu-item>
        <el-menu-item index="/alerts">
          <el-icon><Warning /></el-icon>
          <span>告警记录</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="app-main-container">
      <!-- 顶部栏 -->
      <el-header class="app-header">
        <span class="app-header__title">{{ currentTitle }}</span>
      </el-header>

      <!-- 内容区 -->
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const activeMenu = computed(() => route.path)

const currentTitle = computed(() => route.meta?.title || '驾驶员状态监测系统')
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body,
#app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    sans-serif;
}
</style>

<style scoped>
.app-layout {
  height: 100vh;
}

.app-aside {
  background-color: #1d2535;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  border-bottom: 1px solid #2d3748;
  flex-shrink: 0;
}

.app-logo__text {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
}

.app-menu :deep(.el-menu-item) {
  height: 50px;
  line-height: 50px;
}

.app-menu :deep(.el-menu-item.is-active) {
  background-color: #2d3748 !important;
}

.app-menu :deep(.el-menu-item:hover) {
  background-color: #2d3748 !important;
}

.app-main-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.app-header {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  padding: 0 24px;
  flex-shrink: 0;
}

.app-header__title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
  padding: 24px;
}
</style>
