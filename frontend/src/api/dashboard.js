import client from './client'

export const fetchKpi = () => {
  return client.get('/dashboard/dashboard/kpi')
}

export const fetchRevenueByRegion = () => {
  return client.get('/dashboard/dashboard/revenue_by_region')
}

export const fetchSettlementSummary = () => {
  return client.get('/dashboard/dashboard/settlement_summary')
}

export const fetchHomeOverview = (params = {}) => {
  return client.get('/dashboard/dashboard/home_overview', { params })
}

export const fetchHomeDailyDetail = (params = {}) => {
  return client.get('/dashboard/dashboard/home_daily_detail', { params })
}

export const fetchSalesOverview = (params = {}) => {
  return client.get('/dashboard/dashboard/sales_overview', { params })
}

// legacy - keep for compatibility
export const fetchDashboard = () => {
  return fetchKpi()
}
