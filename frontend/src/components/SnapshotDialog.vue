<template>
  <el-dialog
    v-model="visible"
    title="告警截图预览"
    width="640px"
    :close-on-click-modal="true"
    destroy-on-close
    class="snapshot-dialog"
  >
    <div class="snapshot-dialog__body">
      <div v-if="imageError" class="snapshot-dialog__error">
        <el-empty description="截图不可用" :image-size="80" />
      </div>
      <img
        v-else
        :src="snapshotUrl"
        alt="告警截图"
        class="snapshot-dialog__image"
        @error="handleImageError"
      />
    </div>

    <div v-if="alertInfo" class="snapshot-dialog__info">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="告警类型">
          <el-tag :type="severityTagType(alertInfo.severity)" size="small">
            {{ TYPE_LABEL_MAP[alertInfo.alert_type] || alertInfo.alert_type }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="危险等级">
          <el-tag :type="severityTagType(alertInfo.severity)" size="small">
            {{ SEVERITY_LABEL_MAP[alertInfo.severity] || alertInfo.severity }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="驾驶员">
          {{ alertInfo.driver_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="触发时间">
          {{ alertInfo.created_at || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  /** 是否显示弹窗 */
  modelValue: {
    type: Boolean,
    default: false
  },
  /** 截图路径（相对路径，如 1_phone_20240117.jpg） */
  snapshotPath: {
    type: String,
    default: ''
  },
  /** 告警信息对象（可选，用于展示详情） */
  alertInfo: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const imageError = ref(false)

const snapshotUrl = computed(() => {
  if (!props.snapshotPath) return ''
  return `/snapshots/${props.snapshotPath}`
})

// 重置错误状态
watch(
  () => props.snapshotPath,
  () => {
    imageError.value = false
  }
)

function handleImageError() {
  imageError.value = true
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

function severityTagType(severity) {
  const map = { low: 'info', medium: 'warning', high: 'danger' }
  return map[severity] || 'info'
}
</script>

<style scoped>
.snapshot-dialog__body {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  background: #f5f7fa;
  border-radius: 6px;
  overflow: hidden;
}

.snapshot-dialog__image {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  display: block;
}

.snapshot-dialog__info {
  margin-top: 16px;
}
</style>
