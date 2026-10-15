<template>
  <div class="driver-table">
    <el-table
      :data="filteredDrivers"
      v-loading="loading"
      stripe
      border
      style="width: 100%"
      empty-text="暂无驾驶员数据"
    >
      <el-table-column prop="id" label="ID" width="70" align="center" />
      <el-table-column prop="name" label="姓名" min-width="100" />
      <el-table-column prop="employee_id" label="工号" min-width="120" />
      <el-table-column label="人脸注册" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.has_face_feature ? 'success' : 'info'" size="small">
            {{ row.has_face_feature ? '已注册' : '未注册' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" min-width="160" />
      <el-table-column label="操作" width="100" align="center" fixed="right">
        <template #default="{ row }">
          <el-popconfirm
            title="确认删除该驾驶员？删除后无法恢复。"
            confirm-button-text="确认删除"
            cancel-button-text="取消"
            confirm-button-type="danger"
            @confirm="handleDelete(row)"
          >
            <template #reference>
              <el-button type="danger" size="small" text>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 驾驶员列表数据 */
  drivers: {
    type: Array,
    default: () => []
  },
  /** 搜索关键词（按姓名或工号过滤） */
  searchKeyword: {
    type: String,
    default: ''
  },
  /** 加载状态 */
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['delete'])

const filteredDrivers = computed(() => {
  const keyword = props.searchKeyword.trim().toLowerCase()
  if (!keyword) return props.drivers
  return props.drivers.filter(
    (d) =>
      d.name.toLowerCase().includes(keyword) ||
      d.employee_id.toLowerCase().includes(keyword)
  )
})

function handleDelete(row) {
  emit('delete', row)
}
</script>

<style scoped>
.driver-table {
  width: 100%;
}
</style>
