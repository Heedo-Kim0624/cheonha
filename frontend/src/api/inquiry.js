import client from './client'

export const fetchInquiries = (params = {}) => client.get('/inquiry/inquiries/', { params })
export const getInquiry = (id) => client.get(`/inquiry/inquiries/${id}/`)
export const updateInquiry = (id, data) => client.patch(`/inquiry/inquiries/${id}/`, data)
export const addInquiryMessage = (id, content, authorType = 'admin') =>
  client.post(`/inquiry/inquiries/${id}/messages/`, { content, author_type: authorType })
export const markInquiryRead = (id) => client.post(`/inquiry/inquiries/${id}/mark_read/`)
export const fetchInquiryCounts = (params = {}) => client.get('/inquiry/inquiries/counts/', { params })
