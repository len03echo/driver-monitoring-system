<template>
  <div class="alerts-page">
    <div class="page-header">
      <h2 class="page-title">告警记录</h2>
    </div>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="告警类型">
          <el-select
            v-model="filters.alert_type"
            placeholder="全部类型"
            clearable
            style="width: 130px"
          >
            <el-option
              v-for="item in ALERT_TYPE_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="危险等级">
          <el-select
            v-model="filters.severity"
            placeholder="全部等级"
            clearable
            style="width: 110px"
          >
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>

        <el-form-item label="驾驶员">
          <el-select
            v-model="filters.driver_id"
            placeholder="全部驾驶员"
            clearable
            style="width: 140px"
          >
            <el-option
              v-for="d in drivers"
              :key="d.id"
              :label="`${d.name}（${d.employee_id}）`"
              :value="d.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 告警记录表格 -->
    <el-card shadow="never" class="table-card">
      <AlertTable
        :alerts="alerts"
        :total="total"
        :page="pagination.page"
        :page-size="pagination.page_size"
        :loading="loading"
        @page-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import AlertTable from '@/components/AlertTable.vue'
import { getAlerts, getDrivers } from '@/api/index.js'

const alerts = ref([])
const total = ref(0)
const loading = ref(false)
const drivers = ref([])
const dateRange = ref(null)

const pagination = reactive({ page: 1, page_size: 20 })

const filters = reactive({
  alert_type: '',
  severity: '',
  driver_id: null
})

const ALERT_TYPE_OPTIONS = [
  { label: '使用手机', value: 'phone' },
  { label: '持杯', value: 'cup' },
  { label: '抽烟', value: 'smoking' },
  { label: '闭眼', value: 'eye_closed' },
  { label: '哈欠', value: 'yawning' },
  { label: '低头', value: 'head_down' },
  { label: '未知', value: 'unknown' }
]

function buildParams() {
  const params = {
    page: pagination.page,
    page_size: pagination.page_size
  }
  if (filters.alert_type) params.alert_type = filters.alert_type
  if (filters.severity) params.severity = filters.severity
  if (filters.driver_id) params.driver_id = filters.driver_id
  if (dateRange.value && dateRange.value.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  return params
}

async function loadAlerts() {
  loading.value = true
  try {
    const res = await getAlerts(buildParams())
    alerts.value = res.data.items
    total.value = res.data.total
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function loadDrivers() {
  try {
    const res = await getDrivers()
    drivers.value = res.data
  } catch {
    // 忽略，驾驶员下拉不影响主功能
  }
}

function handleSearch() {
  pagination.page = 1
  loadAlerts()
}

function handleReset() {
  filters.alert_type = ''
  filters.severity = ''
  filters.driver_id = null
  dateRange.value = null
  pagination.page = 1
  loadAlerts()
}

function handlePageChange(page) {
  pagination.page = page
  loadAlerts()
}

function handleSizeChange(size) {
  pagination.page_size = size
  pagination.page = 1
  loadAlerts()
}

onMounted(() => {
  loadAlerts()
  loadDrivers()
})
</script>

<style scoped>
.alerts-page {
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

.filter-card {
  margin-bottom: 16px;
  border-radius: 8px;
}

.table-card {
  border-radius: 8px;
}
</style>
