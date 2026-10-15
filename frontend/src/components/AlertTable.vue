<template>
  <div class="alert-table">
    <el-table
      :data="alerts"
      v-loading="loading"
      stripe
      border
      style="width: 100%"
      empty-text="暂无告警记录"
    >
      <el-table-column prop="id" label="ID" width="70" align="center" />
      <el-table-column prop="driver_name" label="驾驶员" min-width="100" />
      <el-table-column label="告警类型" min-width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="alertTypeTagType(row.alert_type)" size="small">
            {{ TYPE_LABEL_MAP[row.alert_type] || row.alert_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="危险等级" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="severityTagType(row.severity)" size="small">
            {{ SEVERITY_LABEL_MAP[row.severity] || row.severity }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="截图" width="90" align="center">
        <template #default="{ row }">
          <div v-if="row.snapshot_path" class="snapshot-thumb" @click="handlePreview(row)">
            <img
              :src="`/snapshots/${row.snapshot_path}`"
              alt="截图"
              class="snapshot-thumb__img"
              @error="(e) => (e.target.style.display = 'none')"
            />
            <div class="snapshot-thumb__overlay">
              <el-icon><ZoomIn /></el-icon>
            </div>
          </div>
          <span v-else class="no-snapshot">无截图</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="触发时间" min-width="160" />
    </el-table>

    <!-- 分页 -->
    <div class="alert-table__pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="currentPageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- 截图预览弹窗 -->
    <SnapshotDialog
      v-model="previewVisible"
      :snapshot-path="previewSnapshot"
      :alert-info="previewAlertInfo"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ZoomIn } from '@element-plus/icons-vue'
import SnapshotDialog from './SnapshotDialog.vue'

const props = defineProps({
  /** 告警记录列表 */
  alerts: {
    type: Array,
    default: () => []
  },
  /** 总记录数 */
  total: {
    type: Number,
    default: 0
  },
  /** 当前页码 */
  page: {
    type: Number,
    default: 1
  },
  /** 每页条数 */
  pageSize: {
    type: Number,
    default: 20
  },
  /** 加载状态 */
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['page-change', 'size-change'])

const currentPage = computed({
  get: () => props.page,
  set: (val) => emit('page-change', val)
})

const currentPageSize = computed({
  get: () => props.pageSize,
  set: (val) => emit('size-change', val)
})

function handlePageChange(page) {
  emit('page-change', page)
}

function handleSizeChange(size) {
  emit('size-change', size)
}

// 截图预览
const previewVisible = ref(false)
const previewSnapshot = ref('')
const previewAlertInfo = ref(null)

function handlePreview(row) {
  previewSnapshot.value = row.snapshot_path
  previewAlertInfo.value = row
  previewVisible.value = true
}

const TYPE_LABEL_MAP = {
  phone: '使用手机',
  cup: '持杯',
  smoking: '抽烟',
  eye_closed: '闭眼',
  yawning: '哈欠',
  head_down: '低头',
  unknown: '未知'
}

const SEVERITY_LABEL_MAP = {
  low: '低',
  medium: '中',
  high: '高'
}

function alertTypeTagType(type) {
  const map = {
    phone: 'warning',
    cup: 'info',
    smoking: 'danger',
    eye_closed: 'danger',
    yawning: 'warning',
    head_down: 'warning',
    unknown: 'info'
  }
  return map[type] || 'info'
}

function severityTagType(severity) {
  const map = { low: 'info', medium: 'warning', high: 'danger' }
  return map[severity] || 'info'
}
</script>

<style scoped>
.alert-table__pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.snapshot-thumb {
  position: relative;
  width: 56px;
  height: 40px;
  cursor: pointer;
  border-radius: 4px;
  overflow: hidden;
  margin: 0 auto;
}

.snapshot-thumb__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.snapshot-thumb__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  color: #fff;
}

.snapshot-thumb:hover .snapshot-thumb__overlay {
  opacity: 1;
}

.no-snapshot {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
