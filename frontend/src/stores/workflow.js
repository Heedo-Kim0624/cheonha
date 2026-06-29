import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { workflowLanes, workflowSteps, matchWorkflowStepIds, trimApiPath } from '@/data/workflowCatalog'

const MAX_RECENT_EVENTS = 150
const TABS_REFRESH_MS = 3000
const CLOCK_TICK_MS = 500

function inferChannel(path = '') {
  if (path.startsWith('/api/v1/mobile/')) return 'mobile_app'
  if (path.startsWith('/api/v1/field-manager/')) return 'field_manager_app'
  if (path.startsWith('/api/v1/vehicle/')) return 'vehicle_portal'
  if (path.startsWith('/api/v1/tracking/')) return 'tracking'
  if (path.startsWith('/api/v1/points/')) return 'points'
  return 'web_portal'
}

function normalizeUrlParts(urlString) {
  try {
    const url = new URL(urlString)
    return {
      path: url.pathname,
      queryString: url.search.replace(/^\?/, ''),
      fullUrl: url.toString(),
    }
  } catch (_error) {
    return {
      path: urlString,
      queryString: '',
      fullUrl: urlString,
    }
  }
}

function shouldTrackRequest(urlString) {
  return urlString.includes('/api/v1/')
}

function pickDefaultTab(tabs) {
  const preferred = tabs.find((tab) =>
    tab.url &&
    !tab.url.includes('/cheonha/workflow') &&
    (
      tab.url.includes('/cheonha') ||
      tab.url.includes('/portal') ||
      tab.url.includes('43.201.160.163') ||
      tab.url.includes('13.124.120.147')
    ),
  )
  return preferred?.id || tabs[0]?.id || ''
}

export const useWorkflowStore = defineStore('workflow', () => {
  const loading = ref(false)
  const error = ref('')
  const chromeAvailable = ref(false)
  const chromeTabs = ref([])
  const selectedTabId = ref('')
  const selectedTabTitle = ref('')
  const isConnected = ref(false)
  const sessionStartedAt = ref(null)
  const lastEventAt = ref(null)
  const activeRequestMap = ref({})
  const recentEventsState = ref([])
  const nowTick = ref(Date.now())

  let socket = null
  let tabsTimerId = null
  let clockTimerId = null

  const activeRequests = computed(() => {
    void nowTick.value
    return Object.values(activeRequestMap.value)
      .sort((a, b) => b.startedAt - a.startedAt)
      .map((event) => ({
        ...event,
        channel: inferChannel(event.path),
        ageMs: Math.max(0, nowTick.value - event.startedAt),
        stepIds: matchWorkflowStepIds(event.method, event.path),
        displayPath: trimApiPath(event.path, event.queryString),
      }))
  })

  const recentEvents = computed(() =>
    recentEventsState.value.map((event) => ({
      ...event,
      channel: inferChannel(event.path),
      stepIds: matchWorkflowStepIds(event.method, event.path),
      displayPath: trimApiPath(event.path, event.queryString),
    })),
  )

  const stepStateMap = computed(() => {
    const map = new Map()
    for (const step of workflowSteps) {
      const active = activeRequests.value.filter((event) => event.stepIds.includes(step.id))
      const lastEvent = recentEvents.value.find((event) => event.stepIds.includes(step.id)) || null
      map.set(step.id, {
        active,
        lastEvent,
        successCount: recentEvents.value.filter((event) => event.stepIds.includes(step.id) && event.ok).length,
        errorCount: recentEvents.value.filter((event) => event.stepIds.includes(step.id) && !event.ok).length,
        status: active.length
          ? 'working'
          : lastEvent
            ? (lastEvent.ok ? 'completed' : 'failed')
            : 'idle',
      })
    }
    return map
  })

  const stepsWithState = computed(() =>
    workflowSteps.map((step) => ({
      ...step,
      state: stepStateMap.value.get(step.id),
    })),
  )

  const lanesWithState = computed(() =>
    workflowLanes.map((lane) => {
      const steps = stepsWithState.value.filter((step) => step.laneId === lane.id)
      return {
        ...lane,
        steps,
        summary: {
          total: steps.length,
          working: steps.filter((step) => step.state.status === 'working').length,
          completed: steps.filter((step) => step.state.status === 'completed').length,
          failed: steps.filter((step) => step.state.status === 'failed').length,
        },
      }
    }),
  )

  const summary = computed(() => ({
    activeRequests: activeRequests.value.length,
    recentRequests: recentEvents.value.length,
    successCount: recentEvents.value.filter((event) => event.ok).length,
    errorCount: recentEvents.value.filter((event) => !event.ok).length,
    workingSteps: stepsWithState.value.filter((step) => step.state.status === 'working').length,
    completedSteps: stepsWithState.value.filter((step) => step.state.status === 'completed').length,
    failedSteps: stepsWithState.value.filter((step) => step.state.status === 'failed').length,
  }))

  const unmappedRecentEvents = computed(() =>
    recentEvents.value.filter((event) => event.stepIds.length === 0),
  )

  function clearSession() {
    activeRequestMap.value = {}
    recentEventsState.value = []
    sessionStartedAt.value = Date.now()
    lastEventAt.value = null
  }

  function ingestRequestStart(params) {
    const { path, queryString, fullUrl } = normalizeUrlParts(params.request.url)
    if (!shouldTrackRequest(fullUrl)) {
      return
    }
    const startedAt = params.wallTime ? Math.round(params.wallTime * 1000) : Date.now()
    activeRequestMap.value = {
      ...activeRequestMap.value,
      [params.requestId]: {
        requestId: params.requestId,
        method: (params.request.method || 'GET').toUpperCase(),
        path,
        queryString,
        fullUrl,
        startedAt,
        initiatorType: params.initiator?.type || '',
        resourceType: params.type || '',
      },
    }
  }

  function finalizeRequest(requestId, payload) {
    const started = activeRequestMap.value[requestId]
    if (!started) {
      return
    }
    const nextMap = { ...activeRequestMap.value }
    delete nextMap[requestId]
    activeRequestMap.value = nextMap
    recentEventsState.value = [
      {
        ...started,
        ...payload,
      },
      ...recentEventsState.value,
    ].slice(0, MAX_RECENT_EVENTS)
    lastEventAt.value = Date.now()
  }

  function ingestProtocolMessage(message) {
    const payload = JSON.parse(message.data)
    if (!payload.method) return

    if (payload.method === 'Network.requestWillBeSent') {
      ingestRequestStart(payload.params)
      return
    }

    if (payload.method === 'Network.responseReceived') {
      const request = activeRequestMap.value[payload.params.requestId]
      if (!request) return
      activeRequestMap.value = {
        ...activeRequestMap.value,
        [payload.params.requestId]: {
          ...request,
          statusCode: payload.params.response?.status || 0,
        },
      }
      return
    }

    if (payload.method === 'Network.loadingFinished') {
      const started = activeRequestMap.value[payload.params.requestId]
      if (!started) return
      finalizeRequest(payload.params.requestId, {
        ok: (started.statusCode || 0) < 400,
        statusCode: started.statusCode || 200,
        endedAt: Date.now(),
        durationMs: Math.max(0, Date.now() - started.startedAt),
        encodedDataLength: payload.params.encodedDataLength || 0,
      })
      return
    }

    if (payload.method === 'Network.loadingFailed') {
      finalizeRequest(payload.params.requestId, {
        ok: false,
        statusCode: 0,
        endedAt: Date.now(),
        durationMs: 0,
        errorText: payload.params.errorText || 'Network failed',
      })
    }
  }

  function disconnectChrome() {
    isConnected.value = false
    if (socket) {
      socket.onopen = null
      socket.onmessage = null
      socket.onerror = null
      socket.onclose = null
      socket.close()
      socket = null
    }
  }

  function connectToTab(tabId, { reset = true } = {}) {
    if (!tabId) {
      error.value = '연결할 Chrome 탭을 찾지 못했습니다.'
      return
    }
    disconnectChrome()
    if (reset) {
      clearSession()
    }

    const selected = chromeTabs.value.find((tab) => tab.id === tabId)
    selectedTabId.value = tabId
    selectedTabTitle.value = selected?.title || selected?.url || ''

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    socket = new WebSocket(`${protocol}//${window.location.host}/chrome/devtools/page/${tabId}`)

    socket.onopen = () => {
      isConnected.value = true
      error.value = ''
      socket.send(JSON.stringify({ id: 1, method: 'Network.enable' }))
      socket.send(JSON.stringify({ id: 2, method: 'Page.enable' }))
    }

    socket.onmessage = ingestProtocolMessage

    socket.onerror = () => {
      error.value = 'Chrome 원격 디버깅 소켓 연결에 실패했습니다.'
    }

    socket.onclose = () => {
      isConnected.value = false
    }
  }

  async function loadChromeTabs({ autoConnect = true } = {}) {
    loading.value = true
    try {
      const response = await fetch('/chrome/json')
      if (!response.ok) {
        throw new Error(`Chrome tabs ${response.status}`)
      }
      const data = await response.json()
      const tabs = Array.isArray(data)
        ? data
            .filter((tab) => tab.type === 'page')
            .map((tab) => ({
              id: tab.id,
              title: tab.title || '(제목 없음)',
              url: tab.url || '',
            }))
        : []

      chromeTabs.value = tabs
      chromeAvailable.value = true
      error.value = ''

      if (!selectedTabId.value || !tabs.some((tab) => tab.id === selectedTabId.value)) {
        selectedTabId.value = pickDefaultTab(tabs)
      }

      if (autoConnect && selectedTabId.value && !isConnected.value) {
        connectToTab(selectedTabId.value, { reset: false })
      }
    } catch (err) {
      chromeAvailable.value = false
      chromeTabs.value = []
      disconnectChrome()
      error.value =
        'Chrome 네트워크를 읽으려면 Chrome을 원격 디버깅 모드로 실행해야 합니다. 예: chrome.exe --remote-debugging-port=9222'
    } finally {
      loading.value = false
    }
  }

  function startChromeTracking() {
    stopChromeTracking()
    clearSession()
    loadChromeTabs()
    tabsTimerId = window.setInterval(() => {
      loadChromeTabs({ autoConnect: !isConnected.value })
    }, TABS_REFRESH_MS)
    clockTimerId = window.setInterval(() => {
      nowTick.value = Date.now()
    }, CLOCK_TICK_MS)
  }

  function stopChromeTracking() {
    disconnectChrome()
    if (tabsTimerId) {
      window.clearInterval(tabsTimerId)
      tabsTimerId = null
    }
    if (clockTimerId) {
      window.clearInterval(clockTimerId)
      clockTimerId = null
    }
  }

  return {
    loading,
    error,
    chromeAvailable,
    chromeTabs,
    selectedTabId,
    selectedTabTitle,
    isConnected,
    sessionStartedAt,
    lastEventAt,
    activeRequests,
    recentEvents,
    lanesWithState,
    stepsWithState,
    summary,
    unmappedRecentEvents,
    clearSession,
    connectToTab,
    loadChromeTabs,
    startChromeTracking,
    stopChromeTracking,
  }
})
