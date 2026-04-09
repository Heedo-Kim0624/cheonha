import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchKpi, fetchRevenueByRegion, fetchSettlementSummary } from '@/api/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  const kpiData = ref({
    수신: { value: 0, change: 0 },
    지급: { value: 0, change: 0 },
    특근: { value: 0, change: 0 },
    수익: { value: 0, change: 0 }
  })

  const regionRevenue = ref([])
  const recentActivity = ref([])

  const fetchData = async () => {
    try {
      const [kpiResp, regionResp, summaryResp] = await Promise.allSettled([
        fetchKpi(),
        fetchRevenueByRegion(),
        fetchSettlementSummary()
      ])

      if (kpiResp.status === 'fulfilled') {
        const d = kpiResp.value.data
        kpiData.value = {
          수신: { value: Number(d.total_revenue || 0), change: 0 },
          지급: { value: Number(d.total_paid || 0), change: 0 },
          특근: { value: Number(d.total_revenue || 0) - Number(d.total_paid || 0) - Number(d.total_profit || 0), change: 0 },
          수익: { value: Number(d.total_profit || 0), change: 0 }
        }
      }

      if (regionResp.status === 'fulfilled') {
        const regions = regionResp.value.data || []
        const totalRevenue = regions.reduce((s, r) => s + Number(r.revenue || 0), 0)
        regionRevenue.value = regions.map(r => ({
          name: r.region,
          revenue: Number(r.revenue || 0),
          percentage: totalRevenue > 0 ? Math.round((Number(r.revenue || 0) / totalRevenue) * 100) : 0
        }))
      }

      if (summaryResp.status === 'fulfilled') {
        const summaries = summaryResp.value.data || []
        recentActivity.value = summaries.map((s, i) => ({
          id: i,
          description: `${s.period} 정산: 수신 ${Number(s.total_receive || 0).toLocaleString()}원, 수익 ${Number(s.total_profit || 0).toLocaleString()}원`,
          timestamp: new Date(),
          status: 'success'
        }))
      }
    } catch (error) {
      // 실패 시 기본값 유지
    }
  }

  return {
    kpiData,
    regionRevenue,
    recentActivity,
    fetchData
  }
})
