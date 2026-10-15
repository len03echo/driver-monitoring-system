/**
 * Vue Router 路由配置
 *
 * 使用 createWebHistory 模式，配置三个页面路由：
 * - /dashboard  首页看板
 * - /drivers    驾驶员管理
 * - /alerts     告警记录
 */

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '数据看板' }
  },
  {
    path: '/drivers',
    name: 'Drivers',
    component: () => import('@/views/Drivers.vue'),
    meta: { title: '驾驶员管理' }
  },
  {
    path: '/alerts',
    name: 'Alerts',
    component: () => import('@/views/Alerts.vue'),
    meta: { title: '告警记录' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 更新页面标题
router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} - 驾驶员状态监测系统`
    : '驾驶员状态监测系统'
})

export default router
