const STORAGE_PREFIX = 'clever:selected-shipper'
export const SHIPPER_CONTEXT_CHANGED_EVENT = 'clever:shipper-context-changed'

const normalizeCompanyCode = (companyCode = 'cheonha') => (
  String(companyCode || '').trim().toLowerCase() || 'cheonha'
)

const normalizeShipperCode = (shipperCode = '') => (
  String(shipperCode || '').trim().toLowerCase()
)

export function getSelectedShipperCode(companyCode, fallback = 'kurly') {
  const normalizedFallback = normalizeShipperCode(fallback) || 'kurly'
  if (typeof window === 'undefined') return normalizedFallback
  return normalizeShipperCode(
    window.localStorage.getItem(`${STORAGE_PREFIX}:${normalizeCompanyCode(companyCode)}`),
  ) || normalizedFallback
}

export function setSelectedShipperCode(companyCode, shipperCode) {
  const company = normalizeCompanyCode(companyCode)
  const shipper = normalizeShipperCode(shipperCode) || 'kurly'
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(`${STORAGE_PREFIX}:${company}`, shipper)
    window.dispatchEvent(new CustomEvent(SHIPPER_CONTEXT_CHANGED_EVENT, {
      detail: { companyCode: company, shipperCode: shipper },
    }))
  }
  return shipper
}

export function ensureSelectedShipperCode(companyCode, enabledCodes = [], preferredCode = '') {
  const enabled = (enabledCodes || []).map(normalizeShipperCode).filter(Boolean)
  const fallback = enabled[0] || normalizeShipperCode(preferredCode) || 'kurly'
  const current = getSelectedShipperCode(companyCode, preferredCode || fallback)
  if (!enabled.length || enabled.includes(current)) return current
  return setSelectedShipperCode(companyCode, fallback)
}
