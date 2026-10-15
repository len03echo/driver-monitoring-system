<template>
  <el-card class="trend-chart" shadow="never">
    <template #header>
      <span class="chart-title">近 7 天告警趋势</span>
    </template>
    <div v-if="loading" class="chart-placeholder">
      <el-skeleton :rows="4" animated />
    </div>
    <div v-else-if="error" class="chart-error">
      <el-empty description="数据加载失败" :image-size="60" />
    </div>
    <div v-else ref="chartRef" class="chart-container" />
  </el-card>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  /** 趋势数据，格式：[{ date: 'YYYY-MM-DD', count: number }] */
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

const chartRef = ref(null)
let chartInstance = null

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  renderChart()
}

function renderChart() {
  if (!chartInstance || !props.data.length) return

  const dates = props.data.map((item) => item.date)
  const counts = props.data.map((item) => item.count)

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        return `${p.axisValue}<br/>告警数：<b>${p.value}</b>`
      }
    },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { fontSize: 12, color: '#606266' },
      axisLine: { lineStyle: { color: '#dcdfe6' } }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { fontSize: 12, color: '#606266' },
      splitLine: { lineStyle: { color: '#f2f6fc' } }
    },
    series: [
      {
        name: '告警数',
        type: 'line',
        data: counts,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#409eff', width: 2 },
        itemStyle: { color: '#409eff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.3)' },
            { offset: 1, color: 'rgba(64,158,255,0.02)' }
          ])
        }
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
    if (props.loading || props.error) return
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
.trend-chart {
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
