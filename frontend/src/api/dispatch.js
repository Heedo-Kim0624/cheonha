import client from './client'

// Step 1: 배차 파일 업로드
export const uploadDispatchFile = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return client.post('/dispatch/uploads', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
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
export const fetchUploads = () => {
  return client.get('/dispatch/uploads')
}

// 레코드 조회 (전체)
export const getRecords = (uploadId) => {
  return client.get('/dispatch/records', { params: { upload_id: uploadId, limit: 500 } })
}

// 데이터 초기화
export const resetAllData = () => {
  return client.post('/dispatch/uploads/reset_data')
}
