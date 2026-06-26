import buttonApiMapMarkdown from '../../BUTTON_API_MAP.md?raw'

const laneDefinitions = [
  {
    id: 'clever-portal',
    title: 'CLEVER 통합 포털',
    badge: 'PORTAL',
    description: '운영현황, 근무기록, 포인트, 차량관리 흐름을 버튼 단위로 표시합니다.',
  },
  {
    id: 'cheonha-erp',
    title: '천하운수 ERP',
    badge: 'ERP',
    description: '로그인부터 배차, 정산, 권역, 추적, 인력풀까지 ERP 작업 흐름입니다.',
  },
  {
    id: 'driver-app',
    title: '기사용 정산 앱',
    badge: 'APP',
    description: '로그인, 근무시작/종료, CSV 업로드, 포인트 교환, 정산문의 흐름입니다.',
  },
  {
    id: 'field-manager',
    title: '현장관리자 앱',
    badge: 'FIELD',
    description: '구독 신청, 반납, A/S 접수까지 현장관리자 작업 흐름입니다.',
  },
]

function getLaneIdFromSectionCode(code) {
  if (/^A1(?:-|$)/.test(code)) return 'clever-portal'
  if (/^A\d+(?:-|$)/.test(code)) return 'cheonha-erp'
  if (/^B\d+(?:-|$)/.test(code)) return 'driver-app'
  if (/^C\d+(?:-|$)/.test(code)) return 'field-manager'
  return ''
}

function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

function normalizeValue(value = '') {
  return value
    .replace(/<br\s*\/?>/gi, ', ')
    .replace(/`/g, '')
    .replace(/\*\*/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function isDividerRow(cells) {
  return cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, '')))
}

function parseMarkdownTable(tableLines) {
  if (tableLines.length < 3) return null
  const rows = tableLines.map(splitTableRow)
  if (!rows.length || !isDividerRow(rows[1] || [])) return null
  const headers = rows[0].map(normalizeValue)
  const body = rows.slice(2).map((cells) => {
    const row = {}
    headers.forEach((header, index) => {
      row[header] = normalizeValue(cells[index] || '')
    })
    return row
  })
  return { rows: body }
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

function buildApiMatchers(apiText = '') {
  const matchers = []
  const regex = /\b(GET|POST|PUT|PATCH|DELETE)\s+([^\s,()]+)/g
  let match = null

  while ((match = regex.exec(apiText)) !== null) {
    let [, method, path] = match
    path = path.replace(/\?.*$/, '')
    if (!path.startsWith('/api/')) {
      path = `/api/v1${path.startsWith('/') ? path : `/${path}`}`
    }
    const pattern = escapeRegex(path)
      .replace(/\\\{[^}]+\\\}/g, '[^/]+')
      .replace(/\/+$/, '/?')
    matchers.push({
      method,
      path,
      regex: new RegExp(`^${pattern}$`),
    })
  }

  return matchers
}

function buildButtonNode(row, sectionCode, index, inheritedApi = '') {
  const contextParts = []
  ;['서브탭', '폼', '위치'].forEach((key) => {
    if (row[key]) {
      contextParts.push(row[key])
    }
  })

  const buttonLabel =
    firstValue(row, ['버튼', '입력/버튼']) ||
    firstValue(row, ['동작']) ||
    `항목 ${String(index + 1).padStart(2, '0')}`

  const action = firstValue(row, ['동작']) || '문서에 로컬 동작만 정의됨'
  const apiRaw = firstValue(row, ['API', '호출되는 API'])
  const shouldInheritApi = /^(동상|동일|같음)/.test(apiRaw)
  const api = shouldInheritApi
    ? inheritedApi || '라우터 전환 또는 로컬 처리'
    : apiRaw || '라우터 전환 또는 로컬 처리'

  return {
    id: `${sectionCode}-node-${index + 1}`,
    order: index + 1,
    title: [...contextParts, buttonLabel].filter(Boolean).join(' · '),
    buttonLabel,
    action,
    api,
      apiMatchers: buildApiMatchers(api),
    nextLabel: '',
  }
}

function parseButtonWorkflow(markdown) {
  const lines = markdown.split(/\r?\n/)
  const sections = []
  let currentSection = null

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    const headingMatch = /^(##|###)\s+([A-D]\d+(?:-\d+)?)\.\s+(.+)$/.exec(line)

    if (headingMatch) {
      const [, , code, title] = headingMatch
      currentSection = {
        code,
        title: normalizeValue(title),
      }
      continue
    }

    if (!currentSection || !line.trim().startsWith('|')) {
      continue
    }

    const tableLines = []
    while (index < lines.length && lines[index].trim().startsWith('|')) {
      tableLines.push(lines[index])
      index += 1
    }
    index -= 1

    const table = parseMarkdownTable(tableLines)
    const laneId = getLaneIdFromSectionCode(currentSection.code)
    if (!table || !laneId) {
      continue
    }

    let inheritedApi = ''
    const nodes = table.rows.map((row, rowIndex) => {
      const node = buildButtonNode(row, currentSection.code, rowIndex, inheritedApi)
      if (node.api && node.api !== '라우터 전환 또는 로컬 처리') {
        inheritedApi = node.api
      }
      return node
    })
    nodes.forEach((node, nodeIndex) => {
      node.nextLabel = nodes[nodeIndex + 1]?.buttonLabel || ''
    })

    sections.push({
      id: `${currentSection.code}-${sections.length + 1}`,
      laneId,
      code: currentSection.code,
      title: currentSection.title,
      nodes,
    })
  }

  return sections
}

const parsedSections = parseButtonWorkflow(buttonApiMapMarkdown)

export const buttonWorkflowLanes = laneDefinitions
  .map((lane) => {
    const sections = parsedSections.filter((section) => section.laneId === lane.id)
    return {
      ...lane,
      sections,
      sectionCount: sections.length,
      buttonCount: sections.reduce((sum, section) => sum + section.nodes.length, 0),
    }
  })
  .filter((lane) => lane.sectionCount > 0)
