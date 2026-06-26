import buttonApiMapMarkdown from '../../BUTTON_API_MAP.md?raw'

const LANE_DEFINITIONS = [
  {
    id: 'clever-portal',
    title: 'CLEVER 통합관리',
    badge: 'PORTAL',
    subtitle: '통합 현황과 차량 운영',
    description: '통합관리 포털에서 운영현황, 포인트, 차량관리 흐름을 보여줍니다.',
    supportsLive: true,
  },
  {
    id: 'cheonha-erp',
    title: '천하운수 ERP',
    badge: 'ERP',
    subtitle: '천하운수 업무 처리',
    description: '천하운수 웹 ERP에서 로그인, 정산, 권역, 운영 흐름을 보여줍니다.',
    supportsLive: true,
  },
  {
    id: 'driver-app',
    title: '기사용 정산 앱',
    badge: 'APP',
    subtitle: '기사 근무와 정산',
    description: '기사용 앱은 샘플 이벤트로 근무, 포인트, 문의 흐름을 보여줍니다.',
    supportsLive: false,
  },
  {
    id: 'field-manager',
    title: '현장관리자 앱',
    badge: 'FIELD',
    subtitle: '구독·반납·A/S',
    description: '현장관리자 앱은 샘플 이벤트로 구독, 반납, A/S 흐름을 보여줍니다.',
    supportsLive: false,
  },
]

const STATUS = {
  NONE: 'NONE',
  IN_PROGRESS: 'IN_PROGRESS',
  SUCCESS: 'SUCCESS',
  FAILED: 'FAILED',
}

const NODE_TYPES = {
  USER_FEATURE: 'USER_FEATURE',
  UI_SCREEN: 'UI_SCREEN',
  FRONTEND_COMPONENT: 'FRONTEND_COMPONENT',
  BFF: 'BFF',
  BACKEND_SERVICE: 'BACKEND_SERVICE',
  API: 'API',
  DATABASE: 'DATABASE',
  QUEUE: 'QUEUE',
  EXTERNAL_SYSTEM: 'EXTERNAL_SYSTEM',
}

function normalizeValue(value = '') {
  return String(value)
    .replace(/<br\s*\/?>/gi, ', ')
    .replace(/`/g, '')
    .replace(/\*\*/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => normalizeValue(cell))
}

function isDividerRow(cells) {
  return cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, '')))
}

function parseMarkdownTable(tableLines) {
  if (tableLines.length < 3) return null
  const rows = tableLines.map(splitTableRow)
  if (!rows.length || !isDividerRow(rows[1] || [])) return null

  const headers = rows[0]
  const body = rows.slice(2).map((cells) => {
    const row = {}
    headers.forEach((header, index) => {
      row[header] = cells[index] || ''
    })
    return row
  })
  return { headers, rows: body }
}

function firstValue(row, keys) {
  for (const key of keys) {
    if (row[key]) return row[key]
  }
  return ''
}

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function normalizeApiPath(path) {
  let normalized = String(path || '').replace(/\?.*$/, '').trim()
  if (!normalized) return normalized
  if (!normalized.startsWith('/')) normalized = `/${normalized}`
  if (!normalized.startsWith('/api/')) normalized = `/api/v1${normalized}`
  return normalized
}

function inferLaneId(sectionCode) {
  if (/^A1(?:-|$)/.test(sectionCode)) return 'clever-portal'
  if (/^A\d+(?:-|$)/.test(sectionCode)) return 'cheonha-erp'
  if (/^B\d+(?:-|$)/.test(sectionCode)) return 'driver-app'
  if (/^C\d+(?:-|$)/.test(sectionCode)) return 'field-manager'
  return ''
}

function inferFeatureRoute(sectionCode) {
  if (/^A1(?:-|$)/.test(sectionCode)) return '/portal/operations'
  if (/^A2(?:-|$)/.test(sectionCode)) return '/cheonha/login'
  if (/^A3(?:-|$)/.test(sectionCode)) return '/cheonha/dashboard'
  if (/^A4(?:-|$)/.test(sectionCode)) return '/cheonha/crew'
  if (/^A5(?:-|$)/.test(sectionCode)) return '/cheonha/dispatch'
  if (/^A6(?:-|$)/.test(sectionCode)) return '/cheonha/settlement'
  if (/^A7(?:-|$)/.test(sectionCode)) return '/cheonha/region'
  if (/^A8(?:-|$)/.test(sectionCode)) return '/cheonha/inquiry'
  if (/^A9(?:-|$)/.test(sectionCode)) return '/cheonha/tracking'
  if (/^A10(?:-|$)/.test(sectionCode)) return '/cheonha/manpower'
  if (/^A11(?:-|$)/.test(sectionCode)) return '/cheonha/tracking'
  if (/^A12(?:-|$)/.test(sectionCode)) return '/cheonha/operations'
  return '/'
}

function inferCallerLabel(laneId) {
  if (laneId === 'clever-portal') return 'CLEVER Portal Frontend'
  if (laneId === 'cheonha-erp') return 'Cheonha ERP Frontend'
  if (laneId === 'driver-app') return 'Driver Mobile App'
  if (laneId === 'field-manager') return 'Field Manager Mobile App'
  return 'Client'
}

function inferCalleeLabel(path) {
  const normalized = normalizeApiPath(path)
  const segment = normalized.split('/').filter(Boolean)[2] || 'service'
  const map = {
    auth: 'Auth Service',
    accounts: 'Accounts Service',
    dispatch: 'Dispatch Service',
    settlement: 'Settlement Service',
    crew: 'Crew Service',
    dashboard: 'Dashboard Service',
    inquiry: 'Inquiry Service',
    tracking: 'Tracking Service',
    points: 'Points Service',
    manpower: 'Manpower Service',
    territory: 'Territory Service',
    vehicle: 'Vehicle Service',
    mobile: 'Mobile API Service',
    'field-manager': 'Field Manager API',
    partner: 'Partner Service',
    region: 'Region Service',
  }
  return map[segment] || `${segment} Service`
}

function extractApiEntries(apiText, context) {
  const entries = []
  const regex = /\b(GET|POST|PUT|PATCH|DELETE)\s+([^\s,()]+)/g
  let match = null
  let index = 0

  while ((match = regex.exec(apiText)) !== null) {
    const method = match[1]
    const endpoint = normalizeApiPath(match[2])
    if (!endpoint) continue
    index += 1
    entries.push({
      id: `${context.featureId}-api-${context.nodeOrder}-${index}`,
      name: index === 1 ? `${context.buttonLabel} API` : `${context.buttonLabel} API ${index}`,
      method,
      endpoint,
      description: `${context.buttonLabel} 동작에서 호출되는 API입니다.`,
      caller: inferCallerLabel(context.laneId),
      callee: inferCalleeLabel(endpoint),
      inputSummary: context.inputSummary || '문서 기준 별도 입력 요약 없음',
      outputSummary: '요청 처리 결과 또는 다음 단계 진행 정보',
      requiresAuth: !/\/auth\/login|\/accounts\/signup|\/mobile\/login|\/field-manager\/login/.test(endpoint),
      failureConditions: [
        'HTTP 4xx/5xx 응답',
        '인증 또는 권한 오류',
        '네트워크 타임아웃 또는 연결 실패',
        '호출 대상 서비스 내부 예외',
      ],
      relatedNodeIds: [context.nodeId],
      matcher: {
        method,
        path: endpoint,
        regex: new RegExp(`^${escapeRegex(endpoint).replace(/\\\{[^}]+\\\}/g, '[^/]+').replace(/\/+$/, '/?')}$`),
      },
    })
  }

  return entries
}

function inferNodeType(node, index) {
  const text = `${node.title || ''} ${node.description || ''}`.toLowerCase()

  if (index === 0 || /page|screen|modal|calendar|popup|login/.test(text)) {
    return NODE_TYPES.UI_SCREEN
  }
  if (/db|database|query|sheet|csv/.test(text)) {
    return NODE_TYPES.DATABASE
  }
  if (/queue|event|publish|subscribe/.test(text)) {
    return NODE_TYPES.QUEUE
  }
  if (/browser|privacy|external|download-file/.test(text)) {
    return NODE_TYPES.EXTERNAL_SYSTEM
  }
  if (index === 1) {
    return NODE_TYPES.FRONTEND_COMPONENT
  }
  if (index === 2) {
    return NODE_TYPES.BFF
  }
  if (node.apiIds?.length) {
    return NODE_TYPES.BACKEND_SERVICE
  }
  return NODE_TYPES.FRONTEND_COMPONENT
}

function buildNode(row, section, laneId, featureId, rowIndex) {
  const buttonLabel =
    firstValue(row, ['버튼', '입력/버튼']) ||
    firstValue(row, ['동작']) ||
    `단계 ${String(rowIndex + 1).padStart(2, '0')}`

  const action = firstValue(row, ['동작']) || '문서상 동작 설명이 없습니다.'
  const apiRaw = firstValue(row, ['API', '호출되는 API']) || ''
  const nodeId = `${featureId}-node-${rowIndex + 1}`
  const inputSummary = [
    firstValue(row, ['입력/버튼']),
    firstValue(row, ['폼']),
    firstValue(row, ['위치']),
  ]
    .filter(Boolean)
    .join(' / ')

  const node = {
    id: nodeId,
    name: buttonLabel,
    title: buttonLabel,
    description: action,
    buttonLabel,
    action,
    level: 2,
    parentId: featureId,
    status: STATUS.NONE,
    metadata: {
      owner: section.code,
      domain: laneId,
    },
    nodeType: NODE_TYPES.BACKEND_SERVICE,
    sectionCode: section.code,
    apiIds: [],
    inputSummary,
  }

  const apis = extractApiEntries(apiRaw, {
    featureId,
    laneId,
    nodeId,
    nodeOrder: rowIndex + 1,
    buttonLabel,
    inputSummary,
  })

  node.apiIds = apis.map((api) => api.id)
  return { node, apis }
}

function parseFeatures(markdown) {
  const lines = markdown.split(/\r?\n/)
  const features = []
  let currentSection = null

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    const headingMatch = /^(##|###)\s+([A-C]\d+(?:-\d+)?)\.\s+(.+)$/.exec(line)

    if (headingMatch) {
      currentSection = {
        code: headingMatch[2],
        title: normalizeValue(headingMatch[3]),
      }
      continue
    }

    if (!currentSection || !line.trim().startsWith('|')) continue

    const tableLines = []
    while (index < lines.length && lines[index].trim().startsWith('|')) {
      tableLines.push(lines[index])
      index += 1
    }
    index -= 1

    const table = parseMarkdownTable(tableLines)
    const laneId = inferLaneId(currentSection.code)
    if (!table || !laneId) continue

    const featureId = `${laneId}-${currentSection.code}`
    const lane = LANE_DEFINITIONS.find((item) => item.id === laneId)
    const nodes = []
    const edges = []
    const apis = []

    table.rows.forEach((row, rowIndex) => {
      const built = buildNode(row, currentSection, laneId, featureId, rowIndex)
      const node = built.node
      node.nodeType = inferNodeType(node, rowIndex)
      nodes.push(node)
      apis.push(...built.apis)

      if (rowIndex > 0) {
        edges.push({
          id: `${featureId}-edge-${rowIndex}`,
          source: nodes[rowIndex - 1].id,
          target: node.id,
          type: node.apiIds.length ? 'HTTP_REQUEST' : 'INTERNAL_CALL',
          label: node.buttonLabel,
          status: STATUS.NONE,
        })
      }
    })

    const feature = {
      id: featureId,
      sectionCode: currentSection.code,
      laneId,
      laneTitle: lane?.title || laneId,
      laneBadge: lane?.badge || laneId,
      supportsLive: Boolean(lane?.supportsLive),
      liveEntryPath: inferFeatureRoute(currentSection.code),
      name: currentSection.title,
      description:
        firstValue(table.rows[0] || {}, ['동작']) ||
        `${currentSection.title} 기능의 실행 흐름입니다.`,
      userAction:
        firstValue(table.rows[0] || {}, ['버튼', '입력/버튼']) ||
        `${currentSection.title} 기능을 사용자가 실행합니다.`,
      nodes,
      edges,
      apis,
      status: STATUS.NONE,
    }

    features.push(feature)
  }

  return features
}

const features = parseFeatures(buttonApiMapMarkdown)

export const architectureWorkflowCatalog = {
  lanes: LANE_DEFINITIONS.map((lane) => ({
    ...lane,
    features: features.filter((feature) => feature.laneId === lane.id),
  })).filter((lane) => lane.features.length > 0),
  features,
}

export { STATUS, NODE_TYPES }
