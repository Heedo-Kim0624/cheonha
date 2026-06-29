<template>
  <div class="workflow-app">
    <header class="workflow-header">
      <div class="title-block">
        <p class="eyebrow">Architecture Workflow</p>
        <h1>인터랙티브 시스템 아키텍처 다이어그램</h1>
        <p class="subtitle">
          기능을 하나 실행했을 때 어떤 화면, 서비스, API, 데이터 저장소를 거치는지 한눈에 이해할 수 있도록 정리한 워크플로우 뷰입니다.
        </p>
      </div>

      <div class="legend" aria-label="상태 범례">
        <span v-for="item in legendItems" :key="item.status" class="legend-item">
          <span class="dot" :class="item.status"></span>
          {{ item.label }}
        </span>
      </div>
    </header>

    <section class="workflow-toolbar">
      <div class="field">
        <label for="featureSelect">실행할 기능</label>
        <select id="featureSelect" v-model="selectedFeatureId">
          <option v-for="feature in featureOptions" :key="feature.id" :value="feature.id">
            {{ feature.laneBadge }} · {{ feature.name }}
          </option>
        </select>
      </div>

      <div class="field">
        <label for="scenarioSelect">실행 방식</label>
        <select id="scenarioSelect" v-model="selectedScenario">
          <option v-for="option in scenarioOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </div>

      <button type="button" @click="runSelectedFeature">실행</button>
      <button type="button" class="secondary" @click="openFeatureWindow" :disabled="!selectedFeature?.supportsLive">
        연결 창 열기
      </button>
      <button type="button" class="secondary" @click="resetExecutionState">초기화</button>

      <div class="trace-box">
        <strong>현재 traceId</strong>
        <span>{{ currentTraceId || '없음' }}</span>
      </div>
    </section>

    <main class="workbench">
      <aside class="sidebar">
        <div class="section-title">
          <h2>사용자 기능</h2>
          <span class="mini-pill">{{ filteredFeatures.length }}개</span>
        </div>

        <div class="sidebar-help">
          <strong>읽는 순서</strong>
          <p>왼쪽에서 기능을 고르고, 가운데에서 처리 흐름을 보고, 오른쪽에서 선택한 요소의 상세 정보를 확인합니다.</p>
        </div>

        <input
          v-model="searchText"
          type="search"
          class="search-input"
          placeholder="기능명, 서비스명, API, endpoint, 에러코드 검색"
        />

        <div class="filter-grid">
          <div class="field compact">
            <label for="statusFilter">상태</label>
            <select id="statusFilter" v-model="statusFilter">
              <option value="ALL">전체</option>
              <option v-for="item in legendItems" :key="item.status" :value="item.status">
                {{ item.label }}
              </option>
            </select>
          </div>

          <div class="field compact">
            <label for="nodeTypeFilter">노드 타입</label>
            <select id="nodeTypeFilter" v-model="nodeTypeFilter">
              <option value="ALL">전체</option>
              <option v-for="item in nodeTypeOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>
        </div>

        <div class="toggle-row">
          <label class="toggle-chip">
            <input v-model="failedOnly" type="checkbox" />
            실패만 보기
          </label>
          <label class="toggle-chip">
            <input v-model="showApiNodes" type="checkbox" />
            API 표시
          </label>
        </div>

        <div class="feature-list">
          <section v-for="lane in laneFeatureGroups" :key="lane.id" class="lane-group">
            <div class="lane-group-header">
              <span class="mini-pill type">{{ lane.badge }}</span>
              <div class="lane-header-copy">
                <strong>{{ lane.title }}</strong>
                <span>{{ lane.subtitle }}</span>
              </div>
            </div>

            <button
              v-for="feature in lane.features"
              :key="feature.id"
              type="button"
              class="feature-card"
              :class="{ active: feature.id === selectedFeatureId }"
              @click="selectFeature(feature.id, 'level2')"
            >
              <div class="topline">
                <span class="feature-name">{{ feature.name }}</span>
                <span class="status-pill compact" :class="featureStatus(feature.id)">
                  {{ statusLabel(featureStatus(feature.id)) }}
                </span>
              </div>
              <p>{{ feature.description }}</p>
            </button>
          </section>
        </div>
      </aside>

      <section class="canvas-panel">
        <div class="canvas-top">
          <div class="breadcrumb">
            <span>전체 시스템</span>
            <template v-if="selectedFeature">
              <span> &gt; </span>
              <strong>{{ selectedFeature.name }}</strong>
            </template>
            <template v-if="selectedTargetLabel && viewMode !== 'level1'">
              <span> &gt; </span>
              <strong>{{ selectedTargetLabel }}</strong>
            </template>
          </div>

          <div class="view-tabs">
            <button type="button" class="secondary" :class="{ active: viewMode === 'level1' }" @click="viewMode = 'level1'">
              전체 기능
            </button>
            <button
              type="button"
              class="secondary"
              :class="{ active: viewMode === 'level2' }"
              :disabled="!selectedFeature"
              @click="viewMode = 'level2'"
            >
              처리 단계
            </button>
            <button
              type="button"
              class="secondary"
              :class="{ active: viewMode === 'level3' }"
              :disabled="!selectedFeature"
              @click="viewMode = 'level3'"
            >
              API 호출
            </button>
            <button type="button" class="secondary" :class="{ active: showStoryStrip }" @click="showStoryStrip = !showStoryStrip">
              {{ showStoryStrip ? '요약 숨기기' : '요약 보기' }}
            </button>
            <button type="button" class="secondary" :class="{ active: showLogsPanel }" @click="showLogsPanel = !showLogsPanel">
              {{ showLogsPanel ? '로그 숨기기' : '로그 보기' }}
            </button>
          </div>

          <div class="zoom-controls">
            <button type="button" class="secondary" @click="zoomOut" :disabled="zoomLevel <= MIN_ZOOM">축소</button>
            <span class="zoom-readout">{{ zoomPercent }}%</span>
            <button type="button" class="secondary" @click="zoomIn" :disabled="zoomLevel >= MAX_ZOOM">확대</button>
            <button type="button" class="secondary" @click="resetZoom" :disabled="zoomLevel === 1">기본</button>
          </div>
        </div>

        <div class="summary-strip">
          <span class="mini-pill type">1. 기능 선택</span>
          <span class="mini-pill type">2. 처리 단계 확인</span>
          <span class="mini-pill type">3. 실패 지점 확인</span>
          <span class="mini-pill">{{ overallStatusLabel }}</span>
          <span class="mini-pill">기능 {{ filteredFeatures.length }}개</span>
          <span class="mini-pill">단계 {{ selectedFeature?.nodes.length || 0 }}개</span>
          <span class="mini-pill">연결선 {{ selectedFeature?.edges.length || 0 }}개</span>
          <span class="mini-pill">API {{ currentApiNodes.length }}개</span>
          <span class="mini-pill warn">추적 ID {{ currentTraceId || '없음' }}</span>
          <span v-if="windowStateLabel !== '미연결'" class="mini-pill">{{ windowStateLabel }}</span>
        </div>

        <div v-if="showStoryStrip && selectedFeature && storySteps.length" class="story-strip">
          <article v-for="step in storySteps" :key="step.id" class="story-card">
            <span class="story-order">0{{ step.order }}</span>
            <div class="story-body">
              <p class="story-title">{{ step.title }}</p>
              <p class="story-text">{{ step.text }}</p>
            </div>
          </article>
        </div>

        <div class="svg-wrap">
          <svg
            :viewBox="svgViewBox"
            :width="svgCanvasWidth"
            :height="svgCanvasHeight"
            role="img"
            aria-label="시스템 아키텍처 다이어그램"
          >
            <defs>
              <marker
                id="workflowArrow"
                markerWidth="11"
                markerHeight="11"
                refX="8"
                refY="3.5"
                orient="auto"
                markerUnits="strokeWidth"
              >
                <path d="M0,0 L0,7 L8,3.5 z" fill="#94a3b8" />
              </marker>
            </defs>

            <g v-if="viewMode === 'level1'">
              <g v-for="group in level1Groups" :key="group.id">
                <rect :x="group.x" :y="group.y" :width="group.w" :height="group.h" rx="24" class="stage-group level1-group" />
                <text :x="group.x + 18" :y="group.y + 24" class="group-subtitle">{{ group.badge }}</text>
                <text :x="group.x + 18" :y="group.y + 44" class="group-title">
                  <tspan v-for="(line, index) in svgLines(group.title, 16, 2)" :key="`g1-title-${group.id}-${index}`" :x="group.x + 18" :dy="index === 0 ? 0 : 15">
                    {{ line }}
                  </tspan>
                </text>
                <text :x="group.x + 18" :y="group.y + 74" class="group-note">
                  <tspan v-for="(line, index) in svgLines(group.subtitle, 26, 1)" :key="`g1-note-${group.id}-${index}`" :x="group.x + 18" :dy="index === 0 ? 0 : 13">
                    {{ line }}
                  </tspan>
                </text>
              </g>

              <g
                class="node-group"
                :class="{
                  selected: selectedTarget.type === 'FEATURE' && selectedTarget.id === 'feature-root',
                  'node-pulse': false,
                }"
                @click="selectSyntheticRoot"
              >
                <rect :x="level1RootNode.x" :y="level1RootNode.y" :width="level1RootNode.w" :height="level1RootNode.h" rx="18" class="node-card NONE" />
                <text :x="level1RootNode.centerX" y="76" text-anchor="middle" class="node-subtitle">USER ACTION</text>
                <text :x="level1RootNode.centerX" y="100" text-anchor="middle" class="node-title">사용자 액션</text>
              </g>

              <g
                v-for="edge in level1Edges"
                :key="edge.id"
                class="edge-group"
                :class="{ selected: selectedTarget.type === 'EDGE' && selectedTarget.id === edge.id }"
                @click="selectEdge(edge.id, 'level1')"
              >
                <path
                  class="edge-path"
                  :class="[edge.status, edge.status === 'IN_PROGRESS' ? 'edge-flow' : '']"
                  :d="edge.path"
                  marker-end="url(#workflowArrow)"
                />
                <path class="edge-click-area" :d="edge.path" />
              </g>

              <g
                v-for="node in level1Nodes"
                :key="node.id"
                class="node-group"
                :class="{
                  selected: selectedTarget.type === 'FEATURE' && selectedTarget.id === node.id,
                  'node-pulse': node.status === 'IN_PROGRESS',
                  'search-hit': node.searchHit,
                  'opacity-dim': node.dimmed,
                }"
                @click="selectFeature(node.id, 'level2')"
              >
                <rect :x="node.x" :y="node.y" :width="node.w" :height="node.h" rx="18" class="node-card" :class="node.status" />
                <text :x="node.x + 18" :y="node.y + 24" class="node-subtitle">{{ node.badge }}</text>
                <text :x="node.x + 18" :y="node.y + 44" class="node-title">
                  <tspan v-for="(line, index) in svgLines(node.name, 14, 2)" :key="`l1-node-title-${node.id}-${index}`" :x="node.x + 18" :dy="index === 0 ? 0 : 14">
                    {{ line }}
                  </tspan>
                </text>
                <text :x="node.x + 18" :y="node.y + 76" class="node-description">
                  <tspan v-for="(line, index) in svgLines(node.description, 22, 1)" :key="`l1-node-desc-${node.id}-${index}`" :x="node.x + 18" :dy="index === 0 ? 0 : 12">
                    {{ line }}
                  </tspan>
                </text>
                <g :transform="`translate(${node.x + node.w - 86}, ${node.y + node.h - 34})`">
                  <rect width="68" height="22" rx="11" class="badge-bg" :class="node.status" />
                  <text x="34" y="15" text-anchor="middle" class="badge-text">
                    {{ statusLabel(node.status) }}
                  </text>
                </g>
              </g>
            </g>

            <g v-else-if="viewMode === 'level2' && selectedFeature">
              <g v-for="group in level2Groups" :key="group.id">
                <rect :x="group.x" :y="group.y" :width="group.w" :height="group.h" rx="22" class="stage-group" />
                <text :x="group.x + 16" :y="group.y + 24" class="group-title">
                  <tspan v-for="(line, index) in svgLines(group.title, 14, 2)" :key="`g2-title-${group.id}-${index}`" :x="group.x + 16" :dy="index === 0 ? 0 : 14">
                    {{ line }}
                  </tspan>
                </text>
                <text :x="group.x + 16" :y="group.y + 42" class="group-note">
                  <tspan v-for="(line, index) in svgLines(group.subtitle, 20, 1)" :key="`g2-note-${group.id}-${index}`" :x="group.x + 16" :dy="index === 0 ? 0 : 12">
                    {{ line }}
                  </tspan>
                </text>
              </g>

              <g
                v-for="edge in level2Edges"
                :key="edge.id"
                class="edge-group"
                :class="{
                  selected: selectedTarget.type === 'EDGE' && selectedTarget.id === edge.id,
                  'search-hit': edge.searchHit,
                  'opacity-dim': edge.dimmed,
                }"
                @click="selectEdge(edge.id, 'level2')"
              >
                <path
                  class="edge-path"
                  :class="[edge.status, edge.status === 'IN_PROGRESS' ? 'edge-flow' : '']"
                  :d="edge.path"
                  marker-end="url(#workflowArrow)"
                />
                <path class="edge-click-area" :d="edge.path" />
                <rect :x="edge.labelX - 45" :y="edge.labelY - 12" width="90" height="24" rx="12" class="edge-label-bg" />
                <text :x="edge.labelX" :y="edge.labelY + 4" text-anchor="middle" class="edge-label">
                  {{ compactEdgeLabel(edge) }}
                </text>
              </g>

              <g
                v-for="node in level2Nodes"
                :key="node.id"
                class="node-group"
                :class="{
                  selected: selectedTarget.type === 'NODE' && selectedTarget.id === node.id,
                  'node-pulse': node.status === 'IN_PROGRESS',
                  'search-hit': node.searchHit,
                  'opacity-dim': node.dimmed,
                }"
                @click="selectNode(node.id, 'level2')"
              >
                <rect :x="node.x" :y="node.y" :width="node.w" :height="node.h" rx="18" class="node-card" :class="node.status" />
                <text :x="node.x + 18" :y="node.y + 16" class="step-order">STEP {{ node.stepOrder }}</text>
                <text :x="node.x + 18" :y="node.y + 30" class="node-subtitle">{{ node.typeLabel }}</text>
                <text :x="node.x + 18" :y="node.y + 46" class="node-title">
                  <tspan v-for="(line, index) in svgLines(node.name, 16, 2)" :key="`l2-node-title-${node.id}-${index}`" :x="node.x + 18" :dy="index === 0 ? 0 : 14">
                    {{ line }}
                  </tspan>
                </text>
                <text :x="node.x + 18" :y="node.y + 84" class="node-description">
                  <tspan v-for="(line, index) in svgLines(node.plainDescription, 24, 1)" :key="`l2-node-desc-${node.id}-${index}`" :x="node.x + 18" :dy="index === 0 ? 0 : 12">
                    {{ line }}
                  </tspan>
                </text>
                <g :transform="`translate(${node.x + node.w - 86}, ${node.y + node.h - 34})`">
                  <rect width="68" height="22" rx="11" class="badge-bg" :class="node.status" />
                  <text x="34" y="15" text-anchor="middle" class="badge-text">
                    {{ statusLabel(node.status) }}
                  </text>
                </g>
              </g>
            </g>

            <g v-else-if="viewMode === 'level3' && selectedFeature">
              <g v-for="group in level3Groups" :key="group.id">
                <rect :x="group.x" :y="group.y" :width="group.w" :height="group.h" rx="22" class="stage-group" />
                <text :x="group.x + 16" :y="group.y + 24" class="group-title">
                  <tspan v-for="(line, index) in svgLines(group.title, 14, 2)" :key="`g3-title-${group.id}-${index}`" :x="group.x + 16" :dy="index === 0 ? 0 : 14">
                    {{ line }}
                  </tspan>
                </text>
                <text :x="group.x + 16" :y="group.y + 42" class="group-note">
                  <tspan v-for="(line, index) in svgLines(group.subtitle, 20, 1)" :key="`g3-note-${group.id}-${index}`" :x="group.x + 16" :dy="index === 0 ? 0 : 12">
                    {{ line }}
                  </tspan>
                </text>
              </g>

              <g
                class="node-group"
                :class="{
                  selected: selectedTarget.type === 'NODE' && selectedTarget.id === apiRootNode.id,
                  'node-pulse': apiRootNode.status === 'IN_PROGRESS',
                }"
                @click="selectNode(apiRootNode.id, 'level2')"
              >
                <rect :x="apiRootNode.x" :y="apiRootNode.y" :width="apiRootNode.w" :height="apiRootNode.h" rx="18" class="node-card" :class="apiRootNode.status" />
                <text :x="apiRootNode.x + 18" :y="apiRootNode.y + 24" class="node-subtitle">{{ apiRootNode.typeLabel }}</text>
                <text :x="apiRootNode.x + 18" :y="apiRootNode.y + 46" class="node-title">
                  <tspan v-for="(line, index) in svgLines(apiRootNode.name, 16, 2)" :key="`api-root-title-${index}`" :x="apiRootNode.x + 18" :dy="index === 0 ? 0 : 14">
                    {{ line }}
                  </tspan>
                </text>
                <text :x="apiRootNode.x + 18" :y="apiRootNode.y + 84" class="node-description">
                  <tspan v-for="(line, index) in svgLines(apiRootNode.description, 24, 1)" :key="`api-root-desc-${index}`" :x="apiRootNode.x + 18" :dy="index === 0 ? 0 : 12">
                    {{ line }}
                  </tspan>
                </text>
              </g>

              <g
                v-for="edge in level3Edges"
                :key="edge.id"
                class="edge-group"
                :class="{
                  selected: selectedTarget.type === 'EDGE' && selectedTarget.id === edge.id,
                  'search-hit': edge.searchHit,
                  'opacity-dim': edge.dimmed,
                }"
                @click="selectEdge(edge.id, 'level3')"
              >
                <path
                  class="edge-path"
                  :class="[edge.status, edge.status === 'IN_PROGRESS' ? 'edge-flow' : '']"
                  :d="edge.path"
                  marker-end="url(#workflowArrow)"
                />
                <path class="edge-click-area" :d="edge.path" />
              </g>

              <g
                v-for="targetNode in level3TargetNodes"
                :key="targetNode.id"
                class="node-group"
                :class="{
                  'node-pulse': targetNode.status === 'IN_PROGRESS',
                  'opacity-dim': shouldDimByFilters(targetNode.status),
                }"
              >
                <rect :x="targetNode.x" :y="targetNode.y" :width="targetNode.w" :height="targetNode.h" rx="18" class="node-card" :class="targetNode.status" />
                <text :x="targetNode.x + 18" :y="targetNode.y + 24" class="node-subtitle">{{ targetNode.typeLabel }}</text>
                <text :x="targetNode.x + 18" :y="targetNode.y + 46" class="node-title">
                  <tspan v-for="(line, index) in svgLines(targetNode.name, 16, 2)" :key="`target-title-${targetNode.id}-${index}`" :x="targetNode.x + 18" :dy="index === 0 ? 0 : 14">
                    {{ line }}
                  </tspan>
                </text>
                <text :x="targetNode.x + 18" :y="targetNode.y + 84" class="node-description">
                  <tspan v-for="(line, index) in svgLines(targetNode.plainDescription || targetNode.description, 24, 1)" :key="`target-desc-${targetNode.id}-${index}`" :x="targetNode.x + 18" :dy="index === 0 ? 0 : 12">
                    {{ line }}
                  </tspan>
                </text>
                <g :transform="`translate(${targetNode.x + targetNode.w - 86}, ${targetNode.y + targetNode.h - 34})`">
                  <rect width="68" height="22" rx="11" class="badge-bg" :class="targetNode.status" />
                  <text x="34" y="15" text-anchor="middle" class="badge-text">
                    {{ statusLabel(targetNode.status) }}
                  </text>
                </g>
              </g>

              <g
                v-for="apiNode in level3ApiNodes"
                :key="apiNode.id"
                class="node-group"
                :class="{
                  selected: selectedTarget.type === 'API' && selectedTarget.id === apiNode.id,
                  'node-pulse': apiNode.status === 'IN_PROGRESS',
                  'search-hit': apiNode.searchHit,
                  'opacity-dim': apiNode.dimmed,
                }"
                @click="selectApi(apiNode.id)"
              >
                <rect :x="apiNode.x" :y="apiNode.y" :width="apiNode.w" :height="apiNode.h" rx="18" class="node-card" :class="apiNode.status" />
                <text :x="apiNode.x + 18" :y="apiNode.y + 24" class="node-subtitle">{{ apiNode.method }} 쨌 API</text>
                <text :x="apiNode.x + 18" :y="apiNode.y + 46" class="node-title">
                  <tspan v-for="(line, index) in svgLines(apiNode.name, 18, 2)" :key="`api-title-${apiNode.id}-${index}`" :x="apiNode.x + 18" :dy="index === 0 ? 0 : 14">
                    {{ line }}
                  </tspan>
                </text>
                <text :x="apiNode.x + 18" :y="apiNode.y + 84" class="node-description">
                  <tspan v-for="(line, index) in svgLines(apiNode.plainDescription, 24, 1)" :key="`api-desc-${apiNode.id}-${index}`" :x="apiNode.x + 18" :dy="index === 0 ? 0 : 12">
                    {{ line }}
                  </tspan>
                </text>
                <g :transform="`translate(${apiNode.x + apiNode.w - 86}, ${apiNode.y + apiNode.h - 34})`">
                  <rect width="68" height="22" rx="11" class="badge-bg" :class="apiNode.status" />
                  <text x="34" y="15" text-anchor="middle" class="badge-text">
                    {{ statusLabel(apiNode.status) }}
                  </text>
                </g>
              </g>
            </g>
          </svg>
        </div>

        <div class="canvas-hint">
          <span>흐름은 기본적으로 왼쪽에서 오른쪽으로 읽습니다.</span>
          <span>실행 중인 경로는 애니메이션으로, 실패 지점은 빨간색으로 표시됩니다.</span>
          <span>로그를 클릭하면 해당 노드, 연결선, API가 강조됩니다.</span>
        </div>
      </section>

      <aside class="detail-panel">
        <div class="detail-card">
          <p class="eyebrow">상세 정보</p>

          <template v-if="selectedFeatureDetail">
            <h2>{{ selectedFeatureDetail.name }}</h2>
            <p class="muted">{{ selectedFeatureDetail.description }}</p>

            <div class="detail-section" v-if="storySteps.length">
              <h3>이 기능은 이렇게 읽습니다</h3>
              <div class="chip-list">
                <span v-for="step in storySteps" :key="`detail-${step.id}`" class="mini-pill">
                  {{ step.order }}. {{ step.text }}
                </span>
              </div>
            </div>

            <div class="detail-section">
              <h3>기본 정보</h3>
              <div class="kv">
                <div class="k">구분</div><div class="v">기능 노드</div>
                <div class="k">기능 코드</div><div class="v">{{ selectedFeatureDetail.sectionCode }}</div>
                <div class="k">Lane</div><div class="v">{{ selectedFeatureDetail.laneTitle }}</div>
                <div class="k">상태</div><div class="v">{{ statusLabel(featureStatus(selectedFeatureDetail.id)) }}</div>
                <div class="k">사용자 액션</div><div class="v">{{ selectedFeatureDetail.userAction }}</div>
                <div class="k">실행 방식</div><div class="v">{{ selectedFeatureDetail.supportsLive ? '실시간 요청 추적 가능' : '샘플 이벤트 실행' }}</div>
              </div>
            </div>

            <div class="detail-section">
              <h3>관련 주요 서비스</h3>
              <div class="chip-list">
                <span v-for="node in selectedFeatureDetail.nodes" :key="node.id" class="mini-pill type">
                  {{ node.name }}
                </span>
              </div>
            </div>

            <div class="detail-section">
              <h3>관련 API 목록</h3>
              <div class="api-list">
                <button
                  v-for="api in selectedFeatureDetail.apis"
                  :key="api.id"
                  type="button"
                  class="api-card-mini"
                  @click="selectApi(api.id)"
                >
                  <span class="api-method">{{ api.method }}</span>
                  <span class="endpoint">{{ api.endpoint }}</span>
                </button>
              </div>
            </div>

            <div class="detail-actions">
              <button type="button" class="secondary" @click="viewMode = 'level2'">서비스 흐름 보기</button>
              <button type="button" class="secondary" @click="viewMode = 'level3'">API 흐름 보기</button>
            </div>
          </template>

          <template v-else-if="selectedNodeDetail">
            <h2>{{ selectedNodeDetail.name }}</h2>
            <p class="muted">{{ selectedNodeDetail.description }}</p>

            <div class="detail-section">
              <h3>서비스 노드 정보</h3>
              <div class="kv">
                <div class="k">타입</div><div class="v">{{ nodeTypeLabel(selectedNodeDetail.nodeType) }}</div>
                <div class="k">상태</div><div class="v">{{ statusLabel(nodeStatus(selectedNodeDetail.id)) }}</div>
                <div class="k">해당 기능</div><div class="v">{{ selectedFeature?.name }}</div>
                <div class="k">설명</div><div class="v">{{ selectedNodeDetail.description }}</div>
                <div class="k">입력 요약</div><div class="v">{{ selectedNodeDetail.inputSummary || '문서 기준 별도 정보 없음' }}</div>
                <div class="k">마지막 실행 시각</div><div class="v">{{ formatTimestamp(nodeMeta(selectedNodeDetail.id).timestamp) }}</div>
              </div>
            </div>

            <div class="detail-section">
              <h3>호출하는 API</h3>
              <div class="api-list">
                <button
                  v-for="api in selectedNodeApis"
                  :key="api.id"
                  type="button"
                  class="api-card-mini"
                  @click="selectApi(api.id)"
                >
                  <span class="api-method">{{ api.method }}</span>
                  <span class="endpoint">{{ api.endpoint }}</span>
                </button>
              </div>
            </div>

            <div class="detail-section" v-if="nodeMeta(selectedNodeDetail.id).errorMessage">
              <h3>실패 정보</h3>
              <div class="kv">
                <div class="k">에러 코드</div><div class="v">{{ nodeMeta(selectedNodeDetail.id).errorCode || '-' }}</div>
                <div class="k">에러 메시지</div><div class="v">{{ nodeMeta(selectedNodeDetail.id).errorMessage }}</div>
              </div>
            </div>
          </template>

          <template v-else-if="selectedEdgeDetail">
            <h2>{{ selectedEdgeDetail.label }}</h2>
            <p class="muted">노드 간 호출, 요청, 데이터 전달을 나타내는 연결선입니다.</p>

            <div class="detail-section">
              <h3>연결선 정보</h3>
              <div class="kv">
                <div class="k">타입</div><div class="v">{{ edgeTypeLabel(selectedEdgeDetail.type) }}</div>
                <div class="k">호출 주체</div><div class="v">{{ edgeSourceName(selectedEdgeDetail) }}</div>
                <div class="k">호출 대상</div><div class="v">{{ edgeTargetName(selectedEdgeDetail) }}</div>
                <div class="k">상태</div><div class="v">{{ statusLabel(edgeStatus(selectedEdgeDetail.id)) }}</div>
                <div class="k">마지막 실행 시각</div><div class="v">{{ formatTimestamp(edgeMeta(selectedEdgeDetail.id).timestamp) }}</div>
              </div>
            </div>

            <div class="detail-section" v-if="edgeMeta(selectedEdgeDetail.id).errorMessage">
              <h3>실패 정보</h3>
              <div class="kv">
                <div class="k">에러 코드</div><div class="v">{{ edgeMeta(selectedEdgeDetail.id).errorCode || '-' }}</div>
                <div class="k">에러 메시지</div><div class="v">{{ edgeMeta(selectedEdgeDetail.id).errorMessage }}</div>
              </div>
            </div>
          </template>

          <template v-else-if="selectedApiDetail">
            <h2>{{ selectedApiDetail.name }}</h2>
            <p class="muted">{{ selectedApiDetail.description }}</p>

            <div class="detail-section">
              <h3>API 상세</h3>
              <div class="kv">
                <div class="k">Method</div><div class="v">{{ selectedApiDetail.method }}</div>
                <div class="k">Endpoint</div><div class="v endpoint">{{ selectedApiDetail.endpoint }}</div>
                <div class="k">호출 주체</div><div class="v">{{ selectedApiDetail.caller }}</div>
                <div class="k">호출 대상</div><div class="v">{{ selectedApiDetail.callee }}</div>
                <div class="k">입력 요약</div><div class="v">{{ selectedApiDetail.inputSummary }}</div>
                <div class="k">출력 요약</div><div class="v">{{ selectedApiDetail.outputSummary }}</div>
                <div class="k">인증 필요</div><div class="v">{{ selectedApiDetail.requiresAuth ? '예' : '아니오' }}</div>
                <div class="k">현재 상태</div><div class="v">{{ statusLabel(apiStatus(selectedApiDetail.id)) }}</div>
                <div class="k">마지막 실행 시각</div><div class="v">{{ formatTimestamp(apiMeta(selectedApiDetail.id).timestamp) }}</div>
              </div>
            </div>

            <div class="detail-section">
              <h3>실패 조건</h3>
              <div class="chip-list">
                <span v-for="condition in selectedApiDetail.failureConditions" :key="condition" class="mini-pill warn">
                  {{ condition }}
                </span>
              </div>
            </div>

            <div class="detail-section" v-if="apiMeta(selectedApiDetail.id).errorMessage">
              <h3>실패 정보</h3>
              <div class="kv">
                <div class="k">에러 코드</div><div class="v">{{ apiMeta(selectedApiDetail.id).errorCode || '-' }}</div>
                <div class="k">에러 메시지</div><div class="v">{{ apiMeta(selectedApiDetail.id).errorMessage }}</div>
              </div>
            </div>
          </template>

          <template v-else>
            <h2>요소를 선택해 주세요</h2>
            <p class="muted">기능, 서비스 노드, 연결선, API를 클릭하면 상세 정보가 이 패널에 표시됩니다.</p>
          </template>
        </div>
      </aside>
    </main>

    <section v-if="showLogsPanel" class="logs-panel">
      <div class="logs-header">
        <h2>실행 이벤트 로그</h2>
        <div>
          <span class="mini-pill">이벤트 {{ logs.length }}건</span>
          <button type="button" class="ghost" @click="clearLogs">로그 비우기</button>
        </div>
      </div>

      <div class="log-table">
        <div class="log-row header-row">
          <div>시간</div>
          <div>traceId</div>
          <div>단계</div>
          <div>이벤트 타입</div>
          <div>상태</div>
          <div>메시지</div>
          <div>에러</div>
        </div>

        <button
          v-for="log in logs"
          :key="log.eventId"
          type="button"
          class="log-row"
          @click="focusLogTarget(log)"
        >
          <div class="log-cell mono">{{ formatTimeOnly(log.timestamp) }}</div>
          <div class="log-cell mono">{{ log.traceId }}</div>
          <div class="log-cell">{{ log.label }}</div>
          <div class="log-cell">{{ eventTypeLabel(log.eventType) }}</div>
          <div class="log-cell">
            <span class="status-pill compact" :class="log.status">{{ statusLabel(log.status) }}</span>
          </div>
          <div class="log-cell">{{ displayLogMessage(log) }}</div>
          <div class="log-cell mono">{{ log.errorCode || log.errorMessage || '-' }}</div>
        </button>

        <div v-if="logs.length === 0" class="empty-log">
          아직 실행 이벤트가 없습니다. 기능을 선택하고 실행 버튼을 누르면 로그가 시간순으로 쌓입니다.
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { architectureWorkflowCatalog, NODE_TYPES, STATUS } from '@/data/architectureWorkflowCatalog'
import { subscribeWorkflowEvents } from '@/lib/workflowChannel'

const legendItems = [
  { status: STATUS.NONE, label: '상태없음' },
  { status: STATUS.IN_PROGRESS, label: '진행중' },
  { status: STATUS.SUCCESS, label: '성공' },
  { status: STATUS.FAILED, label: '실패' },
]

const scenarioOptions = [
  { value: 'AUTO', label: '자동 선택' },
  { value: 'LIVE', label: '실시간 요청 추적' },
  { value: 'SAMPLE_SUCCESS', label: '샘플 성공' },
  { value: 'SAMPLE_FAILURE', label: '샘플 실패' },
]

const nodeTypeOptions = [
  { value: NODE_TYPES.USER_FEATURE, label: '사용자 기능' },
  { value: NODE_TYPES.UI_SCREEN, label: '사용자 화면' },
  { value: NODE_TYPES.FRONTEND_COMPONENT, label: '브라우저 처리' },
  { value: NODE_TYPES.BFF, label: '중간 전달 계층' },
  { value: NODE_TYPES.BACKEND_SERVICE, label: '서버 처리' },
  { value: NODE_TYPES.API, label: 'API' },
  { value: NODE_TYPES.DATABASE, label: '데이터 저장소' },
  { value: NODE_TYPES.QUEUE, label: '비동기 큐' },
  { value: NODE_TYPES.EXTERNAL_SYSTEM, label: '외부 시스템' },
]

const featureOptions = architectureWorkflowCatalog.features
const featureMap = new Map(featureOptions.map((feature) => [feature.id, feature]))
const nodeToFeatureMap = new Map()
const edgeToFeatureMap = new Map()
const apiToFeatureMap = new Map()
const nodeMap = new Map()
const edgeMap = new Map()
const apiMap = new Map()

featureOptions.forEach((feature) => {
  feature.nodes.forEach((node) => {
    nodeToFeatureMap.set(node.id, feature.id)
    nodeMap.set(node.id, node)
  })
  feature.edges.forEach((edge) => {
    edgeToFeatureMap.set(edge.id, feature.id)
    edgeMap.set(edge.id, edge)
  })
  feature.apis.forEach((api) => {
    apiToFeatureMap.set(api.id, feature.id)
    apiMap.set(api.id, api)
  })
})

const selectedFeatureId = ref(featureOptions[0]?.id || '')
const selectedScenario = ref('AUTO')
const viewMode = ref('level1')
const searchText = ref('')
const statusFilter = ref('ALL')
const nodeTypeFilter = ref('ALL')
const showApiNodes = ref(true)
const failedOnly = ref(false)
const showStoryStrip = ref(false)
const showLogsPanel = ref(false)
const MIN_ZOOM = 0.7
const MAX_ZOOM = 1.8
const ZOOM_STEP = 0.1
const zoomLevel = ref(1)
const currentTraceId = ref('')
const currentTraceStartedAt = ref(0)
const logs = ref([])
const selectedTarget = ref({ type: 'FEATURE', id: featureOptions[0]?.id || '' })
const nodeStateMap = ref({})
const edgeStateMap = ref({})
const apiStateMap = ref({})
const featureStateMap = ref({})
const trackedWindowClosed = ref(true)
const openError = ref('')
const lastLiveEventAt = ref(0)

let unsubscribe = null
let trackedWindow = null
let closePollTimer = null
let sampleTimers = []
let processedEventIds = new Set()

function createStateMeta(overrides = {}) {
  return {
    status: STATUS.NONE,
    eventType: 'RESET',
    message: '상태 없음',
    timestamp: 0,
    errorCode: '',
    errorMessage: '',
    ...overrides,
  }
}

function resetStateMaps() {
  const nextNodeStateMap = {}
  const nextEdgeStateMap = {}
  const nextApiStateMap = {}
  const nextFeatureStateMap = {}

  featureOptions.forEach((feature) => {
    nextFeatureStateMap[feature.id] = createStateMeta()
    feature.nodes.forEach((node) => {
      nextNodeStateMap[node.id] = createStateMeta()
    })
    feature.edges.forEach((edge) => {
      nextEdgeStateMap[edge.id] = createStateMeta()
    })
    feature.apis.forEach((api) => {
      nextApiStateMap[api.id] = createStateMeta()
    })
  })

  nodeStateMap.value = nextNodeStateMap
  edgeStateMap.value = nextEdgeStateMap
  apiStateMap.value = nextApiStateMap
  featureStateMap.value = nextFeatureStateMap
}

resetStateMaps()

const selectedFeature = computed(() => featureMap.get(selectedFeatureId.value) || null)

const currentApiNodes = computed(() => {
  if (!selectedFeature.value) return []
  if (viewMode.value === 'level3' && selectedTarget.value.type === 'NODE') {
    const node = nodeMap.get(selectedTarget.value.id)
    if (node?.apiIds?.length) {
      return node.apiIds.map((apiId) => apiMap.get(apiId)).filter(Boolean)
    }
  }
  return selectedFeature.value.apis
})

const laneFeatureGroups = computed(() => {
  return architectureWorkflowCatalog.lanes
    .map((lane) => ({
      ...lane,
      features: filteredFeatures.value.filter((feature) => feature.laneId === lane.id),
    }))
    .filter((lane) => lane.features.length > 0)
})

function statusPriority(status) {
  if (status === STATUS.FAILED) return 4
  if (status === STATUS.IN_PROGRESS) return 3
  if (status === STATUS.SUCCESS) return 2
  return 1
}

function statusLabel(status) {
  return legendItems.find((item) => item.status === status)?.label || '상태없음'
}

function eventTypeLabel(type) {
  if (type === 'START') return '시작'
  if (type === 'SUCCESS') return '성공'
  if (type === 'FAIL') return '실패'
  if (type === 'RESET') return '초기화'
  return type
}

function nodeTypeLabel(type) {
  return nodeTypeOptions.find((item) => item.value === type)?.label || type
}

function plainNodeRole(nodeType) {
  if (nodeType === NODE_TYPES.UI_SCREEN) return '사용자가 직접 보는 화면입니다.'
  if (nodeType === NODE_TYPES.FRONTEND_COMPONENT) return '브라우저 내부에서 입력을 정리하는 단계입니다.'
  if (nodeType === NODE_TYPES.BFF) return '브라우저와 서버 사이 요청을 연결하는 단계입니다.'
  if (nodeType === NODE_TYPES.BACKEND_SERVICE) return '업무 규칙을 실제로 처리하는 서버 단계입니다.'
  if (nodeType === NODE_TYPES.DATABASE) return '데이터를 저장하거나 조회하는 단계입니다.'
  if (nodeType === NODE_TYPES.QUEUE) return '비동기 작업을 주고받는 단계입니다.'
  if (nodeType === NODE_TYPES.EXTERNAL_SYSTEM) return '외부 시스템과 연결되는 단계입니다.'
  return '내부 처리 흐름을 담당하는 단계입니다.'
}

function truncateText(text, maxLength = 34) {
  const source = String(text || '').replace(/\s+/g, ' ').trim()
  if (!source) return ''
  if (source.length <= maxLength) return source
  return `${source.slice(0, maxLength - 1)}…`
}

function svgLines(text, maxChars = 16, maxLines = 2) {
  const source = String(text || '').replace(/\s+/g, ' ').trim()
  if (!source) return []

  const pushChunked = (value, lines) => {
    let cursor = 0
    while (cursor < value.length) {
      lines.push(value.slice(cursor, cursor + maxChars))
      cursor += maxChars
    }
  }

  const lines = []
  const words = source.split(' ').filter(Boolean)

  if (words.length <= 1) {
    pushChunked(source, lines)
  } else {
    let current = ''
    words.forEach((word) => {
      if (word.length > maxChars) {
        if (current) {
          lines.push(current)
          current = ''
        }
        pushChunked(word, lines)
        return
      }
      const candidate = current ? `${current} ${word}` : word
      if (candidate.length <= maxChars) {
        current = candidate
      } else {
        if (current) lines.push(current)
        current = word
      }
    })
    if (current) lines.push(current)
  }

  if (lines.length <= maxLines) return lines
  const clipped = lines.slice(0, maxLines)
  clipped[maxLines - 1] = truncateText(clipped[maxLines - 1], maxChars)
  return clipped
}

function buildNodeCardDescription(node) {
  if (node.nodeType === NODE_TYPES.UI_SCREEN) {
    return '사용자 입력이 시작됩니다.'
  }
  if (node.nodeType === NODE_TYPES.FRONTEND_COMPONENT) {
    return '입력을 정리해 다음 단계로 넘깁니다.'
  }
  if (node.nodeType === NODE_TYPES.BFF) {
    return '요청을 묶어 서버로 전달합니다.'
  }
  if (node.nodeType === NODE_TYPES.BACKEND_SERVICE) {
    return truncateText(node.description || '업무 규칙을 처리합니다.', 18)
  }
  if (node.nodeType === NODE_TYPES.DATABASE) {
    return '데이터를 저장하거나 조회합니다.'
  }
  if (node.nodeType === NODE_TYPES.QUEUE) {
    return '비동기 작업을 이어줍니다.'
  }
  if (node.nodeType === NODE_TYPES.EXTERNAL_SYSTEM) {
    return truncateText(node.description || '외부 시스템과 연결됩니다.', 18)
  }
  return truncateText(node.description || '처리 단계입니다.', 18)
}

function buildApiCardDescription(api) {
  return truncateText(api.description || `${api.method} ${api.endpoint} 요청`, 20)
}

function buildStoryText(node) {
  return `${node.name}: ${truncateText(buildNodeCardDescription(node), 28)}`
}

function edgeTypeLabel(type) {
  if (type === 'HTTP_REQUEST') return 'HTTP 요청'
  if (type === 'INTERNAL_CALL') return '내부 호출'
  if (type === 'DB_QUERY') return 'DB 접근'
  if (type === 'EVENT_PUBLISH') return '이벤트 발행'
  if (type === 'EVENT_SUBSCRIBE') return '이벤트 구독'
  if (type === 'EXTERNAL_API_CALL') return '외부 API 호출'
  return type
}

function compactEdgeLabel(edge) {
  return truncateText(edge?.label || '연결', 12)
}

function parseViewBoxSize(viewBox) {
  const parts = String(viewBox || '')
    .split(/\s+/)
    .map((value) => Number(value))
  if (parts.length !== 4 || parts.some((value) => Number.isNaN(value))) {
    return { width: 1320, height: 720 }
  }
  return { width: parts[2], height: parts[3] }
}

function nodeStatus(nodeId) {
  return nodeStateMap.value[nodeId]?.status || STATUS.NONE
}

function edgeStatus(edgeId) {
  return edgeStateMap.value[edgeId]?.status || STATUS.NONE
}

function apiStatus(apiId) {
  return apiStateMap.value[apiId]?.status || STATUS.NONE
}

function featureStatus(featureId) {
  return featureStateMap.value[featureId]?.status || STATUS.NONE
}

function nodeMeta(nodeId) {
  return nodeStateMap.value[nodeId] || createStateMeta()
}

function edgeMeta(edgeId) {
  return edgeStateMap.value[edgeId] || createStateMeta()
}

function apiMeta(apiId) {
  return apiStateMap.value[apiId] || createStateMeta()
}

function featureMeta(featureId) {
  return featureStateMap.value[featureId] || createStateMeta()
}

function entryMatchesSearch(text) {
  if (!searchText.value.trim()) return true
  return String(text || '').toLowerCase().includes(searchText.value.trim().toLowerCase())
}

function featureMatchesSearch(feature) {
  const apiText = feature.apis.map((api) => `${api.name} ${api.endpoint}`).join(' ')
  const nodeText = feature.nodes.map((node) => `${node.name} ${node.description}`).join(' ')
  const logText = logs.value
    .filter((log) => log.featureId === feature.id)
    .map((log) => `${log.label} ${log.message} ${log.errorCode} ${log.errorMessage}`)
    .join(' ')
  return entryMatchesSearch(`${feature.name} ${feature.description} ${apiText} ${nodeText} ${logText}`)
}

function featureMatchesStatus(feature) {
  const status = featureStatus(feature.id)
  if (failedOnly.value && status !== STATUS.FAILED) return false
  if (statusFilter.value === 'ALL') return true
  return status === statusFilter.value
}

const filteredFeatures = computed(() =>
  featureOptions.filter((feature) => featureMatchesSearch(feature) && featureMatchesStatus(feature)),
)

function shouldDimByFilters(status, type) {
  if (failedOnly.value && status !== STATUS.FAILED) return true
  if (statusFilter.value !== 'ALL' && status !== statusFilter.value) return true
  if (type && nodeTypeFilter.value !== 'ALL' && type !== nodeTypeFilter.value) return true
  return false
}

function selectedTargetEntity() {
  if (selectedTarget.value.type === 'FEATURE') return featureMap.get(selectedTarget.value.id) || null
  if (selectedTarget.value.type === 'NODE') return nodeMap.get(selectedTarget.value.id) || null
  if (selectedTarget.value.type === 'EDGE') return edgeMap.get(selectedTarget.value.id) || null
  if (selectedTarget.value.type === 'API') return apiMap.get(selectedTarget.value.id) || null
  return null
}

const selectedFeatureDetail = computed(() =>
  selectedTarget.value.type === 'FEATURE' ? featureMap.get(selectedTarget.value.id) || null : null,
)

const selectedNodeDetail = computed(() =>
  selectedTarget.value.type === 'NODE' ? nodeMap.get(selectedTarget.value.id) || null : null,
)

const selectedEdgeDetail = computed(() =>
  selectedTarget.value.type === 'EDGE' ? edgeMap.get(selectedTarget.value.id) || null : null,
)

const selectedApiDetail = computed(() =>
  selectedTarget.value.type === 'API' ? apiMap.get(selectedTarget.value.id) || null : null,
)

const selectedTargetLabel = computed(() => selectedTargetEntity()?.name || selectedTargetEntity()?.label || '')

const overallStatusLabel = computed(() => {
  if (!selectedFeature.value) return '상태없음'
  return `전체 상태 · ${statusLabel(featureStatus(selectedFeature.value.id))}`
})

const windowStateLabel = computed(() => {
  if (!selectedFeature.value?.supportsLive) return '샘플 실행'
  if (trackedWindowClosed.value) return '미연결'
  return '실시간 연결'
})

const selectedNodeApis = computed(() => {
  if (!selectedNodeDetail.value) return []
  return selectedNodeDetail.value.apiIds.map((apiId) => apiMap.get(apiId)).filter(Boolean)
})

const storySteps = computed(() => {
  if (!selectedFeature.value) return []
  return selectedFeature.value.nodes.slice(0, 4).map((node, index) => ({
    id: node.id,
    order: index + 1,
    title: node.name,
    text: buildStoryText(node),
  }))
})

watch(selectedFeatureId, (featureId) => {
  if (!featureId) return
  selectedTarget.value = { type: 'FEATURE', id: featureId }
  if (viewMode.value !== 'level1') {
    viewMode.value = 'level2'
  }
  if (selectedScenario.value === 'AUTO') {
    return
  }
  if (!selectedFeature.value?.supportsLive && selectedScenario.value === 'LIVE') {
    selectedScenario.value = 'SAMPLE_SUCCESS'
  }
})

function currentScenarioMode() {
  if (selectedScenario.value !== 'AUTO') return selectedScenario.value
  return selectedFeature.value?.supportsLive ? 'LIVE' : 'SAMPLE_SUCCESS'
}

function formatTimestamp(timestamp) {
  if (!timestamp) return '없음'
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'short',
    timeStyle: 'medium',
  }).format(new Date(timestamp))
}

function formatTimeOnly(timestamp) {
  if (!timestamp) return '-'
  return new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp))
}

function displayLogMessage(log) {
  const baseLabel = log?.label || log?.targetId || '단계'
  if (log?.eventType === 'START') return `${baseLabel} 시작`
  if (log?.eventType === 'SUCCESS') return `${baseLabel} 성공`
  if (log?.eventType === 'FAIL') return `${baseLabel} 실패`
  if (log?.eventType === 'RESET') return `${baseLabel} 초기화`
  return baseLabel
}

function generateTraceId() {
  const stamp = new Date()
    .toISOString()
    .replace(/[-:.TZ]/g, '')
    .slice(0, 14)
  return `trace-${stamp}-${Math.random().toString(36).slice(2, 6)}`
}

function clearLogs() {
  logs.value = []
}

function resetExecutionState() {
  sampleTimers.forEach((timer) => clearTimeout(timer))
  sampleTimers = []
  processedEventIds = new Set()
  currentTraceId.value = ''
  currentTraceStartedAt.value = 0
  lastLiveEventAt.value = 0
  resetStateMaps()
  clearLogs()
}

function zoomIn() {
  zoomLevel.value = Math.min(MAX_ZOOM, Number((zoomLevel.value + ZOOM_STEP).toFixed(2)))
}

function zoomOut() {
  zoomLevel.value = Math.max(MIN_ZOOM, Number((zoomLevel.value - ZOOM_STEP).toFixed(2)))
}

function resetZoom() {
  zoomLevel.value = 1
}

function isAllowedTransition(previousStatus, nextStatus) {
  if (previousStatus === STATUS.NONE) return nextStatus === STATUS.IN_PROGRESS || nextStatus === STATUS.SUCCESS || nextStatus === STATUS.FAILED
  if (previousStatus === STATUS.IN_PROGRESS) return nextStatus === STATUS.SUCCESS || nextStatus === STATUS.FAILED
  if (previousStatus === STATUS.SUCCESS || previousStatus === STATUS.FAILED) return nextStatus === STATUS.NONE
  return false
}

function updateStateBucket(bucketRef, id, payload) {
  const current = bucketRef.value[id] || createStateMeta()
  if (payload.status !== current.status && !isAllowedTransition(current.status, payload.status)) {
    return false
  }

  bucketRef.value = {
    ...bucketRef.value,
    [id]: {
      ...current,
      ...payload,
    },
  }
  return true
}

function recomputeFeatureStatus(featureId) {
  const feature = featureMap.get(featureId)
  if (!feature) return
  const statuses = [
    ...feature.nodes.map((node) => nodeStatus(node.id)),
    ...feature.edges.map((edge) => edgeStatus(edge.id)),
    ...feature.apis.map((api) => apiStatus(api.id)),
  ]

  let nextStatus = STATUS.NONE
  if (statuses.some((status) => status === STATUS.FAILED)) {
    nextStatus = STATUS.FAILED
  } else if (statuses.some((status) => status === STATUS.IN_PROGRESS)) {
    nextStatus = STATUS.IN_PROGRESS
  } else if (statuses.length && statuses.every((status) => status === STATUS.SUCCESS)) {
    nextStatus = STATUS.SUCCESS
  } else if (statuses.some((status) => status === STATUS.SUCCESS)) {
    nextStatus = STATUS.IN_PROGRESS
  }

  const mostRecent = [...feature.nodes.map((node) => nodeMeta(node.id)), ...feature.edges.map((edge) => edgeMeta(edge.id)), ...feature.apis.map((api) => apiMeta(api.id))]
    .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))[0]

  featureStateMap.value = {
    ...featureStateMap.value,
    [featureId]: createStateMeta({
      ...(featureStateMap.value[featureId] || {}),
      status: nextStatus,
      eventType: mostRecent?.eventType || 'RESET',
      message: mostRecent?.message || '상태 없음',
      timestamp: mostRecent?.timestamp || 0,
      errorCode: mostRecent?.errorCode || '',
      errorMessage: mostRecent?.errorMessage || '',
    }),
  }
}

function pushLog(entry) {
  logs.value = [...logs.value, entry].sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0))
}

function emitExecutionEvent(event) {
  if (!currentTraceId.value || event.traceId !== currentTraceId.value) return
  if (processedEventIds.has(event.eventId)) return
  processedEventIds.add(event.eventId)

  let handled = false

  if (event.targetType === 'FEATURE') {
    handled = updateStateBucket(featureStateMap, event.targetId, {
      status: event.status,
      eventType: event.eventType,
      message: event.message,
      timestamp: event.timestamp,
      errorCode: event.errorCode || '',
      errorMessage: event.errorMessage || '',
    })
  }

  if (event.targetType === 'NODE') {
    handled = updateStateBucket(nodeStateMap, event.targetId, {
      status: event.status,
      eventType: event.eventType,
      message: event.message,
      timestamp: event.timestamp,
      errorCode: event.errorCode || '',
      errorMessage: event.errorMessage || '',
    })
  }

  if (event.targetType === 'EDGE') {
    handled = updateStateBucket(edgeStateMap, event.targetId, {
      status: event.status,
      eventType: event.eventType,
      message: event.message,
      timestamp: event.timestamp,
      errorCode: event.errorCode || '',
      errorMessage: event.errorMessage || '',
    })
  }

  if (event.targetType === 'API') {
    handled = updateStateBucket(apiStateMap, event.targetId, {
      status: event.status,
      eventType: event.eventType,
      message: event.message,
      timestamp: event.timestamp,
      errorCode: event.errorCode || '',
      errorMessage: event.errorMessage || '',
    })
  }

  if (!handled) return

  const featureId =
    event.featureId ||
    (event.targetType === 'FEATURE' ? event.targetId : nodeToFeatureMap.get(event.targetId) || edgeToFeatureMap.get(event.targetId) || apiToFeatureMap.get(event.targetId))

  if (featureId) {
    recomputeFeatureStatus(featureId)
  }

  pushLog({
    eventId: event.eventId,
    traceId: event.traceId,
    featureId,
    targetType: event.targetType,
    targetId: event.targetId,
    eventType: event.eventType,
    status: event.status,
    timestamp: event.timestamp,
    message: event.message,
    errorCode: event.errorCode || '',
    errorMessage: event.errorMessage || '',
    label: event.label || event.targetId,
  })
}

function selectFeature(featureId, nextMode = 'level2') {
  selectedFeatureId.value = featureId
  selectedTarget.value = { type: 'FEATURE', id: featureId }
  viewMode.value = nextMode
}

function selectNode(nodeId, nextMode = 'level2') {
  selectedTarget.value = { type: 'NODE', id: nodeId }
  viewMode.value = nextMode
}

function selectEdge(edgeId, nextMode = 'level2') {
  selectedTarget.value = { type: 'EDGE', id: edgeId }
  viewMode.value = nextMode
}

function selectApi(apiId) {
  selectedTarget.value = { type: 'API', id: apiId }
  viewMode.value = 'level3'
}

function selectSyntheticRoot() {
  selectedTarget.value = { type: 'FEATURE', id: selectedFeatureId.value }
}

function edgeSourceName(edge) {
  return nodeMap.get(edge.source)?.name || edge.source
}

function edgeTargetName(edge) {
  return nodeMap.get(edge.target)?.name || edge.target
}

function focusLogTarget(log) {
  if (log.targetType === 'FEATURE') {
    selectFeature(log.targetId, 'level2')
    return
  }
  if (log.targetType === 'NODE') {
    selectNode(log.targetId, 'level2')
    return
  }
  if (log.targetType === 'EDGE') {
    selectEdge(log.targetId, viewMode.value === 'level1' ? 'level2' : viewMode.value)
    return
  }
  if (log.targetType === 'API') {
    selectApi(log.targetId)
  }
}

function orthogonalHorizontalPath(startX, startY, endX, endY, laneX) {
  return `M ${startX} ${startY} H ${laneX} V ${endY} H ${endX}`
}

function orthogonalVerticalPath(startX, startY, endX, endY, laneY) {
  return `M ${startX} ${startY} V ${laneY} H ${endX} V ${endY}`
}

const CONNECTOR_GAP = 16

function buildLevel1Layout() {
  const features = filteredFeatures.value
  const lanes = architectureWorkflowCatalog.lanes
    .map((lane) => ({
      ...lane,
      features: features.filter((feature) => feature.laneId === lane.id),
    }))
    .filter((lane) => lane.features.length > 0)

  const cardWidth = 236
  const cardHeight = 102
  const laneWidth = 314
  const laneGap = 58
  const laneStartX = 60
  const laneStartY = 172
  const lanePaddingX = 20
  const lanePaddingTop = 44
  const lanePaddingBottom = 22
  const innerGap = 30
  const rootCenterX = Math.max(540, laneStartX + ((lanes.length * laneWidth + Math.max(0, lanes.length - 1) * laneGap) / 2))
  const rootBottomY = 124

  const groups = lanes.map((lane, laneIndex) => {
    const x = laneStartX + laneIndex * (laneWidth + laneGap)
    const height = lanePaddingTop + lane.features.length * cardHeight + Math.max(0, lane.features.length - 1) * innerGap + lanePaddingBottom
    return {
      id: `level1-group-${lane.id}`,
      laneId: lane.id,
      title: lane.title,
      subtitle: truncateText(lane.subtitle || lane.description, 30),
      badge: lane.badge,
      x,
      y: laneStartY,
      w: laneWidth,
      h: height,
    }
  })

  const nodes = []
  groups.forEach((group) => {
    const lane = lanes.find((item) => item.id === group.laneId)
    lane.features.forEach((feature, featureIndex) => {
      const x = group.x + lanePaddingX
      const y = group.y + lanePaddingTop + featureIndex * (cardHeight + innerGap)
      const status = featureStatus(feature.id)
      nodes.push({
        id: feature.id,
        x,
        y,
        w: cardWidth,
        h: cardHeight,
        name: feature.name,
        badge: feature.laneBadge,
        description: truncateText(feature.description, 34),
        status,
        dimmed: shouldDimByFilters(status),
        searchHit: searchText.value && featureMatchesSearch(feature),
      })
    })
  })

  const edges = nodes.map((node, edgeIndex) => {
    const targetX = node.x + node.w / 2
    const targetY = node.y - CONNECTOR_GAP
    const branchY = rootBottomY + 34 + edgeIndex * 14
    const path = orthogonalVerticalPath(rootCenterX, rootBottomY + CONNECTOR_GAP, targetX, targetY, branchY)
    return {
      id: `level1-edge-${node.id}`,
      source: 'feature-root',
      target: node.id,
      path,
      label: node.name,
      status: node.status,
      searchHit: node.searchHit,
      dimmed: node.dimmed,
    }
  })

  const totalWidth = laneStartX + lanes.length * laneWidth + Math.max(0, lanes.length - 1) * laneGap + 60
  const totalHeight = groups.length ? Math.max(...groups.map((group) => group.y + group.h)) + 40 : 520
  return {
    groups,
    nodes,
    edges,
    rootCenterX,
    viewBox: `0 0 ${Math.max(1080, totalWidth)} ${Math.max(640, totalHeight)}`,
  }
}

function stageKeyForNode(node) {
  switch (node.nodeType) {
    case NODE_TYPES.UI_SCREEN:
      return 'ui'
    case NODE_TYPES.FRONTEND_COMPONENT:
      return 'frontend'
    case NODE_TYPES.BFF:
      return 'bff'
    case NODE_TYPES.BACKEND_SERVICE:
      return 'service'
    case NODE_TYPES.DATABASE:
    case NODE_TYPES.QUEUE:
      return 'data'
    case NODE_TYPES.EXTERNAL_SYSTEM:
      return 'external'
    default:
      return 'service'
  }
}

function buildLevel2Layout() {
  if (!selectedFeature.value) {
    return { groups: [], nodes: [], edges: [], viewBox: '0 0 1260 720' }
  }

  const stageDefinitions = [
    { key: 'ui', title: '\uC0AC\uC6A9\uC790 \uD654\uBA74', subtitle: '\uC0AC\uC6A9\uC790 \uC785\uB825\uC774 \uC2DC\uC791\uB418\uB294 \uACF3', x: 70, w: 240 },
    { key: 'frontend', title: '\uBE0C\uB77C\uC6B0\uC800 \uCC98\uB9AC', subtitle: '\uC785\uB825\uC744 \uC815\uB9AC\uD558\uB294 \uB2E8\uACC4', x: 380, w: 240 },
    { key: 'bff', title: '\uC911\uAC04 \uC804\uB2EC', subtitle: '\uC694\uCCAD\uC744 \uC11C\uBC84\uB85C \uB118\uAE30\uB294 \uB2E8\uACC4', x: 690, w: 240 },
    { key: 'service', title: '\uC11C\uBC84 \uCC98\uB9AC', subtitle: '\uC5C5\uBB34 \uADDC\uCE59\uC744 \uCC98\uB9AC\uD558\uB294 \uB2E8\uACC4', x: 1000, w: 290 },
    { key: 'data', title: '\uB370\uC774\uD130 \uCC98\uB9AC', subtitle: 'DB \uB610\uB294 \uD050\uB97C \uB2E4\uB8E8\uB294 \uB2E8\uACC4', x: 1360, w: 240 },
    { key: 'external', title: '\uC678\uBD80 \uC5F0\uB3D9', subtitle: '\uC678\uBD80 \uC2DC\uC2A4\uD15C\uACFC \uC5F0\uACB0\uB418\uB294 \uB2E8\uACC4', x: 1670, w: 240 },
  ]

  const stageBuckets = Object.fromEntries(stageDefinitions.map((stage) => [stage.key, []]))
  selectedFeature.value.nodes.forEach((node) => {
    stageBuckets[stageKeyForNode(node)].push(node)
  })

  const baseY = 116
  const cardHeight = 112
  const verticalGap = 68
  const nodes = []

  stageDefinitions.forEach((stage) => {
    stageBuckets[stage.key].forEach((node, rowIndex) => {
      const y = baseY + rowIndex * (cardHeight + verticalGap)
      const status = nodeStatus(node.id)
      nodes.push({
        ...node,
        x: stage.x + 12,
        y,
        w: stage.w - 24,
        h: cardHeight,
        stageKey: stage.key,
        rowIndex,
        stageIndex: stageDefinitions.findIndex((item) => item.key === stage.key),
        stageTitle: stage.title,
        stepOrder: selectedFeature.value.nodes.findIndex((item) => item.id === node.id) + 1,
        status,
        typeLabel: nodeTypeLabel(node.nodeType),
        plainDescription: buildNodeCardDescription(node),
        dimmed: shouldDimByFilters(status, node.nodeType),
        searchHit: entryMatchesSearch(`${node.name} ${node.description} ${node.inputSummary}`),
      })
    })
  })

  const groups = stageDefinitions.map((stage) => {
    const rows = Math.max(1, stageBuckets[stage.key].length)
    return {
      id: `level2-group-${stage.key}`,
      title: stage.title,
      subtitle: stage.subtitle,
      x: stage.x,
      y: 42,
      w: stage.w,
      h: 78 + rows * (cardHeight + verticalGap),
    }
  })

  const nodeLookup = Object.fromEntries(nodes.map((node) => [node.id, node]))
  const edges = selectedFeature.value.edges.map((edge) => {
    const source = nodeLookup[edge.source]
    const target = nodeLookup[edge.target]
    const startX = source.x + source.w + CONNECTOR_GAP
    const startY = source.y + source.h / 2
    const endX = target.x - CONNECTOR_GAP
    const endY = target.y + target.h / 2
    const gap = Math.max(72, endX - startX)
    const laneOffset = 42 + (((source.rowIndex || 0) + (target.rowIndex || 0)) % 4) * 24
    const laneX = startX + Math.min(gap - 24, laneOffset)
    const status = edgeStatus(edge.id)
    return {
      ...edge,
      path: orthogonalHorizontalPath(startX, startY, endX, endY, laneX),
      labelX: laneX,
      labelY: startY < endY ? startY + (endY - startY) / 2 : endY + (startY - endY) / 2,
      status,
      dimmed: shouldDimByFilters(status),
      searchHit: entryMatchesSearch(`${edge.label} ${edge.type}`),
    }
  })

  const totalHeight = Math.max(...groups.map((group) => group.y + group.h)) + 40
  return {
    groups,
    nodes,
    edges,
    viewBox: `0 0 1990 ${Math.max(760, totalHeight)}`,
  }
}

function buildLevel3Layout() {
  if (!selectedFeature.value) {
    return { groups: [], rootNode: null, apiNodes: [], targetNodes: [], edges: [], viewBox: '0 0 1360 720' }
  }

  const rootSource = selectedNodeDetail.value || selectedFeature.value.nodes[0]
  const rootStatus = selectedNodeDetail.value ? nodeStatus(rootSource.id) : featureStatus(selectedFeature.value.id)
  const rootNode = {
    id: rootSource.id,
    x: 100,
    y: 258,
    w: 300,
    h: 112,
    name: rootSource.name,
    description: buildNodeCardDescription(rootSource),
    typeLabel: selectedNodeDetail.value ? nodeTypeLabel(rootSource.nodeType) : '기능 시작점',
    status: rootStatus,
  }

  const apiList = showApiNodes.value ? currentApiNodes.value : []
  const cardWidth = 380
  const cardHeight = 112
  const gapY = 66
  const apiNodes = apiList.map((api, index) => {
    const y = 112 + index * (cardHeight + gapY)
    const status = apiStatus(api.id)
    return {
      ...api,
      rowIndex: index,
      x: 600,
      y,
      w: cardWidth,
      h: cardHeight,
      status,
      plainDescription: buildApiCardDescription(api),
      dimmed: shouldDimByFilters(status, NODE_TYPES.API),
      searchHit: entryMatchesSearch(`${api.name} ${api.endpoint} ${api.description}`),
    }
  })

  const calleeNames = Array.from(new Set(apiList.map((api) => api.callee)))
  const targetNodes = calleeNames.map((callee, index) => ({
    id: `${selectedFeature.value.id}-callee-${index + 1}`,
    name: callee,
    description: `${callee}에서 실제 요청을 처리합니다.`,
    typeLabel: '서버 처리 대상',
    rowIndex: index,
    x: 1180,
    y: 168 + index * 178,
    w: 320,
    h: 102,
    status: apiList.some((api) => api.callee === callee && apiStatus(api.id) === STATUS.FAILED)
      ? STATUS.FAILED
      : apiList.some((api) => api.callee === callee && apiStatus(api.id) === STATUS.IN_PROGRESS)
        ? STATUS.IN_PROGRESS
        : apiList.some((api) => api.callee === callee && apiStatus(api.id) === STATUS.SUCCESS)
          ? STATUS.SUCCESS
          : STATUS.NONE,
    plainDescription: '요청을 실제로 처리하는 서버입니다.',
  }))

  const targetNodeMap = Object.fromEntries(targetNodes.map((node) => [node.name, node]))
  const edges = []

  apiNodes.forEach((apiNode) => {
    const api = apiMap.get(apiNode.id)
    const targetNode = targetNodeMap[api.callee]
    const leftStartX = rootNode.x + rootNode.w + CONNECTOR_GAP
    const leftStartY = rootNode.y + rootNode.h / 2
    const leftEndX = apiNode.x - CONNECTOR_GAP
    const leftEndY = apiNode.y + apiNode.h / 2
    const leftGap = Math.max(84, leftEndX - leftStartX)
    const leftLaneX = leftStartX + Math.min(leftGap - 28, 52 + (apiNode.rowIndex % 4) * 24)

    edges.push({
      id: `${selectedFeature.value.id}-api-source-${apiNode.id}`,
      source: rootNode.id,
      target: apiNode.id,
      type: 'HTTP_REQUEST',
      label: api.method,
      path: orthogonalHorizontalPath(leftStartX, leftStartY, leftEndX, leftEndY, leftLaneX),
      status: apiNode.status,
      dimmed: shouldDimByFilters(apiNode.status),
      searchHit: apiNode.searchHit,
    })

    if (!targetNode) return
    const rightStartX = apiNode.x + apiNode.w + CONNECTOR_GAP
    const rightStartY = apiNode.y + apiNode.h / 2
    const rightEndX = targetNode.x - CONNECTOR_GAP
    const rightEndY = targetNode.y + targetNode.h / 2
    const rightGap = Math.max(84, rightEndX - rightStartX)
    const rightLaneX = rightStartX + Math.min(rightGap - 28, 52 + (((apiNode.rowIndex || 0) + (targetNode.rowIndex || 0)) % 4) * 24)
    edges.push({
      id: `${selectedFeature.value.id}-api-target-${apiNode.id}`,
      source: apiNode.id,
      target: targetNode.id,
      type: 'HTTP_REQUEST',
      label: api.method,
      path: orthogonalHorizontalPath(rightStartX, rightStartY, rightEndX, rightEndY, rightLaneX),
      status: apiNode.status,
      dimmed: shouldDimByFilters(apiNode.status),
      searchHit: apiNode.searchHit,
    })
  })

  const groups = [
    { id: 'level3-source', title: '\uC694\uCCAD \uC2DC\uC791\uC810', subtitle: '\uC5B4\uB514\uC11C \uC694\uCCAD\uC774 \uC2DC\uC791\uB418\uB294\uC9C0', x: 70, y: 42, w: 360, h: 590 },
    { id: 'level3-api', title: 'API \uD638\uCD9C', subtitle: '\uC2E4\uC81C\uB85C \uC624\uAC00\uB294 HTTP \uD638\uCD9C', x: 560, y: 42, w: 460, h: Math.max(590, 108 + apiNodes.length * 152) },
    { id: 'level3-target', title: '\uC11C\uBC84 \uCC98\uB9AC\uC810', subtitle: '\uC5B4\uB290 \uC11C\uBC84\uAC00 \uCC98\uB9AC\uD558\uB294\uC9C0', x: 1140, y: 42, w: 390, h: 590 },
  ]

  const totalHeight = Math.max(
    ...groups.map((group) => group.y + group.h),
    ...(targetNodes.length ? targetNodes.map((node) => node.y + node.h + 40) : [0]),
    ...(apiNodes.length ? apiNodes.map((node) => node.y + node.h + 40) : [0]),
  )
  return {
    groups,
    rootNode,
    apiNodes,
    targetNodes,
    edges,
    viewBox: `0 0 1780 ${Math.max(760, totalHeight)}`,
  }
}

const level1Layout = computed(() => buildLevel1Layout())
const level2Layout = computed(() => buildLevel2Layout())
const level3Layout = computed(() => buildLevel3Layout())

const level1Groups = computed(() => level1Layout.value.groups || [])
const level1RootNode = computed(() => {
  const centerX = level1Layout.value.rootCenterX || 540
  return {
    x: centerX - 130,
    y: 40,
    w: 260,
    h: 84,
    centerX,
  }
})
const level1Nodes = computed(() => level1Layout.value.nodes)
const level1Edges = computed(() => level1Layout.value.edges)
const level2Groups = computed(() => level2Layout.value.groups || [])
const level2Nodes = computed(() => level2Layout.value.nodes)
const level2Edges = computed(() => level2Layout.value.edges)
const level3Groups = computed(() => level3Layout.value.groups || [])
const level3ApiNodes = computed(() => level3Layout.value.apiNodes)
const level3TargetNodes = computed(() => level3Layout.value.targetNodes || [])
const level3Edges = computed(() => level3Layout.value.edges)
const apiRootNode = computed(() => level3Layout.value.rootNode || {
  id: '',
  x: 170,
  y: 50,
  w: 720,
  h: 96,
  name: '',
  description: '',
  typeLabel: '',
  status: STATUS.NONE,
})

const svgViewBox = computed(() => {
  if (viewMode.value === 'level1') return level1Layout.value.viewBox
  if (viewMode.value === 'level2') return level2Layout.value.viewBox
  return level3Layout.value.viewBox
})

const svgBaseSize = computed(() => parseViewBoxSize(svgViewBox.value))
const svgCanvasWidth = computed(() => Math.round(svgBaseSize.value.width * zoomLevel.value))
const svgCanvasHeight = computed(() => Math.round(svgBaseSize.value.height * zoomLevel.value))
const zoomPercent = computed(() => Math.round(zoomLevel.value * 100))

function createExecutionEvent({
  eventId,
  targetType,
  targetId,
  status,
  eventType,
  message,
  featureId,
  timestamp = Date.now(),
  errorCode = '',
  errorMessage = '',
  label = '',
}) {
  return {
    eventId,
    traceId: currentTraceId.value,
    targetType,
    targetId,
    status,
    eventType,
    message,
    featureId,
    timestamp,
    errorCode,
    errorMessage,
    label,
  }
}

function markPreviousStepsSuccess(feature, nodeIndex, timestamp) {
  for (let index = 0; index < nodeIndex; index += 1) {
    const node = feature.nodes[index]
    if (nodeStatus(node.id) === STATUS.NONE) {
      emitExecutionEvent(
        createExecutionEvent({
          eventId: `${currentTraceId.value}-${node.id}-auto-success`,
          targetType: 'NODE',
          targetId: node.id,
          status: STATUS.SUCCESS,
          eventType: 'SUCCESS',
          message: `${node.name} 완료`,
          featureId: feature.id,
          timestamp,
          label: node.name,
        }),
      )
    }
    const edge = feature.edges[index]
    if (edge && edgeStatus(edge.id) === STATUS.NONE) {
      emitExecutionEvent(
        createExecutionEvent({
          eventId: `${currentTraceId.value}-${edge.id}-auto-success`,
          targetType: 'EDGE',
          targetId: edge.id,
          status: STATUS.SUCCESS,
          eventType: 'SUCCESS',
          message: `${edge.label} 성공`,
          featureId: feature.id,
          timestamp,
          label: edge.label,
        }),
      )
    }
  }
}

function applyApiNetworkEvent(api, networkEvent) {
  if (!selectedFeature.value) return
  const feature = selectedFeature.value
  const nodeId = api.relatedNodeIds[0]
  const nodeIndex = feature.nodes.findIndex((node) => node.id === nodeId)
  const edge = feature.edges.find((item) => item.target === nodeId)
  const timestamp = networkEvent.endedAt || networkEvent.startedAt || Date.now()
  const isStart = networkEvent.type === 'request-start'
  const isFailure = !isStart && networkEvent.ok === false

  markPreviousStepsSuccess(feature, nodeIndex, timestamp)

  if (edge) {
    emitExecutionEvent(
      createExecutionEvent({
        eventId: `${networkEvent.id}-${edge.id}-${isStart ? 'start' : isFailure ? 'fail' : 'success'}`,
        targetType: 'EDGE',
        targetId: edge.id,
        status: isStart ? STATUS.IN_PROGRESS : isFailure ? STATUS.FAILED : STATUS.SUCCESS,
        eventType: isStart ? 'START' : isFailure ? 'FAIL' : 'SUCCESS',
        message: `${edge.label} ${isStart ? '시작' : isFailure ? '실패' : '성공'}`,
        featureId: feature.id,
        timestamp,
        errorCode: isFailure ? `HTTP_${networkEvent.statusCode || 0}` : '',
        errorMessage: isFailure ? networkEvent.errorText || '요청 실패' : '',
        label: edge.label,
      }),
    )
  }

  emitExecutionEvent(
    createExecutionEvent({
      eventId: `${networkEvent.id}-${nodeId}-${isStart ? 'start' : isFailure ? 'fail' : 'success'}`,
      targetType: 'NODE',
      targetId: nodeId,
      status: isStart ? STATUS.IN_PROGRESS : isFailure ? STATUS.FAILED : STATUS.SUCCESS,
      eventType: isStart ? 'START' : isFailure ? 'FAIL' : 'SUCCESS',
      message: `${nodeMap.get(nodeId)?.name || nodeId} ${isStart ? '처리 시작' : isFailure ? '처리 실패' : '처리 성공'}`,
      featureId: feature.id,
      timestamp,
      errorCode: isFailure ? `HTTP_${networkEvent.statusCode || 0}` : '',
      errorMessage: isFailure ? networkEvent.errorText || '요청 실패' : '',
      label: nodeMap.get(nodeId)?.name || nodeId,
    }),
  )

  emitExecutionEvent(
    createExecutionEvent({
      eventId: `${networkEvent.id}-${api.id}-${isStart ? 'start' : isFailure ? 'fail' : 'success'}`,
      targetType: 'API',
      targetId: api.id,
      status: isStart ? STATUS.IN_PROGRESS : isFailure ? STATUS.FAILED : STATUS.SUCCESS,
      eventType: isStart ? 'START' : isFailure ? 'FAIL' : 'SUCCESS',
      message: `${api.method} ${api.endpoint} ${isStart ? '호출 시작' : isFailure ? '호출 실패' : '호출 성공'}`,
      featureId: feature.id,
      timestamp,
      errorCode: isFailure ? `HTTP_${networkEvent.statusCode || 0}` : '',
      errorMessage: isFailure ? networkEvent.errorText || '요청 실패' : '',
      label: `${api.method} ${api.endpoint}`,
    }),
  )
}

function normalizeRequestPath(path = '') {
  return String(path).replace(/\?.*$/, '').replace(/\/+$/, '') || '/'
}

function matchesApi(networkEvent, api) {
  return api.matcher.method === networkEvent.method && api.matcher.regex.test(normalizeRequestPath(networkEvent.path))
}

function handleWorkflowChannelEvent(networkEvent) {
  if (!currentTraceId.value || !selectedFeature.value) return
  if (currentScenarioMode() !== 'LIVE' || !selectedFeature.value.supportsLive) return
  if ((networkEvent.startedAt || 0) < currentTraceStartedAt.value) return

  const matchedApis = selectedFeature.value.apis.filter((api) => matchesApi(networkEvent, api))
  if (!matchedApis.length) return

  lastLiveEventAt.value = Date.now()
  matchedApis.forEach((api) => applyApiNetworkEvent(api, networkEvent))
}

function openFeatureWindow() {
  if (!selectedFeature.value?.supportsLive) return
  try {
    openError.value = ''
    trackedWindow = window.open(selectedFeature.value.liveEntryPath, `workflow-${selectedFeature.value.id}`)
    trackedWindowClosed.value = !trackedWindow
    if (closePollTimer) window.clearInterval(closePollTimer)
    closePollTimer = window.setInterval(() => {
      trackedWindowClosed.value = !trackedWindow || trackedWindow.closed
    }, 1000)
  } catch (error) {
    trackedWindowClosed.value = true
    openError.value = error instanceof Error ? error.message : '연결 창을 열지 못했습니다.'
  }
}

function scheduleSampleEvent(delayMs, callback) {
  const timer = window.setTimeout(callback, delayMs)
  sampleTimers.push(timer)
}

function runSampleScenario(feature, mode) {
  sampleTimers.forEach((timer) => clearTimeout(timer))
  sampleTimers = []

  emitExecutionEvent(
    createExecutionEvent({
      eventId: `${currentTraceId.value}-feature-start`,
      targetType: 'FEATURE',
      targetId: feature.id,
      status: STATUS.IN_PROGRESS,
      eventType: 'START',
      message: `${feature.name} 실행 시작`,
      featureId: feature.id,
      label: feature.name,
    }),
  )

  const failingIndex = mode === 'SAMPLE_FAILURE' ? Math.max(0, feature.nodes.length - 2) : -1
  let delay = 350

  feature.nodes.forEach((node, index) => {
    const edge = feature.edges.find((item) => item.target === node.id)

    scheduleSampleEvent(delay, () => {
      if (edge) {
        emitExecutionEvent(
          createExecutionEvent({
            eventId: `${currentTraceId.value}-${edge.id}-start`,
            targetType: 'EDGE',
            targetId: edge.id,
            status: STATUS.IN_PROGRESS,
            eventType: 'START',
            message: `${edge.label} 시작`,
            featureId: feature.id,
            label: edge.label,
          }),
        )
      }
      emitExecutionEvent(
        createExecutionEvent({
          eventId: `${currentTraceId.value}-${node.id}-start`,
          targetType: 'NODE',
          targetId: node.id,
          status: STATUS.IN_PROGRESS,
          eventType: 'START',
          message: `${node.name} 처리 시작`,
          featureId: feature.id,
          label: node.name,
        }),
      )
      node.apiIds.forEach((apiId) => {
        const api = apiMap.get(apiId)
        if (!api) return
        emitExecutionEvent(
          createExecutionEvent({
            eventId: `${currentTraceId.value}-${api.id}-start`,
            targetType: 'API',
            targetId: api.id,
            status: STATUS.IN_PROGRESS,
            eventType: 'START',
            message: `${api.method} ${api.endpoint} 호출 시작`,
            featureId: feature.id,
            label: `${api.method} ${api.endpoint}`,
          }),
        )
      })
    })

    delay += 550

    scheduleSampleEvent(delay, () => {
      const failed = index === failingIndex
      const finalStatus = failed ? STATUS.FAILED : STATUS.SUCCESS
      const finalEventType = failed ? 'FAIL' : 'SUCCESS'
      const errorCode = failed ? 'SAMPLE_FAILURE' : ''
      const errorMessage = failed ? '샘플 실패 시나리오에서 의도적으로 중단했습니다.' : ''

      if (edge) {
        emitExecutionEvent(
          createExecutionEvent({
            eventId: `${currentTraceId.value}-${edge.id}-${failed ? 'fail' : 'success'}`,
            targetType: 'EDGE',
            targetId: edge.id,
            status: finalStatus,
            eventType: finalEventType,
            message: `${edge.label} ${failed ? '실패' : '성공'}`,
            featureId: feature.id,
            errorCode,
            errorMessage,
            label: edge.label,
          }),
        )
      }

      emitExecutionEvent(
        createExecutionEvent({
          eventId: `${currentTraceId.value}-${node.id}-${failed ? 'fail' : 'success'}`,
          targetType: 'NODE',
          targetId: node.id,
          status: finalStatus,
          eventType: finalEventType,
          message: `${node.name} ${failed ? '실패' : '성공'}`,
          featureId: feature.id,
          errorCode,
          errorMessage,
          label: node.name,
        }),
      )

      node.apiIds.forEach((apiId) => {
        const api = apiMap.get(apiId)
        if (!api) return
        emitExecutionEvent(
          createExecutionEvent({
            eventId: `${currentTraceId.value}-${api.id}-${failed ? 'fail' : 'success'}`,
            targetType: 'API',
            targetId: api.id,
            status: finalStatus,
            eventType: finalEventType,
            message: `${api.method} ${api.endpoint} ${failed ? '실패' : '성공'}`,
            featureId: feature.id,
            errorCode,
            errorMessage,
            label: `${api.method} ${api.endpoint}`,
          }),
        )
      })

      if (failed) {
        sampleTimers.forEach((timer) => clearTimeout(timer))
        sampleTimers = []
      }
    })

    delay += 450
  })
}

function runSelectedFeature() {
  if (!selectedFeature.value) return

  resetExecutionState()
  currentTraceId.value = generateTraceId()
  currentTraceStartedAt.value = Date.now()
  selectedTarget.value = { type: 'FEATURE', id: selectedFeature.value.id }
  viewMode.value = 'level2'

  const mode = currentScenarioMode()
  if (mode === 'LIVE' && selectedFeature.value.supportsLive) {
    emitExecutionEvent(
      createExecutionEvent({
        eventId: `${currentTraceId.value}-feature-start`,
        targetType: 'FEATURE',
        targetId: selectedFeature.value.id,
        status: STATUS.IN_PROGRESS,
        eventType: 'START',
        message: `${selectedFeature.value.name} 실시간 추적 시작`,
        featureId: selectedFeature.value.id,
        label: selectedFeature.value.name,
      }),
    )
    openFeatureWindow()
    return
  }

  runSampleScenario(selectedFeature.value, mode)
}

onMounted(() => {
  unsubscribe = subscribeWorkflowEvents(handleWorkflowChannelEvent)
})

onBeforeUnmount(() => {
  if (unsubscribe) unsubscribe()
  if (closePollTimer) window.clearInterval(closePollTimer)
  sampleTimers.forEach((timer) => clearTimeout(timer))
})
</script>

<style scoped>
.workflow-app {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 12px;
  height: 100vh;
  padding: 14px;
  background: radial-gradient(circle at top left, #dbeafe 0, transparent 28%), #f4f7fb;
  color: #0f172a;
  overflow: hidden;
}

.workflow-header,
.workflow-toolbar,
.sidebar,
.canvas-panel,
.detail-panel,
.logs-panel {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 18px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(16px);
}

.workflow-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  min-width: 0;
}

.eyebrow {
  margin: 0 0 6px;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.title-block {
  min-width: 0;
}

.title-block h1 {
  margin: 0;
  font-size: 22px;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.subtitle {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
  max-width: 68ch;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.legend-item,
.status-pill,
.mini-pill,
.toggle-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  padding: 5px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  background: #94a3b8;
}

.dot.NONE { background: #94a3b8; }
.dot.IN_PROGRESS { background: #2563eb; animation: dotPulse 1.1s ease-in-out infinite; }
.dot.SUCCESS { background: #16a34a; }
.dot.FAILED { background: #dc2626; }

@keyframes dotPulse {
  0%, 100% { transform: scale(0.86); opacity: 0.65; }
  50% { transform: scale(1.18); opacity: 1; }
}

.workflow-toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1.1fr) minmax(220px, 1fr) auto auto auto minmax(220px, 0.9fr);
  gap: 10px;
  align-items: end;
  padding: 12px;
  min-width: 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.field.compact label {
  margin-bottom: 1px;
}

.field label {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

select,
input {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 11px;
  background: white;
  color: #0f172a;
  outline: none;
}

select:focus,
input:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 4px rgba(147, 197, 253, 0.25);
}

button {
  border: 0;
  border-radius: 12px;
  padding: 10px 13px;
  background: #0f172a;
  color: white;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14);
  transition: transform 0.12s ease, opacity 0.12s ease, background 0.12s ease;
  white-space: nowrap;
}

button:hover {
  transform: translateY(-1px);
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  transform: none;
}

button.secondary,
button.ghost {
  background: #f1f5f9;
  color: #0f172a;
  box-shadow: none;
  border: 1px solid #e2e8f0;
}

button.ghost {
  background: transparent;
  border-color: transparent;
}

button.active {
  background: #2563eb;
  color: white;
  border-color: #2563eb;
}

.trace-box {
  min-width: 0;
  background: #0f172a;
  color: #dbeafe;
  border-radius: 14px;
  padding: 9px 11px;
  font-size: 12px;
  line-height: 1.35;
}

.trace-box strong {
  display: block;
  color: white;
  font-size: 11px;
  margin-bottom: 2px;
  opacity: 0.78;
}

.trace-box span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.workbench {
  display: grid;
  grid-template-columns: minmax(248px, 280px) minmax(0, 1fr) minmax(320px, 360px);
  gap: 14px;
  min-height: 0;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  overflow: hidden;
  min-width: 0;
}

.section-title,
.lane-group-header,
.logs-header,
.canvas-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.canvas-top,
.lane-group-header {
  align-items: flex-start;
}

.canvas-top {
  flex-wrap: wrap;
}

.section-title h2,
.logs-header h2 {
  margin: 0;
  font-size: 14px;
}

.sidebar-help {
  border: 1px solid #dbe4ef;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  padding: 10px 12px;
}

.sidebar-help strong {
  display: block;
  font-size: 12px;
  color: #0f172a;
  margin-bottom: 4px;
}

.sidebar-help p {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #64748b;
}

.search-input {
  margin-top: -2px;
}

.filter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.toggle-chip {
  cursor: pointer;
}

.toggle-chip input {
  width: auto;
  margin: 0;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
  padding-right: 6px;
}

.lane-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 4px;
}

.lane-group + .lane-group {
  border-top: 1px solid #eef2f7;
  padding-top: 12px;
}

.lane-header-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.lane-header-copy strong {
  font-size: 13px;
  color: #0f172a;
}

.lane-header-copy span {
  font-size: 11px;
  color: #64748b;
  line-height: 1.35;
}

.feature-card {
  width: 100%;
  text-align: left;
  background: white;
  border: 1px solid #e2e8f0;
  box-shadow: none;
  color: #0f172a;
  border-radius: 14px;
  padding: 10px;
}

.feature-card:hover {
  border-color: #bfdbfe;
  background: #f8fbff;
}

.feature-card.active {
  border-color: #60a5fa;
  background: #eff6ff;
}

.feature-card .topline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  font-weight: 800;
}

.feature-name {
  min-width: 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.feature-card p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.status-pill.compact,
.mini-pill {
  padding: 4px 8px;
  font-size: 11px;
  white-space: nowrap;
}

.status-pill.NONE { color: #475569; background: #f1f5f9; }
.status-pill.IN_PROGRESS { color: #1d4ed8; background: #dbeafe; border-color: #bfdbfe; }
.status-pill.SUCCESS { color: #15803d; background: #dcfce7; border-color: #bbf7d0; }
.status-pill.FAILED { color: #b91c1c; background: #fee2e2; border-color: #fecaca; }
.feature-card .status-pill.compact { flex: 0 0 auto; }

.mini-pill.type { background: #eef2ff; color: #3730a3; border-color: #c7d2fe; }
.mini-pill.warn { background: #fffbeb; color: #b45309; border-color: #fde68a; }

.canvas-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 10px;
  padding: 14px;
  min-height: 0;
  min-width: 0;
}

.breadcrumb {
  color: #475569;
  font-size: 13px;
  line-height: 1.4;
  flex: 1 1 auto;
  min-width: 0;
}

.view-tabs {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 2px;
  flex: 0 0 auto;
  scrollbar-width: thin;
}

.zoom-controls {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.zoom-readout {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 58px;
  height: 36px;
  padding: 0 10px;
  border-radius: 12px;
  border: 1px solid #dbe4ef;
  background: #f8fafc;
  color: #334155;
  font-size: 12px;
  font-weight: 800;
}

.summary-strip {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  align-items: center;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 2px;
  scrollbar-width: thin;
}

.summary-strip .mini-pill,
.view-tabs button {
  flex: 0 0 auto;
}

.svg-wrap {
  position: relative;
  min-height: 0;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  overflow: auto;
}

.canvas-hint {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.35;
}

.canvas-hint span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: #f8fafc;
}

svg {
  display: block;
  flex: 0 0 auto;
  background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
  background-size: 18px 18px;
}

.story-strip {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 2px;
  scrollbar-width: thin;
}

.story-card {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px;
  border-radius: 16px;
  border: 1px solid #dbe4ef;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  min-width: 240px;
  max-width: 280px;
  flex: 0 0 auto;
}

.story-order {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: #0f172a;
  color: white;
  font-size: 12px;
  font-weight: 900;
  flex: 0 0 auto;
}

.story-body {
  min-width: 0;
}

.story-title {
  margin: 0;
  font-size: 13px;
  font-weight: 900;
  color: #0f172a;
}

.story-text {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: #475569;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.stage-group {
  fill: rgba(248, 250, 252, 0.9);
  stroke: #dbe4ef;
  stroke-width: 1.6;
}

.stage-group.level1-group {
  fill: rgba(241, 245, 249, 0.88);
}

.group-title {
  font-size: 13px;
  font-weight: 900;
  fill: #0f172a;
}

.group-note {
  font-size: 10px;
  fill: #64748b;
}

.step-order {
  font-size: 10px;
  font-weight: 900;
  fill: #94a3b8;
  letter-spacing: 0.08em;
}

.group-subtitle {
  font-size: 10px;
  font-weight: 800;
  fill: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.node-group {
  cursor: pointer;
}

.node-card {
  fill: rgba(255,255,255,0.96);
  stroke-width: 2.4;
  filter: drop-shadow(0 10px 14px rgba(15, 23, 42, 0.08));
}

.node-card.NONE { stroke: #94a3b8; }
.node-card.IN_PROGRESS { stroke: #2563eb; }
.node-card.SUCCESS { stroke: #16a34a; }
.node-card.FAILED { stroke: #dc2626; }

.node-group.selected .node-card {
  stroke-width: 4;
  filter: drop-shadow(0 14px 18px rgba(37, 99, 235, 0.18));
}

.node-group.search-hit .node-card,
.edge-group.search-hit .edge-path {
  stroke: #f59e0b !important;
  stroke-width: 4.2;
}

.node-title {
  font-size: 14px;
  font-weight: 900;
  fill: #0f172a;
}

.node-subtitle {
  font-size: 10px;
  font-weight: 800;
  fill: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.node-description {
  font-size: 10px;
  fill: #64748b;
}

.badge-text {
  font-size: 10px;
  font-weight: 900;
  fill: white;
}

.badge-bg.NONE { fill: #94a3b8; }
.badge-bg.IN_PROGRESS { fill: #2563eb; }
.badge-bg.SUCCESS { fill: #16a34a; }
.badge-bg.FAILED { fill: #dc2626; }

.edge-path {
  fill: none;
  stroke-width: 3.4;
  stroke-linecap: round;
}

.edge-path.NONE { stroke: #94a3b8; opacity: 0.56; }
.edge-path.IN_PROGRESS { stroke: #2563eb; opacity: 0.96; }
.edge-path.SUCCESS { stroke: #16a34a; opacity: 0.92; }
.edge-path.FAILED { stroke: #dc2626; opacity: 0.95; }

.edge-click-area {
  fill: none;
  stroke: transparent;
  stroke-width: 20;
  cursor: pointer;
}

.edge-group.selected .edge-path {
  stroke-width: 6;
  filter: drop-shadow(0 4px 8px rgba(15, 23, 42, 0.24));
}

.edge-flow {
  stroke-dasharray: 9 9;
  animation: flowDash 0.75s linear infinite;
}

.node-pulse .node-card {
  animation: nodePulse 1s ease-in-out infinite;
}

@keyframes flowDash {
  from { stroke-dashoffset: 24; }
  to { stroke-dashoffset: 0; }
}

@keyframes nodePulse {
  0%, 100% { filter: drop-shadow(0 0 0 rgba(37,99,235,0.0)); }
  50% { filter: drop-shadow(0 0 16px rgba(37,99,235,0.35)); }
}

.edge-label-bg {
  fill: rgba(255, 255, 255, 0.92);
  stroke: #e2e8f0;
  stroke-width: 1;
}

.edge-label {
  font-size: 10px;
  fill: #475569;
  font-weight: 800;
}

.opacity-dim {
  opacity: 0.18;
}

.detail-panel {
  padding: 14px;
  overflow: auto;
  min-width: 0;
}

.detail-card {
  min-width: 0;
}

.detail-card h2 {
  margin: 0 0 6px;
  font-size: 20px;
  letter-spacing: -0.025em;
  line-height: 1.25;
}

.muted {
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
  margin: 0 0 12px;
}

.detail-section {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e2e8f0;
}

.detail-section h3 {
  margin: 0 0 9px;
  font-size: 13px;
  color: #0f172a;
}

.kv {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 8px 10px;
  font-size: 12px;
  line-height: 1.45;
}

.k {
  color: #64748b;
  font-weight: 800;
}

.v {
  color: #0f172a;
  overflow-wrap: anywhere;
}

.chip-list,
.api-list {
  min-width: 0;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip-list .mini-pill {
  max-width: 100%;
  white-space: normal;
  align-items: flex-start;
  line-height: 1.4;
}

.api-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.api-card-mini {
  width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: start;
  gap: 8px;
  text-align: left;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #0f172a;
  box-shadow: none;
  border-radius: 14px;
  padding: 10px;
}

.api-card-mini:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.api-method {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 46px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 950;
  margin-right: 0;
}

.endpoint {
  display: block;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  color: #334155;
  overflow-wrap: anywhere;
  line-height: 1.45;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.logs-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
  max-height: 240px;
}

.logs-header {
  padding: 12px 14px;
  border-bottom: 1px solid #e2e8f0;
  flex-wrap: wrap;
}

.logs-header > div {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.log-table {
  overflow: auto;
  font-size: 12px;
  scrollbar-width: thin;
}

.log-row {
  display: grid;
  grid-template-columns: 88px 170px 160px 88px 98px minmax(260px, 1fr) 180px;
  gap: 10px;
  align-items: center;
  min-width: 1040px;
  width: 100%;
  padding: 9px 14px;
  border-bottom: 1px solid #eef2f7;
  background: transparent;
  box-shadow: none;
  border-radius: 0;
  color: #0f172a;
  text-align: left;
}

.log-row.header-row {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f8fafc;
  font-weight: 900;
  color: #475569;
  cursor: default;
}

.log-row:not(.header-row):hover {
  background: #f8fbff;
  transform: none;
}

.log-cell {
  min-width: 0;
  overflow-wrap: anywhere;
  line-height: 1.45;
}

.log-cell.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty-log {
  padding: 22px 14px;
  color: #64748b;
}

@media (max-width: 1400px) {
  .workflow-toolbar {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .trace-box {
    grid-column: span 3;
  }

  .workbench {
    grid-template-columns: minmax(220px, 248px) minmax(0, 1fr);
  }

  .detail-panel {
    grid-column: 1 / -1;
    max-height: 360px;
  }
}

@media (max-width: 960px) {
  .workflow-app {
    padding: 10px;
    grid-template-rows: auto auto auto auto;
  }

  .workflow-header,
  .workflow-toolbar {
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }

  .legend {
    justify-content: flex-start;
  }

  .workbench {
    display: flex;
    flex-direction: column;
  }

  .sidebar {
    max-height: 360px;
  }

  .view-tabs,
  .summary-strip {
    width: 100%;
  }

  .canvas-hint {
    flex-direction: row;
  }

  svg {
    min-width: 820px;
  }
}
</style>


