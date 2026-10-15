<template>
  <el-card class="stat-card" shadow="hover">
    <div class="stat-card__body">
      <div class="stat-card__icon" :style="{ backgroundColor: iconBg }">
        <el-icon :size="28" :color="iconColor">
          <component :is="icon" />
        </el-icon>
      </div>
      <div class="stat-card__content">
        <div class="stat-card__value">
          <span v-if="!loading">{{ value }}</span>
          <el-skeleton-item v-else variant="text" style="width: 60px; height: 32px" />
        </div>
        <div class="stat-card__label">{{ label }}</div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  /** 统计数值 */
  value: {
    type: [Number, String],
    default: 0
  },
  /** 卡片标签 */
  label: {
    type: String,
    required: true
  },
  /** Element Plus 图标组件名 */
  icon: {
    type: [String, Object],
    default: null
  },
  /** 图标背景色 */
  iconBg: {
    type: String,
    default: '#ecf5ff'
  },
  /** 图标颜色 */
  iconColor: {
    type: String,
    default: '#409eff'
  },
  /** 加载状态 */
  loading: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.stat-card {
  border-radius: 8px;
}

.stat-card__body {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-card__icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card__content {
  flex: 1;
  min-width: 0;
}

.stat-card__value {
  font-size: 32px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.stat-card__label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}
</style>
