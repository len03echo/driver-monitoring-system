<template>
  <el-card class="type-pie-chart" shadow="never">
    <template #header>
      <span class="chart-title">告警类型分布</span>
    </template>
    <div v-if="loading" class="chart-placeholder">
      <el-skeleton :rows="4" animated />
    </div>
    <div v-else-if="error" class="chart-error">
      <el-empty description="数据加载失败" :image-size="60" />
    </div>
    <div v-else-if="!data.length" class="chart-error">
      <el-empty description="暂无告警数据" :image-size="60" />
    </div>
    <div v-else ref="chartRef" class="chart-container" />
  </el-card>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  /** 类型分布数据，格式：[{ alert_type: string, count: number }] */
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: Boolean,
    default: false
  }
})

// 告警类型中文映射
const TYPE_LABEL_MAP = {
  phone: '使用手机',
  cup: '持杯',
  smoking: '抽烟',
  eye_closed: '闭眼',
  yawning: '哈欠',
  head_down: '低头',
  unknown: '未知'
}

const chartRef = ref(null)
let chartInstance = null

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  renderChart()
}

function renderChart() {
  if (!chartInstance || !props.data.length) return

  const seriesData = props.data.map((item) => ({
    name: TYPE_LABEL_MAP[item.alert_type] || item.alert_type,
    value: item.count
  }))

  chartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}：{c} 次（{d}%）'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { fontSize: 12, color: '#606266' }
    },
    series: [
      {
        name: '告警类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: false,
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' }
        },
        data: seriesData,
        color: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#9b59b6']
      }
    ]
  })
}

function handleResize() {
  chartInstance?.resize()
}

watch(
  () => [props.data, props.loading, props.error],
  async () => {
    await nextTick()
    if (props.loading || props.error || !props.data.length) return
    if (!chartInstance) {
      initChart()
    } else {
      renderChart()
    }
  },
  { deep: true }
)

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.type-pie-chart {
  border-radius: 8px;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.chart-container {
  height: 280px;
  width: 100%;
}

.chart-placeholder,
.chart-error {
  height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
