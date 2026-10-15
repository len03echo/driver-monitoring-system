/**
 * Axios 封装及 API 方法
 *
 * 统一请求拦截器、响应拦截器、错误处理，封装所有 API 调用方法。
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const request = axios.create({
  baseURL: '',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    const res = response.data
    // 业务层错误（code 非 200）
    if (res.code !== 200) {
      ElMessage.error(res.msg || '请求失败')
      return Promise.reject(new Error(res.msg || '请求失败'))
    }
    return res
  },
  (error) => {
    if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else if (error.response) {
      const msg = error.response.data?.msg || `请求失败（${error.response.status}）`
      ElMessage.error(msg)
    } else {
      ElMessage.error('网络连接失败，请检查服务是否启动')
    }
    return Promise.reject(error)
  }
)

// ============================================================
// 驾驶员档案 API
// ============================================================

/**
 * 获取驾驶员列表
 * @returns {Promise<{code, data: Array, msg}>}
 */
export function getDrivers() {
  return request.get('/api/drivers')
}

/**
 * 新增驾驶员
 * @param {{ name: string, employee_id: string }} data
 * @returns {Promise<{code, data: Object, msg}>}
 */
export function createDriver(data) {
  return request.post('/api/drivers', data)
}

/**
 * 删除驾驶员
 * @param {number} id 驾驶员 ID
 * @returns {Promise<{code, data: null, msg}>}
 */
export function deleteDriver(id) {
  return request.delete(`/api/drivers/${id}`)
}

// ============================================================
// 告警记录 API
// ============================================================

/**
 * 查询告警记录（分页 + 筛选）
 * @param {{
 *   page?: number,
 *   page_size?: number,
 *   alert_type?: string,
 *   severity?: string,
 *   driver_id?: number,
 *   start_date?: string,
 *   end_date?: string
 * }} params
 * @returns {Promise<{code, data: {total, page, page_size, items}, msg}>}
 */
export function getAlerts(params = {}) {
  return request.get('/api/alerts', { params })
}

// ============================================================
// 统计数据 API
// ============================================================

/**
 * 获取统计概览（今日告警数、驾驶员总数、今日会话数）
 * @returns {Promise<{code, data: {today_alerts, total_drivers, today_sessions}, msg}>}
 */
export function getStatsOverview() {
  return request.get('/api/stats/overview')
}

/**
 * 获取近 7 天告警趋势
 * @returns {Promise<{code, data: Array<{date, count}>, msg}>}
 */
export function getStatsTrend() {
  return request.get('/api/stats/trend')
}

/**
 * 获取告警类型分布
 * @returns {Promise<{code, data: Array<{alert_type, count}>, msg}>}
 */
export function getStatsType() {
  return request.get('/api/stats/type')
}

export default request
