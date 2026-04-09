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

// legacy - keep for compatibility
export const fetchDashboard = () => {
  return fetchKpi()
}
