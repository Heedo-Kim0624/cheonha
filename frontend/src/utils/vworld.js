/**
 * VWorld 2D 지도 API 2.0 준비 대기 유틸.
 *
 * 실제 스크립트는 index.html 에서 초기 로드된다 (document.write 순차 로드 특성 때문).
 * 이 함수는 jQuery/OpenLayers/vw.ol3.Map 이 전부 준비될 때까지만 기다린다.
 */
export function loadVWorld({ timeout = 15000, interval = 80 } = {}) {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined') return reject(new Error('SSR unsupported'))

    const ready = () =>
      window.vw && window.vw.ol3 && typeof window.vw.ol3.Map === 'function' &&
      window.ol && window.ol.proj && typeof window.ol.proj.fromLonLat === 'function'

    if (ready()) return resolve({ vw: window.vw, ol: window.ol })

    const started = Date.now()
    const timer = setInterval(() => {
      if (ready()) {
        clearInterval(timer)
        return resolve({ vw: window.vw, ol: window.ol })
      }
      if (Date.now() - started >= timeout) {
        clearInterval(timer)
        reject(new Error('VWorld 스크립트 로드 타임아웃 — 네트워크 · 인증키 · 차단 여부 확인 필요'))
      }
    }, interval)
  })
}
