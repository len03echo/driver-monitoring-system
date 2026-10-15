<template>
  <div class="drivers-page">
    <div class="page-header">
      <h2 class="page-title">驾驶员管理</h2>
      <el-button type="primary" :icon="Plus" @click="showAddDialog = true">
        新增驾驶员
      </el-button>
    </div>

    <!-- 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-input
        v-model="searchKeyword"
        placeholder="按姓名或工号搜索"
        :prefix-icon="Search"
        clearable
        style="max-width: 320px"
      />
    </el-card>

    <!-- 驾驶员表格 -->
    <el-card shadow="never" class="table-card">
      <DriverTable
        :drivers="drivers"
        :search-keyword="searchKeyword"
        :loading="loading"
        @delete="handleDelete"
      />
    </el-card>

    <!-- 新增驾驶员对话框 -->
    <DriverFormDialog
      v-model="showAddDialog"
      :submitting="submitting"
      @submit="handleCreate"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import DriverTable from '@/components/DriverTable.vue'
import DriverFormDialog from '@/components/DriverFormDialog.vue'
import { getDrivers, createDriver, deleteDriver } from '@/api/index.js'

const drivers = ref([])
const loading = ref(false)
const searchKeyword = ref('')
const showAddDialog = ref(false)
const submitting = ref(false)

async function loadDrivers() {
  loading.value = true
  try {
    const res = await getDrivers()
    drivers.value = res.data
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function handleCreate(formData) {
  submitting.value = true
  try {
    await createDriver(formData)
    ElMessage.success('驾驶员创建成功')
    showAddDialog.value = false
    await loadDrivers()
  } catch {
    // 错误已由拦截器处理
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await deleteDriver(row.id)
    ElMessage.success('删除成功')
    await loadDrivers()
  } catch {
    // 错误已由拦截器处理
  }
}

onMounted(() => {
  loadDrivers()
})
</script>

<style scoped>
.drivers-page {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.search-card {
  margin-bottom: 16px;
  border-radius: 8px;
}

.table-card {
  border-radius: 8px;
}
</style>
