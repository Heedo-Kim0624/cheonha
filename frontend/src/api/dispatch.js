import client from './client'

// Step 1: 배차 파일 업로드
export const uploadDispatchFile = (file, shipperCode = 'kurly') => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('shipper_code', shipperCode || 'kurly')
  return client.post('/dispatch/uploads', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const previewTextDispatch = (payload) => {
  return client.post('/dispatch/uploads/text-preview/', payload)
}

export const uploadTextDispatch = (payload) => {
  return client.post('/dispatch/uploads/text/', payload)
}

// 감지 정보 조회
export const getDetectedInfo = (uploadId) => {
  return client.get(`/dispatch/uploads/${uploadId}/detected_info`)
}

// 통합 설정 (권역 + 배송원)
export const configureAll = (uploadId, data) => {
  return client.post(`/dispatch/uploads/${uploadId}/configure`, data)
}

// 박스수 업데이트 (분리 레코드용)
export const updateBoxes = (uploadId, records) => {
  return client.post(`/dispatch/uploads/${uploadId}/update_boxes`, { records })
}

// 특근 설정 (사람 기준)
export const setOvertime = (uploadId, crew) => {
  return client.post(`/dispatch/uploads/${uploadId}/set_overtime`, { crew })
}

// 정산 확정
export const finalizeUpload = (uploadId, data = {}) => {
  return client.post(`/dispatch/uploads/${uploadId}/finalize`, data)
}

// 업로드 목록 조회
export const fetchUploads = (params = {}) => {
  return client.get('/dispatch/uploads', { params })
}

// 업로드한 배차표 원본 파일 다운로드
export const downloadDispatchFile = (uploadId) => {
  return client.get(`/dispatch/uploads/${uploadId}/download-file`, {
    responseType: 'blob'
  })
}

// 운영현황 일별/조별 리포트
export const fetchOperationReport = (params = {}) => {
  return client.get('/dispatch/uploads/operation-report', { params })
}

export const fetchOperationReportYongchaMap = (params = {}) => {
  return client.get('/dispatch/uploads/operation-report-yongcha-map', { params })
}

export const fetchOperationReportTerritories = (params = {}) => {
  return client.get('/dispatch/uploads/operation-report-territories', { params })
}

export const downloadOperationReportCsv = (params = {}) => {
  return client.get('/dispatch/uploads/operation-report-csv', {
    params,
    responseType: 'blob'
  })
}

// 레코드 조회 (전체)
export const getRecords = (uploadId) => {
  return client.get('/dispatch/records', { params: { upload_id: uploadId, limit: 500 } })
}

// 데이터 초기화
export const resetAllData = () => {
  return client.post('/dispatch/uploads/reset_data')
}
