<template>
  <div class="dashboard">
    <div class="page-header">
      <h2 class="page-title">数据看板</h2>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :xs="24" :sm="8">
        <StatCard
          :value="overview.today_alerts"
          label="今日告警总数"
          :icon="Warning"
          icon-bg="#fef0f0"
          icon-color="#f56c6c"
          :loading="overviewLoading"
        />
      </el-col>
      <el-col :xs="24" :sm="8">
        <StatCard
          :value="overview.total_drivers"
          label="已注册驾驶员"
          :icon="User"
          icon-bg="#ecf5ff"
          icon-color="#409eff"
          :loading="overviewLoading"
        />
      </el-col>
      <el-col :xs="24" :sm="8">
        <StatCard
          :value="overview.today_sessions"
          label="今日监测会话"
          :icon="VideoCamera"
          icon-bg="#f0f9eb"
          icon-color="#67c23a"
          :loading="overviewLoading"
        />
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :xs="24" :lg="14">
        <TrendChart
          :data="trendData"
          :loading="trendLoading"
          :error="trendError"
        />
      </el-col>
      <el-col :xs="24" :lg="10">
        <TypePieChart
          :data="typeData"
          :loading="typeLoading"
          :error="typeError"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Warning, User, VideoCamera } from '@element-plus/icons-vue'
import StatCard from '@/components/StatCard.vue'
import TrendChart from '@/components/TrendChart.vue'
import TypePieChart from '@/components/TypePieChart.vue'
import { getStatsOverview, getStatsTrend, getStatsType } from '@/api/index.js'

// 概览数据
const overview = ref({ today_alerts: 0, total_drivers: 0, today_sessions: 0 })
const overviewLoading = ref(false)

// 趋势数据
const trendData = ref([])
const trendLoading = ref(false)
const trendError = ref(false)

// 类型分布数据
const typeData = ref([])
const typeLoading = ref(false)
const typeError = ref(false)

async function loadOverview() {
  overviewLoading.value = true
  try {
    const res = await getStatsOverview()
    overview.value = res.data
  } catch {
    // 错误已由拦截器处理
  } finally {
    overviewLoading.value = false
  }
}

async function loadTrend() {
  trendLoading.value = true
  trendError.value = false
  try {
    const res = await getStatsTrend()
    trendData.value = res.data
  } catch {
    trendError.value = true
  } finally {
    trendLoading.value = false
  }
}

async function loadType() {
  typeLoading.value = true
  typeError.value = false
  try {
    const res = await getStatsType()
    typeData.value = res.data
  } catch {
    typeError.value = true
  } finally {
    typeLoading.value = false
  }
}

onMounted(() => {
  loadOverview()
  loadTrend()
  loadType()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.stat-row {
  margin-bottom: 20px;
}

.stat-row .el-col {
  margin-bottom: 16px;
}

.chart-row .el-col {
  margin-bottom: 16px;
}
</style>
