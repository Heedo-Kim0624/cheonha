<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Filter Card -->
      <div class="bg-white rounded-xl p-5 border border-gray-200 space-y-4">
        <div class="flex items-center gap-3 flex-wrap">
          <span class="text-sm font-semibold text-gray-600">조</span>
          <button
            @click="onTeamChange('')"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-all"
            :class="teamId === '' ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
          >전체</button>
          <button
            v-for="t in teams" :key="t.id"
            @click="onTeamChange(t.id)"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-all"
            :class="Number(teamId) === t.id ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
          >{{ t.name }}</button>
        </div>

        <div class="flex items-center gap-3 flex-wrap">
          <button
            @click="toggleDraw"
            :class="drawing ? 'bg-danger text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
            class="px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5"
          >
            <span>{{ drawing ? '✕' : '✎' }}</span>
            {{ drawing ? '그리기 중단' : '새 권역 그리기' }}
          </button>
        </div>
      </div>

      <!-- Map + Info Row -->
      <div class="flex gap-5" style="height: 680px">
        <!-- Map Card -->
        <div class="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col">
          <div class="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h3 class="text-sm font-bold text-text">권역 지도</h3>
              <p class="text-xs text-gray-500">
                <template v-if="selectedHistory">
                  {{ selectedHistory.crew_name }} · {{ selectedHistory.date }} 권역 내부 경로
                </template>
                <template v-else-if="selectedTerritory">{{ selectedTerritory.code }} 권역 선택됨</template>
                <template v-else>조를 선택하고 권역을 클릭하세요</template>
              </p>
            </div>
            <div class="flex items-center gap-2">
              <button @click="fitToAll" class="px-3 py-1.5 text-xs rounded-md border border-gray-200 hover:bg-gray-50">전체 맞춤</button>
              <button v-if="selectedHistory" @click="fitToSelected" class="px-3 py-1.5 text-xs rounded-md bg-primary-light border border-primary text-primary-dark font-semibold">선택 경로 확대</button>
            </div>
          </div>

          <div class="relative flex-1" :class="{ 'opacity-60': !loading && !visibleTerritories.length }">
            <div id="vw-tracking-map" ref="mapEl" class="absolute inset-0" style="width:100%;height:100%"></div>

            <!-- 맵 위에 올라가는 사이클 팝업 (ol.Overlay 가 위치 조정) -->
            <div ref="popupEl" class="pointer-events-auto">
              <div v-if="popupCycle" class="w-52 bg-white rounded-lg border border-gray-200 shadow-xl overflow-hidden">
                <div class="flex items-center justify-between px-3 py-2 bg-primary-light">
                  <div class="flex items-center gap-2">
                    <span class="w-5 h-5 rounded-full bg-primary text-white text-[10px] font-bold flex items-center justify-center">
                      {{ popupCycle.cycle_no }}
                    </span>
                    <span class="text-sm font-bold text-text">Cycle {{ popupCycle.cycle_no }}</span>
                  </div>
                  <button @click="closePopup" class="text-gray-400 hover:text-gray-700 text-sm leading-none">✕</button>
                </div>
                <div class="px-3 py-2.5 grid grid-cols-2 gap-2">
                  <div>
                    <div class="flex items-center gap-1 mb-0.5">
                      <span class="w-2 h-2 rounded-full" style="background:#FACC15"></span>
                      <span class="text-[10px] font-semibold text-gray-500">Searching</span>
                    </div>
                    <div class="text-sm font-bold text-text">{{ fmtSeconds(popupCycle.sr_seconds) }}</div>
                  </div>
                  <div>
                    <div class="flex items-center gap-1 mb-0.5">
                      <span class="w-2 h-2 rounded-full" style="background:#22C55E"></span>
                      <span class="text-[10px] font-semibold text-gray-500">Delivering</span>
                    </div>
                    <div class="text-sm font-bold text-text">{{ fmtSeconds(popupCycle.dl_seconds) }}</div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="mapError" class="absolute inset-0 flex items-center justify-center bg-white/90 z-20">
              <div class="max-w-sm text-center px-6">
                <div class="w-12 h-12 mx-auto rounded-full bg-red-50 border-2 border-danger flex items-center justify-center text-xl mb-2">⚠️</div>
                <h4 class="text-sm font-bold text-danger mb-1">지도 스크립트 로드 실패</h4>
                <p class="text-xs text-gray-500 leading-relaxed">{{ mapError }}</p>
              </div>
            </div>

            <div v-if="selectedHistory" class="absolute left-4 bottom-4 bg-white/95 backdrop-blur rounded-lg border border-gray-200 px-3 py-2 shadow-sm z-10">
              <p class="text-[10px] font-bold text-gray-500 mb-1">
                권역 내부 경로
              </p>
              <div class="flex items-center gap-3 text-xs">
                <span class="flex items-center gap-1"><span class="inline-block w-4 h-1 rounded" style="background:#2563EB"></span>In Vehicle</span>
                <span class="flex items-center gap-1"><span class="inline-block w-4 h-1 rounded" style="background:#FACC15"></span>Searching</span>
                <span class="flex items-center gap-1"><span class="inline-block w-4 h-1 rounded" style="background:#22C55E"></span>Delivering</span>
              </div>
            </div>

            <!-- 상단 힌트: 단계 안내 (권역은 항상 보이므로 비파괴적으로) -->
            <div v-if="!selectedHistory && !loading && visibleTerritories.length" class="absolute top-3 left-1/2 -translate-x-1/2 z-10">
              <div class="bg-white/95 backdrop-blur rounded-full border border-gray-200 shadow-sm px-3 py-1 text-[11px] text-gray-600">
                <template v-if="!teamId">전체 권역 · 조를 선택하면 해당 조 권역으로 좁혀집니다</template>
                <template v-else>{{ teamName }} 권역 · 폴리곤을 클릭하면 난이도, 추천 배송원, 배송 이력을 봅니다</template>
              </div>
            </div>

            <!-- 정말 아무것도 없을 때 (권역도 없음) -->
            <div v-if="!loading && !teamId" class="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
              <div class="bg-white rounded-2xl border border-gray-200 shadow-lg px-8 py-6 max-w-sm text-center pointer-events-auto">
                <div class="w-14 h-14 mx-auto rounded-full bg-primary-light border-2 border-primary flex items-center justify-center mb-3 text-2xl">🗺️</div>
                <h4 class="text-base font-bold text-text mb-1">조를 선택하세요</h4>
                <p class="text-xs text-gray-500 leading-relaxed">조를 선택하면 해당 조의 권역 폴리곤과 목록이 표시됩니다.</p>
              </div>
            </div>

            <div v-else-if="!loading && !visibleTerritories.length" class="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
              <div class="bg-white rounded-2xl border border-gray-200 shadow-lg px-8 py-6 max-w-sm text-center pointer-events-auto">
                <div class="w-14 h-14 mx-auto rounded-full bg-primary-light border-2 border-primary flex items-center justify-center mb-3 text-2xl">🗺️</div>
                <h4 class="text-base font-bold text-text mb-1">등록된 권역이 없습니다</h4>
                <p class="text-xs text-gray-500 leading-relaxed">"새 권역 그리기" 로 권역을 추가하세요.</p>
              </div>
            </div>

            <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/50 pointer-events-none z-10">
              <div class="px-4 py-2 rounded-lg bg-gray-800 text-white text-sm">불러오는 중…</div>
            </div>
          </div>
        </div>

        <!-- Info Panel -->
        <div v-if="teamId || selectedTerritory" class="w-[380px] bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden">
          <!-- 권역이 선택되어 있으면 권역 상세를 우선 표시 -->
          <template v-if="selectedTerritory">
            <div class="p-4 border-b border-gray-200 flex items-start justify-between">
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <span class="w-3 h-3 rounded-sm" :style="{ background: selectedTerritory.color || '#2563EB' }"></span>
                  <h3 class="text-base font-bold text-text">{{ selectedTerritory.code }}</h3>
                  <span v-if="selectedTerritory.group_letter" class="px-2 py-0.5 rounded bg-primary-light text-primary-dark text-[10px] font-bold">
                    조 {{ selectedTerritory.group_letter }}
                  </span>
                </div>
                <div class="text-[11px] text-gray-500">
                  권역 폴리곤 · 클릭한 권역의 상세 정보
                </div>
              </div>
              <div class="flex items-center gap-1">
                <input type="color" :value="selectedTerritory.color || '#2563EB'" @change="changeTerritoryColor"
                  class="w-7 h-7 rounded cursor-pointer" title="색상" />
                <button @click="removeTerritory" class="px-2 py-1 rounded text-[10px] bg-danger text-white">삭제</button>
                <button @click="clearTerritory" class="px-2 py-1 rounded text-[10px] bg-gray-100 text-gray-600 hover:bg-gray-200">닫기</button>
              </div>
            </div>

            <div class="p-4 space-y-3 overflow-y-auto">
              <template v-if="territoryPanelMode === 'cycles' && selectedHistory">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-xs font-semibold text-gray-600">선택 이력 사이클</div>
                    <div class="text-[10px] text-gray-400">{{ selectedHistory.date }} · {{ selectedHistory.crew_name }}</div>
                  </div>
                  <button @click="showOverviewPanel" class="px-2 py-1 rounded text-[10px] bg-gray-100 text-gray-600 hover:bg-gray-200">
                    배송이력 목록
                  </button>
                </div>
                <div class="space-y-1">
                  <button
                    v-for="c in selectedHistoryCycles"
                    :key="c.cycle_id"
                    @click="onCycleCardClick(c)"
                    :data-cycle="c.cycle_no"
                    class="w-full rounded border border-gray-100 bg-gray-50 hover:border-primary px-2 py-2 text-left text-xs transition"
                  >
                    <div class="flex items-center justify-between">
                      <span class="font-bold">Cycle {{ c.cycle_no }}</span>
                      <span class="text-[10px] text-gray-400">camera end {{ c.capture_count || 0 }}</span>
                    </div>
                    <div class="text-[10px] text-gray-500 mt-0.5">
                      IV {{ c.iv_seconds == null ? '—' : fmtSeconds(c.iv_seconds) }} · SR {{ fmtSeconds(c.sr_seconds) }} · DL {{ fmtSeconds(c.dl_seconds) }}
                    </div>
                  </button>
                </div>
              </template>

              <template v-else-if="territoryPanelMode === 'manpower'">
                <div class="flex items-center justify-between">
                  <span class="text-xs font-semibold text-gray-600">추천 배송원</span>
                  <button @click="showOverviewPanel" class="px-2 py-1 rounded text-[10px] bg-gray-100 text-gray-600 hover:bg-gray-200">
                    배송이력 보기
                  </button>
                </div>
                <div class="flex rounded-lg bg-gray-100 p-0.5">
                  <button @click="manpowerSort = 'distance'"
                    class="flex-1 px-2 py-1 rounded-md text-[10px] font-semibold"
                    :class="manpowerSort === 'distance' ? 'bg-white text-text shadow-sm' : 'text-gray-500'">
                    거리순
                  </button>
                  <button @click="manpowerSort = 'recommend'"
                    class="flex-1 px-2 py-1 rounded-md text-[10px] font-semibold"
                    :class="manpowerSort === 'recommend' ? 'bg-white text-text shadow-sm' : 'text-gray-500'">
                    추천순
                  </button>
                </div>
                <button @click="loadNearbyManpower" class="w-full px-3 py-2 rounded-lg bg-info text-white text-sm font-semibold hover:opacity-90">
                  👥 추천 배송원 새로고침
                </button>
                <div v-if="recommendedManpower.length" class="space-y-1">
                  <div v-for="m in recommendedManpower" :key="m.name + m.phone" class="bg-gray-50 rounded p-2 text-xs">
                    <div class="flex items-center gap-2">
                      <span class="font-bold">{{ m.name }}</span>
                      <span v-if="m.has_vehicle" class="px-1.5 py-0.5 rounded bg-primary-light text-primary-dark text-[9px]">차량</span>
                      <span class="text-gray-400">{{ m.age }}세</span>
                      <span class="text-gray-400">경력 {{ m.experience_years }}년</span>
                      <span class="ml-auto text-gray-500">{{ m.distance_m >= 1000 ? (m.distance_m / 1000).toFixed(1) + 'km' : Math.round(m.distance_m) + 'm' }}</span>
                    </div>
                    <div class="mt-1 text-[10px] text-gray-400">
                      추천점수 {{ m.recommend_score.toFixed(1) }} · 신체 {{ selectedDifficulty.physical }}/5 · 주행 {{ selectedDifficulty.driving }}/5
                    </div>
                  </div>
                </div>
                <div v-else class="text-[11px] text-gray-400 py-3 text-center border border-dashed border-gray-200 rounded">
                  표시할 추천 배송원이 없습니다
                </div>
              </template>

              <template v-else>
              <!-- 더미 난이도 -->
              <div>
                <div class="text-xs font-semibold text-gray-600 mb-1">배송지 난이도</div>
                <div class="grid grid-cols-2 gap-2">
                  <div class="bg-gray-50 rounded p-2">
                    <div class="flex items-center justify-between mb-1">
                      <span class="text-[10px] text-gray-400">신체적 난이도</span>
                      <span class="text-sm font-bold">{{ selectedDifficulty.physical }}/5</span>
                    </div>
                    <div class="h-1.5 rounded-full bg-gray-200 overflow-hidden">
                      <div class="h-full bg-danger" :style="{ width: selectedDifficulty.physical * 20 + '%' }"></div>
                    </div>
                  </div>
                  <div class="bg-gray-50 rounded p-2">
                    <div class="flex items-center justify-between mb-1">
                      <span class="text-[10px] text-gray-400">주행 난이도</span>
                      <span class="text-sm font-bold">{{ selectedDifficulty.driving }}/5</span>
                    </div>
                    <div class="h-1.5 rounded-full bg-gray-200 overflow-hidden">
                      <div class="h-full bg-warning" :style="{ width: selectedDifficulty.driving * 20 + '%' }"></div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 일별 박스수 -->
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold text-gray-600">
                    일별 박스수
                    <span v-if="territoryBoxes.length" class="ml-2 text-[10px] text-gray-400 font-normal">
                      합계 {{ boxTotal }} · 평균 {{ boxAvg }}
                    </span>
                  </span>
                  <button @click="openBoxEditor" class="text-[10px] text-primary-dark hover:underline">+ 추가</button>
                </div>
                <div v-if="!territoryBoxes.length" class="text-[11px] text-gray-400 py-3 text-center border border-dashed border-gray-200 rounded">
                  데이터 없음 · 배차표 업로드 또는 직접 추가
                </div>
                <div v-else class="space-y-1">
                  <!-- 막대그래프 (값 라벨 포함) -->
                  <div class="relative h-28 flex items-end gap-1 border-b border-l border-gray-200 px-1 pt-5">
                    <div v-for="b in territoryBoxes" :key="boxRowKey(b)"
                      class="flex-1 min-w-[10px] h-full flex items-end justify-center group cursor-help relative"
                      :title="`${b.date} · ${Math.round(b.box_count)} 박스${b.is_split ? ' (분배)' : ''}`">
                      <span class="absolute -top-4 text-[9px] text-gray-500 opacity-0 group-hover:opacity-100 transition whitespace-nowrap">
                        {{ Math.round(b.box_count) }}
                      </span>
                      <div class="w-full max-w-7 bg-primary rounded-t hover:bg-primary-dark transition min-h-[4px]"
                        :style="{ height: boxBarHeight(b) + '%' }"></div>
                    </div>
                    <!-- 최대값 보조선 -->
                    <div class="absolute right-0 top-0 text-[9px] text-gray-400 px-1">max {{ Math.round(maxBox) }}</div>
                  </div>
                  <!-- 날짜 라벨 (7개 이하면 전부, 많으면 양끝 + 중간) -->
                  <div class="flex text-[9px] text-gray-500 pl-1">
                    <div v-for="(b, i) in territoryBoxes" :key="i" class="flex-1 text-center truncate">
                      {{ territoryBoxes.length <= 10 ? b.date.slice(5) : (i === 0 || i === territoryBoxes.length - 1 || i === Math.floor(territoryBoxes.length / 2) ? b.date.slice(5) : '') }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- 사이클 통계 -->
              <div>
                <div class="text-xs font-semibold text-gray-600 mb-1">권역 배송 이력 요약</div>
                <div class="grid grid-cols-3 gap-2">
                  <div class="bg-gray-50 rounded p-2 text-center">
                    <div class="text-[10px] text-gray-400">평균 IV</div>
                    <div class="text-sm font-bold">{{ fmtSeconds(territoryCycles.summary?.avg_iv_sec) }}</div>
                  </div>
                  <div class="bg-gray-50 rounded p-2 text-center">
                    <div class="text-[10px] text-gray-400">평균 SR</div>
                    <div class="text-sm font-bold" style="color:#CA8A04">{{ fmtSeconds(territoryCycles.summary?.avg_sr_sec) }}</div>
                  </div>
                  <div class="bg-gray-50 rounded p-2 text-center">
                    <div class="text-[10px] text-gray-400">평균 DL</div>
                    <div class="text-sm font-bold" style="color:#15803D">{{ fmtSeconds(territoryCycles.summary?.avg_dl_sec) }}</div>
                  </div>
                </div>
                <div class="mt-1 text-[10px] text-gray-500">
                  camera end {{ territoryCycles.summary?.capture_count || 0 }} / cycles {{ territoryCycles.summary?.cycle_count || 0 }} / IV {{ territoryCycles.summary?.iv_cycle_count || 0 }}
                </div>
              </div>

              <button @click="showManpowerPanel" class="w-full px-3 py-2 rounded-lg bg-gray-900 text-white text-sm font-semibold hover:bg-gray-800">
                인력풀 보기
              </button>

              <!-- 배송 이력 -->
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold text-gray-600">배송 이력</span>
                  <span class="text-[10px] text-gray-400">클릭 시 권역 내부 경로 표시</span>
                </div>
                <div v-if="!territoryHistories.length" class="text-[11px] text-gray-400 py-3 text-center border border-dashed border-gray-200 rounded">
                  No camera end history in this territory
                </div>
                <div v-else class="space-y-1 max-h-44 overflow-y-auto">
                  <button
                    v-for="h in territoryHistories"
                    :key="h.session_id"
                    @click="onTerritoryHistoryClick(h)"
                    class="w-full rounded border px-2 py-2 text-left text-xs transition"
                    :class="selectedHistory && selectedHistory.session_id === h.session_id ? 'bg-primary-light border-primary' : 'bg-white border-gray-100 hover:border-primary'"
                  >
                    <div class="flex items-center justify-between">
                      <span class="font-bold">{{ h.date }} · {{ h.crew_name }}</span>
                      <span class="flex items-center gap-1">
                        <span
                          role="button"
                          tabindex="0"
                          @click.stop="downloadHistoryCsv(h)"
                          @keydown.enter.stop.prevent="downloadHistoryCsv(h)"
                          class="px-1.5 py-0.5 rounded bg-gray-900 text-white text-[10px] font-semibold hover:bg-gray-700"
                        >CSV</span>
                        <span class="text-[10px] text-gray-400">camera end {{ h.capture_count }}</span>
                      </span>
                    </div>
                    <div class="text-[10px] text-gray-500 mt-0.5">
                      사이클 {{ h.cycle_count }}개 · IV {{ h.iv_cycle_count ? fmtSeconds(h.avg_iv_seconds) : '—' }} · SR {{ fmtSeconds(h.avg_sr_seconds) }} · DL {{ fmtSeconds(h.avg_dl_seconds) }}
                    </div>
                  </button>
                </div>
              </div>
              </template>
            </div>
          </template>

          <template v-else>
            <div class="p-5 border-b border-gray-200">
              <h3 class="text-base font-bold text-text mb-1">{{ teamName || '조 미선택' }}</h3>
            </div>
            <div class="flex-1 overflow-y-auto p-4 space-y-2">
              <div v-if="!visibleTerritories.length" class="text-center text-sm text-gray-400 py-8">
                표시할 권역이 없습니다
              </div>
              <button
                v-for="t in visibleTerritories" :key="t.id"
                @click="selectTerritory(t)"
                class="w-full px-3 py-2.5 rounded-lg flex items-center gap-3 hover:bg-gray-50 transition text-left"
              >
                <span class="w-3 h-3 rounded-sm flex-shrink-0" :style="{ background: t.color || '#2563EB' }"></span>
                <div class="flex-1 text-left">
                  <div class="text-sm font-semibold text-text">{{ t.code }}</div>
                  <div class="text-[11px] text-gray-500">조 {{ t.group_letter || '-' }} · 클릭해서 상세 보기</div>
                </div>
                <span class="text-gray-300">›</span>
              </button>
            </div>
          </template>
        </div>
      </div>

      <!-- 권역 그리기 안내 배지 -->
      <div v-if="drawing" class="fixed left-1/2 -translate-x-1/2 bottom-8 bg-gray-800 text-white text-xs px-4 py-2 rounded-full shadow-lg z-30">
        지도를 클릭해 폴리곤을 그리세요 · 마지막 점을 더블클릭하면 마무리
      </div>

      <!-- 권역 저장 모달 (그리기 완료 시) -->
      <div v-if="pendingPolygon" class="fixed inset-0 bg-black/40 z-40 flex items-center justify-center" @click.self="cancelPendingPolygon">
        <div class="w-[360px] bg-white rounded-xl p-5 border border-gray-200 space-y-3">
          <h3 class="font-bold text-text">권역 이름 입력</h3>
          <input v-model="pendingCode" placeholder="예: 30X4" type="text"
            class="w-full px-2 py-1.5 border border-gray-200 rounded" />
          <div class="text-[10px] text-gray-500">
            '30X4' 처럼 알파벳을 포함하면 자동으로 조(X)가 추출됩니다.
          </div>
          <div class="flex justify-end gap-2">
            <button @click="cancelPendingPolygon" class="px-3 py-1.5 rounded bg-gray-100 text-sm">취소</button>
            <button @click="savePendingPolygon" class="px-3 py-1.5 rounded bg-primary text-white text-sm font-semibold">저장</button>
          </div>
        </div>
      </div>

      <!-- 박스수 수동 입력 모달 -->
      <div v-if="boxEdit" class="fixed inset-0 bg-black/40 z-40 flex items-center justify-center" @click.self="boxEdit = null">
        <div class="w-[360px] bg-white rounded-xl p-5 border border-gray-200 space-y-3">
          <h3 class="font-bold text-text">{{ selectedTerritory?.code }} · 박스수 입력</h3>
          <label class="block text-sm">날짜<input v-model="boxEdit.date" type="date" class="mt-1 w-full px-2 py-1.5 border border-gray-200 rounded" /></label>
          <label class="block text-sm">박스 수<input v-model.number="boxEdit.box_count" type="number" min="0" class="mt-1 w-full px-2 py-1.5 border border-gray-200 rounded" /></label>
          <div class="flex justify-end gap-2">
            <button @click="boxEdit = null" class="px-3 py-1.5 rounded bg-gray-100 text-sm">취소</button>
            <button @click="saveBoxEditor" class="px-3 py-1.5 rounded bg-primary text-white text-sm font-semibold">저장</button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import client from '@/api/client'
import { fetchTrackingSession, fetchSessionCaptures, fetchSessionPoints, downloadTrackingCsv } from '@/api/tracking'
import {
  listTerritories, createTerritory, updateTerritory, deleteTerritory,
  territoryBoxSeries, setTerritoryBoxes,
  territoryCyclesInside, territoryNearbyManpower,
} from '@/api/territory'
import { loadVWorld } from '@/utils/vworld'

const teams = ref([])
const teamId = ref('')
const selectedDate = ref(todayStr())
const searchQuery = ref('')
const toneOthers = ref(true)
const loading = ref(false)
const sessions = ref([])
const selectedSession = ref(null)
const selectedHistory = ref(null)
const detail = reactive({ cycles: [], points: [], captures: [] })
const hoveredCycle = ref(null)
const mapError = ref('')

const mapEl = ref(null)
const popupEl = ref(null)
const popupCycle = ref(null)
let vmap = null
let olLib = null
let routeLayer = null
let markerLayer = null
let highlightLayer = null
let territoryLayer = null
let manpowerLayer = null
let drawInteraction = null

/* ---------- 권역(territory) 관련 상태 ---------- */
const territories = ref([])
const selectedTerritory = ref(null)
const territoryBoxes = ref([])
const territoryCycles = ref({ cycles: [], summary: null })
const nearbyManpower = ref([])
const manpowerSort = ref('recommend')
const territoryPanelMode = ref('overview')
const drawing = ref(false)
const pendingPolygon = ref(null)
const pendingCode = ref('')
const boxEdit = ref(null)

const teamName = computed(() => {
  const t = teams.value.find(x => x.id === Number(teamId.value))
  return t ? t.name : ''
})

function hashText(text) {
  return String(text || '').split('').reduce((sum, ch) => sum + ch.charCodeAt(0), 0)
}

function difficultyFor(t) {
  const seed = hashText(t?.code || '')
  return {
    physical: (seed % 5) + 1,
    driving: (Math.floor(seed / 5) % 5) + 1,
  }
}

const selectedDifficulty = computed(() => difficultyFor(selectedTerritory.value))

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function manpowerScore(m) {
  const age = Number(m.age || 45)
  const exp = Number(m.experience_years || 0)
  const distanceM = Number(m.distance_m || 0)
  const physical = Number(selectedDifficulty.value.physical || 1)
  const driving = Number(selectedDifficulty.value.driving || 1)

  const ageFit = 100 - clamp((age - 25) / 35, 0, 1) * 100
  const requiredExp = driving * 4
  const drivingFit = clamp(exp / requiredExp, 0, 1) * 100
  const distanceFit = 100 - clamp(distanceM / 10000, 0, 1) * 100

  const physicalWeight = 1 + physical * 0.45
  const drivingWeight = 1 + driving * 0.45
  const distanceWeight = 0.9
  const vehicleBonus = m.has_vehicle ? 3 : 0

  return clamp(
    (
      ageFit * physicalWeight +
      drivingFit * drivingWeight +
      distanceFit * distanceWeight
    ) / (physicalWeight + drivingWeight + distanceWeight) + vehicleBonus,
    0,
    100,
  )
}

function manpowerDisplayKey(m) {
  return String(m.name || m.phone || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '')
}

const recommendedManpower = computed(() => {
  const rows = nearbyManpower.value.map(m => ({
    ...m,
    recommend_score: manpowerScore(m),
  }))
  const sortedRows = manpowerSort.value === 'distance'
    ? rows.sort((a, b) => (a.distance_m || 0) - (b.distance_m || 0))
    : rows.sort((a, b) => b.recommend_score - a.recommend_score)

  const seen = new Set()
  const deduped = []
  for (const row of sortedRows) {
    const key = manpowerDisplayKey(row)
    if (key && seen.has(key)) continue
    if (key) seen.add(key)
    deduped.push(row)
  }

  if (manpowerSort.value === 'distance') {
    return deduped
  }
  return deduped
})

const territoryHistories = computed(() => {
  const rows = territoryCycles.value?.cycles || []
  const grouped = new Map()

  for (const c of rows) {
    const key = c.session_id
    let h = grouped.get(key)
    if (!h) {
      h = {
        session_id: c.session_id,
        crew_name: c.crew_name || '',
        date: c.date || '',
        cycles: [],
        cycle_count: 0,
        capture_count: 0,
        iv_cycle_count: 0,
        iv_seconds_sum: 0,
        sr_seconds_sum: 0,
        dl_seconds_sum: 0,
        started_at: c.route_started_at || c.started_at,
        ended_at: c.route_ended_at || c.ended_at,
        avg_iv_seconds: null,
        avg_sr_seconds: 0,
        avg_dl_seconds: 0,
      }
      grouped.set(key, h)
    }

    h.cycles.push(c)
    h.cycle_count += 1
    h.capture_count += Number(c.capture_count || 0)
    h.sr_seconds_sum += Number(c.sr_seconds || 0)
    h.dl_seconds_sum += Number(c.dl_seconds || 0)

    if (c.iv_seconds != null) {
      h.iv_seconds_sum += Number(c.iv_seconds || 0)
      h.iv_cycle_count += 1
    }

    const startedAt = c.route_started_at || c.started_at
    const endedAt = c.route_ended_at || c.ended_at
    if (startedAt && (!h.started_at || new Date(startedAt) < new Date(h.started_at))) h.started_at = startedAt
    if (endedAt && (!h.ended_at || new Date(endedAt) > new Date(h.ended_at))) h.ended_at = endedAt
  }

  const histories = Array.from(grouped.values())
  for (const h of histories) {
    h.cycles.sort((a, b) => Number(a.cycle_no || 0) - Number(b.cycle_no || 0))
    h.avg_iv_seconds = h.iv_cycle_count ? Math.round(h.iv_seconds_sum / h.iv_cycle_count) : null
    h.avg_sr_seconds = h.cycle_count ? Math.round(h.sr_seconds_sum / h.cycle_count) : 0
    h.avg_dl_seconds = h.cycle_count ? Math.round(h.dl_seconds_sum / h.cycle_count) : 0
  }

  return histories.sort((a, b) => {
    const at = new Date(a.started_at || a.date).getTime() || 0
    const bt = new Date(b.started_at || b.date).getTime() || 0
    if (bt !== at) return bt - at
    return String(b.session_id).localeCompare(String(a.session_id))
  })
})

const selectedHistoryCycles = computed(() => selectedHistory.value?.cycles || [])

const hasData = computed(() => !!selectedHistory.value)
const filteredSessions = computed(() => {
  const q = searchQuery.value.trim()
  if (!q) return sessions.value
  return sessions.value.filter(s =>
    (s.crew_name || '').includes(q) ||
    (s.vehicle_number || '').includes(q),
  )
})

const agg = computed(() => {
  const ss = sessions.value
  if (!ss.length) return { cycles: 0, avgSr: '—', avgDl: '—' }
  const cycles = ss.reduce((a, s) => a + (s.cycle_count || 0), 0)
  const div = cycles || 1
  const avgSr = Math.round(ss.reduce((a, s) => a + (s.sr_seconds || 0), 0) / div)
  const avgDl = Math.round(ss.reduce((a, s) => a + (s.dl_seconds || 0), 0) / div)
  return { cycles, avgSr: fmtSeconds(avgSr), avgDl: fmtSeconds(avgDl) }
})

function pct(key) {
  const s = selectedSession.value
  if (!s || !s.total_seconds) return 0
  return Math.round(((s[`${key}_seconds`] || 0) / s.total_seconds) * 100)
}

function todayStr() { return new Date().toISOString().slice(0, 10) }
function fmtSeconds(sec) {
  if (sec === null || sec === undefined) return '—'
  const m = Math.floor(sec / 60), s = sec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}
function fmtTimeRange(s) { return `${fmtTime(s.started_at)} → ${fmtTime(s.ended_at)}` }
function fmtMoney(v) {
  if (v == null) return '—'
  const n = Number(v)
  if (Math.abs(n) >= 10000) return `${(n / 10000).toFixed(1)}만`
  return n.toLocaleString()
}
function fmtDateTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day} ${fmtTime(iso)}`
}

function filenameFromDisposition(header) {
  if (!header) return ''
  const encoded = header.match(/filename\*=UTF-8''([^;]+)/i)
  if (encoded?.[1]) {
    try { return decodeURIComponent(encoded[1].replace(/"/g, '')) } catch (e) {}
  }
  const plain = header.match(/filename="?([^";]+)"?/i)
  return plain?.[1] || ''
}

function sanitizeFilename(value) {
  return String(value || '')
    .replace(/[\\/:*?"<>|\s]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

async function downloadHistoryCsv(history) {
  if (!history?.session_id) return
  try {
    const response = await downloadTrackingCsv(history.session_id)
    const filename = filenameFromDisposition(response.headers['content-disposition'])
      || `${sanitizeFilename(`work_session_${history.crew_name || 'crew'}_${history.date || ''}_${history.session_id}`)}.csv`
    const blob = new Blob([response.data], {
      type: response.headers['content-type'] || 'text/csv;charset=utf-8',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('CSV 다운로드 실패: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadTeams() {
  try {
    const r = await client.get('/accounts/teams')
    teams.value = r.data.results || r.data || []
    // 초기 뷰는 '전체' — teamId 비운 채로 모든 권역을 본다
  } catch (e) { /* ignore */ }
}

async function loadSessions() {
  // 권역관리에서는 조/날짜 기준 전체 경로를 자동으로 띄우지 않는다.
  sessions.value = []
  selectedSession.value = null
  selectedHistory.value = null
  detail.cycles = []
  detail.points = []
  detail.captures = []
  if (routeLayer) routeLayer.getSource().clear()
  if (markerLayer) markerLayer.getSource().clear()
  if (highlightLayer) highlightLayer.getSource().clear()
  closePopup()
  renderTerritories()
  fitToTerritories()
}

function onTeamChange(v) {
  teamId.value = v
  // 조가 바뀌면, 선택된 권역이 새 필터에서 빠지면 해제
  if (selectedTerritory.value &&
      teamId.value &&
      Number(selectedTerritory.value.team) !== Number(teamId.value)) {
    clearTerritory()
  }
  onFilterChange()
}
function onFilterChange() { loadSessions() }

async function onDeleteClick() {
  // 권역관리에서는 전체 세션 삭제 UI 를 제공하지 않는다.
}

async function selectSession(s) {
  // 권역 선택 상태와 상호 배타 — 세션 진입시 권역 해제
  if (selectedTerritory.value) clearTerritory()
  selectedSession.value = s
  loading.value = true
  try {
    const r = await fetchTrackingSession(s.id)
    const d = r.data
    selectedSession.value = { ...s, ...d }
    detail.cycles = d.cycles || []
    detail.points = d.points || []
    detail.captures = d.captures || []
    drawDetail(d)
  } finally {
    loading.value = false
  }
}

function clearSelection({ redrawOverview = true } = {}) {
  selectedSession.value = null
  detail.cycles = []
  detail.points = []
  detail.captures = []
  if (redrawOverview) drawOverview()
}

function highlightCycle(cycle) {
  hoveredCycle.value = cycle ? cycle.cycle_no : null
  if (!vmap || !highlightLayer) return
  const src = highlightLayer.getSource()
  src.clear()
  // hover 가 해제돼도 popup 이 열려있으면 그 사이클을 highlight 유지
  const target = cycle || popupCycle.value
  if (!target) return
  const ts = new Date(target.started_at).getTime()
  const te = new Date(target.ended_at).getTime()
  const pts = detail.points.filter(p => {
    const t = new Date(p.recorded_at).getTime()
    return t >= ts && t <= te &&
      p.lat != null && p.lon != null &&
      (!selectedTerritory.value || pointInTerritory(p.lon, p.lat, selectedTerritory.value.geometry))
  })
  if (pts.length < 2) return
  const coords = pts.map(p => olLib.proj.fromLonLat([p.lon, p.lat]))
  const feat = new olLib.Feature({ geometry: new olLib.geom.LineString(coords) })
  feat.setStyle(new olLib.style.Style({
    stroke: new olLib.style.Stroke({ color: '#C8D530', width: 12, lineCap: 'round' }),
  }))
  src.addFeature(feat)
}

/* ---------- VWorld 지도 ---------- */
// 지도 라인 색상 — In Vehicle 파랑 · Searching 노랑 · Delivering 초록
const STATE_COLORS = { IV: '#2563EB', SR: '#FACC15', DL: '#22C55E' }
let popupOverlay = null
let _pendingExtent = null
const hitTolerance = 10

async function initMap() {
  if (vmap) return
  try {
    const { vw, ol } = await loadVWorld()
    olLib = ol

    const options = {
      basemapType: vw.ol3.BasemapType.GRAPHIC,
      controlDensity: vw.ol3.DensityType.EMPTY,
      interactionDensity: vw.ol3.DensityType.BASIC,
      controlsAutoArrange: true,
      homePosition: vw.ol3.CameraPosition,
      initPosition: vw.ol3.CameraPosition,
    }
    vmap = new vw.ol3.Map('vw-tracking-map', options)

    const center = ol.proj.fromLonLat([126.9784, 37.5665])
    vmap.getView().setCenter(center)
    vmap.getView().setZoom(12)

    territoryLayer = new ol.layer.Vector({ source: new ol.source.Vector(), zIndex: 3 })
    routeLayer = new ol.layer.Vector({ source: new ol.source.Vector(), zIndex: 5 })
    markerLayer = new ol.layer.Vector({ source: new ol.source.Vector(), zIndex: 8 })
    manpowerLayer = new ol.layer.Vector({ source: new ol.source.Vector(), zIndex: 9 })
    highlightLayer = new ol.layer.Vector({ source: new ol.source.Vector(), zIndex: 10 })
    vmap.addLayer(territoryLayer)
    vmap.addLayer(routeLayer)
    vmap.addLayer(markerLayer)
    vmap.addLayer(manpowerLayer)
    vmap.addLayer(highlightLayer)

    // 팝업 overlay (segment/세션 클릭 시 사이클 상세)
    if (popupEl.value) {
      popupOverlay = new ol.Overlay({
        element: popupEl.value,
        positioning: 'bottom-center',
        offset: [0, -16],
        stopEvent: true,
      })
      vmap.addOverlay(popupOverlay)
    }

    // 클릭: route(최우선) → territory → 빈곳(닫기)
    vmap.on('click', (evt) => {
      if (drawing.value) return

      // 우선순위대로 수집
      let routeFeat = null
      let territoryFeat = null
      vmap.forEachFeatureAtPixel(evt.pixel, (f) => {
        if (!routeFeat && (f.get('sessionId') !== undefined || f.get('cycleNo') !== undefined)) {
          routeFeat = f
        } else if (!territoryFeat && f.get('territoryId') !== undefined) {
          territoryFeat = f
        }
      }, { hitTolerance })

      // 1) 경로/세그먼트 히트
      if (routeFeat) {
        if (!selectedSession.value && !selectedHistory.value) {
          const sid = routeFeat.get('sessionId')
          const s = sessions.value.find(x => x.id === sid)
          if (s) selectSession(s)
          return
        }
        const cn = routeFeat.get('cycleNo')
        if (cn != null) {
          const cyc = detail.cycles.find(c => c.cycle_no === cn)
          if (cyc) {
            popupCycle.value = cyc
            if (popupOverlay) popupOverlay.setPosition(evt.coordinate)
            highlightCycle(cyc)
            scrollCycleIntoView(cn)
          }
        }
        return
      }

      // 2) 권역 폴리곤 히트
      if (territoryFeat) {
        const tid = territoryFeat.get('territoryId')
        const t = territories.value.find(x => x.id === tid)
        if (t) selectTerritory(t)
        return
      }

      // 3) 빈곳: 팝업만 닫고 권역/세션 선택은 유지
      closePopup()
    })

    // 호버 시 pointer 커서
    vmap.on('pointermove', (evt) => {
      if (evt.dragging) return
      let hit = false
      vmap.forEachFeatureAtPixel(evt.pixel, (f) => {
        if (f.get('sessionId') !== undefined ||
            f.get('cycleNo') !== undefined ||
            f.get('territoryId') !== undefined) {
          hit = true; return true
        }
      }, { hitTolerance })
      vmap.getTargetElement().style.cursor = hit ? 'pointer' : ''
    })

    if (typeof ResizeObserver !== 'undefined' && mapEl.value) {
      const ro = new ResizeObserver(() => {
        if (!vmap) return
        vmap.updateSize()
        // pending extent 가 있으면 리사이즈 후 재적용
        if (_pendingExtent) applyFit(_pendingExtent, _pendingExtent.opts)
      })
      ro.observe(mapEl.value)
    }
    setTimeout(() => vmap.updateSize && vmap.updateSize(), 200)
  } catch (e) {
    console.error('[TrackingView] VWorld init failed:', e)
    mapError.value = e.message || '알 수 없는 오류'
  }
}

function closePopup() {
  popupCycle.value = null
  if (popupOverlay) popupOverlay.setPosition(undefined)
  highlightCycle(null)
}

/* =========== 권역 관련 =========== */
function _hexToRgba(hex, a) {
  if (!hex || hex[0] !== '#' || hex.length !== 7) return `rgba(37,99,235,${a})`
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${a})`
}

const visibleTerritories = computed(() => {
  // 조 선택 없으면 지도/우측 목록을 비운다. 선택되면 해당 조 것만 표시.
  // 과거 import 데이터는 team FK 없이 group_letter 만 있는 경우가 있어 둘 다 본다.
  if (!teamId.value) return []
  const selectedTeam = teams.value.find(x => x.id === Number(teamId.value))
  const code = (selectedTeam?.code || '').toUpperCase()
  return territories.value.filter(t =>
    Number(t.team) === Number(teamId.value) ||
    (!!code && String(t.group_letter || '').toUpperCase() === code),
  )
})

function renderTerritories() {
  if (!territoryLayer || !olLib) return
  const src = territoryLayer.getSource()
  src.clear()
  for (const t of visibleTerritories.value) {
    if (!t.geometry || !t.geometry.type) continue
    const isSel = selectedTerritory.value && selectedTerritory.value.id === t.id
    const style = new olLib.style.Style({
      stroke: new olLib.style.Stroke({
        color: isSel ? '#111827' : (t.color || '#2563EB'),
        width: isSel ? 3 : 1.5,
      }),
      fill: new olLib.style.Fill({
        color: _hexToRgba(t.color || '#2563EB', isSel ? 0.35 : 0.15),
      }),
      text: !selectedTerritory.value ? new olLib.style.Text({
        text: t.code,
        font: 'bold 12px sans-serif',
        fill: new olLib.style.Fill({ color: '#111827' }),
        stroke: new olLib.style.Stroke({ color: '#FFFFFF', width: 4 }),
        overflow: true,
      }) : undefined,
    })
    let geom = null
    if (t.geometry.type === 'Polygon') {
      const coords = t.geometry.coordinates.map(ring => ring.map(c => olLib.proj.fromLonLat(c)))
      geom = new olLib.geom.Polygon(coords)
    } else if (t.geometry.type === 'MultiPolygon') {
      const coords = t.geometry.coordinates.map(p => p.map(ring => ring.map(c => olLib.proj.fromLonLat(c))))
      geom = new olLib.geom.MultiPolygon(coords)
    }
    if (!geom) continue
    const feat = new olLib.Feature({ geometry: geom })
    feat.set('territoryId', t.id)
    feat.setStyle(style)
    src.addFeature(feat)
  }
}

function fitToTerritories() {
  if (!vmap || !territoryLayer) return
  const ext = territoryLayer.getSource().getExtent()
  if (ext && isFinite(ext[0])) {
    applyFit(ext, { padding: [60, 60, 60, 60], maxZoom: 15 })
  }
}

function fitToTerritory(t) {
  if (!vmap || !territoryLayer || !t) return
  const feat = territoryLayer.getSource().getFeatures()
    .find(f => f.get('territoryId') === t.id)
  if (feat) {
    applyFit(feat.getGeometry().getExtent(), { padding: [70, 70, 70, 70], maxZoom: 17 })
    return
  }
  if (t.centroid_lat != null && t.centroid_lon != null) {
    vmap.getView().setCenter(olLib.proj.fromLonLat([t.centroid_lon, t.centroid_lat]))
    vmap.getView().setZoom(15)
  }
}

async function loadTerritories() {
  try {
    const r = await listTerritories()
    territories.value = r.data.results || r.data || []
    renderTerritories()
    // 초기엔 조/날짜 없으므로 전체 권역으로 fit
    if (!teamId.value && !selectedDate.value && !selectedSession.value) {
      fitToTerritories()
    }
  } catch (e) { /* ignore */ }
}

async function selectTerritory(t) {
  // 세션 detail 은 닫고 권역 모드로 전환
  selectedSession.value = null
  selectedHistory.value = null
  territoryPanelMode.value = 'overview'
  detail.cycles = []
  detail.points = []
  detail.captures = []
  clearLayers()
  if (manpowerLayer) manpowerLayer.getSource().clear()
  selectedTerritory.value = t
  territoryBoxes.value = []
  territoryCycles.value = { cycles: [], summary: null }
  nearbyManpower.value = []
  renderTerritories()

  fitToTerritory(t)

  // 두 API 를 독립적으로 호출 — 하나가 실패해도 다른 쪽은 표시
  try {
    const bs = await territoryBoxSeries(t.id)
    territoryBoxes.value = Array.isArray(bs.data) ? bs.data : (bs.data?.results || [])
  } catch (e) {
    console.error('[territory] box_series failed', e.response?.status, e.response?.data)
    territoryBoxes.value = []
  }
  try {
    const ci = await territoryCyclesInside(t.id)
    territoryCycles.value = ci.data || { cycles: [], summary: null }
  } catch (e) {
    console.error('[territory] cycles_inside failed', e.response?.status, e.response?.data)
    territoryCycles.value = { cycles: [], summary: null }
  }
}

function clearTerritory() {
  selectedTerritory.value = null
  selectedHistory.value = null
  territoryPanelMode.value = 'overview'
  territoryBoxes.value = []
  territoryCycles.value = { cycles: [], summary: null }
  nearbyManpower.value = []
  if (manpowerLayer) manpowerLayer.getSource().clear()
  clearLayers()
  renderTerritories()
}

async function changeTerritoryColor(e) {
  if (!selectedTerritory.value) return
  const color = e.target.value
  try {
    await updateTerritory(selectedTerritory.value.id, { color })
    selectedTerritory.value.color = color
    const idx = territories.value.findIndex(x => x.id === selectedTerritory.value.id)
    if (idx >= 0) territories.value[idx].color = color
    renderTerritories()
  } catch (err) { /* ignore */ }
}

async function removeTerritory() {
  const t = selectedTerritory.value
  if (!t) return
  if (!confirm(`'${t.code}' 권역을 삭제할까요?`)) return
  try {
    await deleteTerritory(t.id)
    clearTerritory()
    await loadTerritories()
  } catch (e) {
    alert('삭제 실패: ' + (e.response?.data?.detail || e.message))
  }
}

function toggleDraw() {
  if (drawing.value) {
    if (drawInteraction) vmap.removeInteraction(drawInteraction)
    drawInteraction = null
    drawing.value = false
    return
  }
  if (!olLib) return
  drawInteraction = new olLib.interaction.Draw({
    source: territoryLayer.getSource(), type: 'Polygon',
  })
  drawInteraction.on('drawend', (evt) => {
    pendingPolygon.value = evt.feature
    pendingCode.value = ''
    drawing.value = false
    vmap.removeInteraction(drawInteraction)
    drawInteraction = null
  })
  vmap.addInteraction(drawInteraction)
  drawing.value = true
}

async function savePendingPolygon() {
  if (!pendingPolygon.value) return
  const code = pendingCode.value.trim()
  if (!code) { alert('권역 이름을 입력하세요'); return }
  const geom = pendingPolygon.value.getGeometry()
  const coords = geom.getCoordinates().map(ring => ring.map(c => olLib.proj.toLonLat(c)))
  try {
    await createTerritory({
      code,
      team: teamId.value || null,
      geometry: { type: 'Polygon', coordinates: coords },
    })
    // draw 레이어에 임시로 그려진 feature 제거 (재로드로 대체됨)
    territoryLayer.getSource().removeFeature(pendingPolygon.value)
    pendingPolygon.value = null
    pendingCode.value = ''
    await loadTerritories()
  } catch (e) {
    alert('저장 실패: ' + (e.response?.data?.detail || JSON.stringify(e.response?.data || e.message)))
  }
}

function cancelPendingPolygon() {
  if (pendingPolygon.value && territoryLayer) {
    try { territoryLayer.getSource().removeFeature(pendingPolygon.value) } catch (e) {}
  }
  pendingPolygon.value = null
  pendingCode.value = ''
}

function openBoxEditor() {
  boxEdit.value = { date: new Date().toISOString().slice(0, 10), box_count: 0 }
}
async function saveBoxEditor() {
  if (!selectedTerritory.value || !boxEdit.value) return
  try {
    await setTerritoryBoxes(selectedTerritory.value.id, boxEdit.value)
    boxEdit.value = null
    const r = await territoryBoxSeries(selectedTerritory.value.id)
    territoryBoxes.value = r.data || []
  } catch (e) {
    alert('저장 실패: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadNearbyManpower() {
  if (!selectedTerritory.value) return
  try {
    const r = await territoryNearbyManpower(selectedTerritory.value.id, 10000)
    nearbyManpower.value = r.data || []
    if (manpowerLayer && olLib) {
      const src = manpowerLayer.getSource()
      src.clear()
      for (const m of nearbyManpower.value) {
        if (m.lat == null || m.lon == null) continue
        const f = new olLib.Feature({ geometry: new olLib.geom.Point(olLib.proj.fromLonLat([m.lon, m.lat])) })
        f.setStyle(new olLib.style.Style({
          image: new olLib.style.Circle({
            radius: 6,
            fill: new olLib.style.Fill({ color: '#2980B9' }),
            stroke: new olLib.style.Stroke({ color: '#FFFFFF', width: 2 }),
          }),
        }))
        src.addFeature(f)
      }
    }
  } catch (e) {
    alert('근처 인력 조회 실패: ' + (e.response?.data?.detail || e.message))
  }
}

function showOverviewPanel() {
  territoryPanelMode.value = 'overview'
  selectedHistory.value = null
  detail.cycles = []
  detail.points = []
  detail.captures = []
  if (routeLayer) routeLayer.getSource().clear()
  if (markerLayer) markerLayer.getSource().clear()
  if (highlightLayer) highlightLayer.getSource().clear()
  if (manpowerLayer) manpowerLayer.getSource().clear()
  closePopup()
  renderTerritories()
  if (selectedTerritory.value) fitToTerritory(selectedTerritory.value)
}

async function showManpowerPanel() {
  territoryPanelMode.value = 'manpower'
  selectedHistory.value = null
  detail.cycles = []
  detail.points = []
  detail.captures = []
  if (routeLayer) routeLayer.getSource().clear()
  if (markerLayer) markerLayer.getSource().clear()
  if (highlightLayer) highlightLayer.getSource().clear()
  if (manpowerLayer) manpowerLayer.getSource().clear()
  closePopup()
  renderTerritories()
  await loadNearbyManpower()
}

function pointInRing(lon, lat, ring) {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1]
    const xj = ring[j][0], yj = ring[j][1]
    const intersect = ((yi > lat) !== (yj > lat)) &&
      (lon < ((xj - xi) * (lat - yi)) / ((yj - yi) || 1e-12) + xi)
    if (intersect) inside = !inside
  }
  return inside
}

function pointInPolygon(lon, lat, polygon) {
  if (!polygon?.length || !pointInRing(lon, lat, polygon[0])) return false
  return !polygon.slice(1).some(ring => pointInRing(lon, lat, ring))
}

function pointInTerritory(lon, lat, geom) {
  if (!geom) return false
  if (geom.type === 'Polygon') return pointInPolygon(lon, lat, geom.coordinates)
  if (geom.type === 'MultiPolygon') return (geom.coordinates || []).some(poly => pointInPolygon(lon, lat, poly))
  return false
}

async function onTerritoryHistoryClick(history) {
  if (!selectedTerritory.value) return
  selectedHistory.value = history
  territoryPanelMode.value = 'cycles'
  if (manpowerLayer) manpowerLayer.getSource().clear()
  loading.value = true
  try {
    const [pointsResponse, capturesResponse] = await Promise.all([
      fetchSessionPoints(history.session_id),
      fetchSessionCaptures(history.session_id),
    ])
    detail.cycles = history.cycles || []
    detail.points = pointsResponse.data || []
    detail.captures = capturesResponse.data || []
    drawClippedHistory(detail.points)
  } catch (e) {
    alert('Failed to load route details: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function drawClippedHistory(points) {
  if (!vmap || !routeLayer || !markerLayer) return
  clearLayers()
  renderTerritories()
  if (!points.length) {
    alert('해당 이력의 권역 내부 경로 포인트가 없습니다.')
    fitToTerritory(selectedTerritory.value)
    return
  }

  const src = routeLayer.getSource()
  const mSrc = markerLayer.getSource()
  const extent = _emptyExtent()
  const insidePoints = []
  let current = []
  let currentState = null
  let currentCycleId = null

  const flushSegment = () => {
    if (current.length >= 2) {
      const state = current[0].state
      const coords = current.map(p => olLib.proj.fromLonLat([p.lon, p.lat]))
      const feat = new olLib.Feature({ geometry: new olLib.geom.LineString(coords) })
      feat.set('state', state)
      feat.set('cycleNo', _cycleNoOf(current[0]))
      feat.setStyle(new olLib.style.Style({
        stroke: new olLib.style.Stroke({
          color: STATE_COLORS[state] || '#111827',
          width: 7,
          lineCap: 'round',
          lineJoin: 'round',
        }),
      }))
      src.addFeature(feat)
    }
    current = []
    currentState = null
    currentCycleId = null
  }

  for (const p of points) {
    const inside = p.lat != null && p.lon != null &&
      pointInTerritory(p.lon, p.lat, selectedTerritory.value.geometry)
    if (!inside) {
      flushSegment()
      continue
    }

    const state = p.state || ''
    const cycleId = p.cycle_id || 0
    if (current.length && (state !== currentState || cycleId !== currentCycleId)) {
      flushSegment()
    }

    currentState = state
    currentCycleId = cycleId
    current.push(p)
    insidePoints.push(p)
    _extendExtent(extent, olLib.proj.fromLonLat([p.lon, p.lat]))
  }
  flushSegment()

  if (!insidePoints.length) {
    alert('해당 이력의 권역 내부 경로 포인트가 없습니다.')
    fitToTerritory(selectedTerritory.value)
    return
  }

  const first = insidePoints[0]
  const last = insidePoints[insidePoints.length - 1]
  const startFeat = new olLib.Feature({ geometry: new olLib.geom.Point(olLib.proj.fromLonLat([first.lon, first.lat])) })
  startFeat.setStyle(makeBadgeStyle('#2563EB', 'S', 10))
  mSrc.addFeature(startFeat)
  const endFeat = new olLib.Feature({ geometry: new olLib.geom.Point(olLib.proj.fromLonLat([last.lon, last.lat])) })
  endFeat.setStyle(makeBadgeStyle('#111827', 'E', 10))
  mSrc.addFeature(endFeat)

  for (const c of detail.captures || []) {
    if (c.lat == null || c.lon == null) continue
    if (!pointInTerritory(c.lon, c.lat, selectedTerritory.value.geometry)) continue
    const coord = olLib.proj.fromLonLat([c.lon, c.lat])
    const f = new olLib.Feature({ geometry: new olLib.geom.Point(coord) })
    f.setStyle(makeDotStyle('#E74C3C', 8))
    mSrc.addFeature(f)
    _extendExtent(extent, coord)
  }

  if (isFinite(extent[0])) {
    applyFit(extent, { padding: [60, 60, 60, 60], maxZoom: 18 })
  } else {
    fitToTerritory(selectedTerritory.value)
  }
}

const maxBox = computed(() => Math.max(1, ...territoryBoxes.value.map(b => b.box_count || 0)))
const boxTotal = computed(() => Math.round(territoryBoxes.value.reduce((a, b) => a + (b.box_count || 0), 0)))
const boxAvg = computed(() => territoryBoxes.value.length
  ? Math.round(boxTotal.value / territoryBoxes.value.length)
  : 0)
function boxRowKey(b) {
  return `${b.date || 'date'}-${b.territory || 'territory'}-${b.source || 'source'}`
}
function boxBarHeight(b) {
  const value = Number(b?.box_count || 0)
  if (!value || !maxBox.value) return 4
  return Math.max(4, Math.min(100, Math.round((value / maxBox.value) * 100)))
}

function scrollCycleIntoView(cycleNo) {
  const el = document.querySelector(`[data-cycle="${cycleNo}"]`)
  if (el && el.scrollIntoView) {
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
}

function onCycleCardClick(cyc) {
  popupCycle.value = cyc
  highlightCycle(cyc)

  // 사이클 구간 포인트들을 추출
  const ts = new Date(cyc.started_at).getTime()
  const te = new Date(cyc.ended_at).getTime()
  const cyclePts = detail.points.filter(p => {
    const t = new Date(p.recorded_at).getTime()
    return t >= ts && t <= te &&
      p.lat != null && p.lon != null &&
      (!selectedTerritory.value || pointInTerritory(p.lon, p.lat, selectedTerritory.value.geometry))
  })
  if (!cyclePts.length) return

  // 1) 해당 사이클 extent 로 zoom-to-layer
  const ext = [Infinity, Infinity, -Infinity, -Infinity]
  for (const p of cyclePts) {
    const xy = olLib.proj.fromLonLat([p.lon, p.lat])
    if (xy[0] < ext[0]) ext[0] = xy[0]
    if (xy[1] < ext[1]) ext[1] = xy[1]
    if (xy[0] > ext[2]) ext[2] = xy[0]
    if (xy[1] > ext[3]) ext[3] = xy[1]
  }
  applyFit(ext, { padding: [80, 80, 80, 80], maxZoom: 19 })

  // 2) 팝업을 사이클 중간 포인트에 앵커링
  if (popupOverlay) {
    const mid = cyclePts[Math.floor(cyclePts.length / 2)]
    popupOverlay.setPosition(olLib.proj.fromLonLat([mid.lon, mid.lat]))
  }
}

function clearLayers() {
  ;[routeLayer, markerLayer, highlightLayer].forEach(l => l && l.getSource().clear())
  closePopup()
}

function _extendExtent(ext, xy) {
  if (ext[0] > xy[0]) ext[0] = xy[0]
  if (ext[1] > xy[1]) ext[1] = xy[1]
  if (ext[2] < xy[0]) ext[2] = xy[0]
  if (ext[3] < xy[1]) ext[3] = xy[1]
}
const _emptyExtent = () => [Infinity, Infinity, -Infinity, -Infinity]

async function drawOverview() {
  if (!vmap) return
  clearLayers()
  const src = routeLayer.getSource()
  const mSrc = markerLayer.getSource()
  const extent = _emptyExtent()

  for (const s of sessions.value) {
    try {
      const { data } = await client.get(`/tracking/sessions/${s.id}/points/`)
      const pts = (data || []).filter(p => p.lat != null && p.lon != null)
      if (!pts.length) continue
      const coords = pts.map(p => {
        const xy = olLib.proj.fromLonLat([p.lon, p.lat])
        _extendExtent(extent, xy)
        return xy
      })
      const feat = new olLib.Feature({ geometry: new olLib.geom.LineString(coords) })
      feat.set('sessionId', s.id)
      feat.setStyle(new olLib.style.Style({
        stroke: new olLib.style.Stroke({
          color: withAlpha(s.route_color, toneOthers.value ? 0.85 : 1),
          width: 4, lineCap: 'round', lineJoin: 'round',
        }),
      }))
      src.addFeature(feat)

      const startFeat = new olLib.Feature({ geometry: new olLib.geom.Point(coords[0]) })
      startFeat.setStyle(makeDotStyle(s.route_color, 7))
      mSrc.addFeature(startFeat)
    } catch (e) { /* skip */ }
  }
  if (isFinite(extent[0])) {
    applyFit(extent, { padding: [40, 40, 40, 40], maxZoom: 17 })
  } else {
    fitToTerritories()
  }
}

function drawDetail(session) {
  if (!vmap) return
  clearLayers()
  const src = routeLayer.getSource()
  const mSrc = markerLayer.getSource()
  const pts = session.points || []
  if (!pts.length) return
  const extent = _emptyExtent()

  // state 별 연속 segment 로 분할 — 각 feature 에 cycleNo/state 부여
  let segStart = 0
  for (let i = 1; i <= pts.length; i++) {
    const boundary = i === pts.length ||
      pts[i].state !== pts[segStart].state ||
      (pts[i].cycle_id || 0) !== (pts[segStart].cycle_id || 0)
    if (!boundary) continue
    const slice = pts.slice(Math.max(0, segStart - 1), i + 1)
    if (slice.length >= 2) {
      const coords = slice.map(p => {
        const xy = olLib.proj.fromLonLat([p.lon, p.lat])
        _extendExtent(extent, xy)
        return xy
      })
      const state = pts[segStart].state
      const feat = new olLib.Feature({ geometry: new olLib.geom.LineString(coords) })
      feat.set('state', state)
      feat.set('cycleNo', _cycleNoOf(pts[segStart]))
      feat.setStyle(new olLib.style.Style({
        stroke: new olLib.style.Stroke({
          color: STATE_COLORS[state] || '#777',
          width: 7, lineCap: 'round', lineJoin: 'round',
        }),
      }))
      src.addFeature(feat)
    }
    segStart = i
  }

  const start = new olLib.Feature({
    geometry: new olLib.geom.Point(olLib.proj.fromLonLat([pts[0].lon, pts[0].lat])),
  })
  start.setStyle(makeBadgeStyle(STATE_COLORS.IV, 'S'))
  mSrc.addFeature(start)
  const endPt = pts[pts.length - 1]
  const end = new olLib.Feature({
    geometry: new olLib.geom.Point(olLib.proj.fromLonLat([endPt.lon, endPt.lat])),
  })
  end.setStyle(makeBadgeStyle('#111827', 'E'))
  mSrc.addFeature(end)

  // camera end points
  for (const c of session.captures || []) {
    if (c.lat == null || c.lon == null) continue
    const coord = olLib.proj.fromLonLat([c.lon, c.lat])
    const f = new olLib.Feature({ geometry: new olLib.geom.Point(coord) })
    f.setStyle(makeDotStyle('#E74C3C', 8))
    mSrc.addFeature(f)
  }

  applyFit(extent, { padding: [50, 50, 50, 50], maxZoom: 19 })
}

// cycle_id(DB PK) → cycle_no 매핑. detail.cycles 각 항목에 { id, cycle_no } 있음.
function _cycleNoOf(pt) {
  if (!pt || pt.state === 'IV' || pt.cycle_id == null) return null
  const c = detail.cycles.find(x => x.id === pt.cycle_id)
  return c ? c.cycle_no : null
}

function makeDotStyle(color, radius = 6) {
  return new olLib.style.Style({
    image: new olLib.style.Circle({
      radius,
      fill: new olLib.style.Fill({ color }),
      stroke: new olLib.style.Stroke({ color: '#FFFFFF', width: 2 }),
    }),
  })
}
function makeBadgeStyle(color, text = '', fontSize = 12) {
  return new olLib.style.Style({
    image: new olLib.style.Circle({
      radius: 12,
      fill: new olLib.style.Fill({ color }),
      stroke: new olLib.style.Stroke({ color: '#FFFFFF', width: 3 }),
    }),
    text: text ? new olLib.style.Text({
      text,
      font: `bold ${fontSize}px sans-serif`,
      fill: new olLib.style.Fill({ color: '#FFFFFF' }),
    }) : undefined,
  })
}

function withAlpha(hex, alpha) {
  // #RRGGBB -> rgba()
  if (!hex || hex[0] !== '#' || hex.length !== 7) return hex
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

/**
 * ext: [minX, minY, maxX, maxY]  (EPSG:3857, meters)
 * 지도 픽셀 크기를 직접 측정해서 필요한 resolution(m/px)을 계산하고,
 * setCenter + setResolution 으로 결정론적 fit 을 수행한다.
 * (vmap.getView().fit() 은 VWorld 래퍼 · 애니메이션 · 레이아웃 타이밍 이슈 때문에 사용하지 않음)
 */
function applyFit(ext, opts = {}) {
  if (!vmap || !ext || !isFinite(ext[0]) || !isFinite(ext[2])) return
  _pendingExtent = Object.assign([...ext], { opts })

  const paddingPx = (Array.isArray(opts.padding) ? Math.max(...opts.padding) : opts.padding) || 40
  const maxZoom = opts.maxZoom || 18

  const run = () => {
    vmap.updateSize()
    const size = vmap.getSize()
    if (!size || !size[0] || !size[1]) return false

    const [minX, minY, maxX, maxY] = ext
    const extW = maxX - minX
    const extH = maxY - minY

    const cx = (minX + maxX) / 2
    const cy = (minY + maxY) / 2
    const view = vmap.getView()
    view.setCenter([cx, cy])

    if (extW <= 0 || extH <= 0) {
      view.setZoom(Math.min(17, maxZoom))
      return true
    }

    const availW = Math.max(16, size[0] - 2 * paddingPx)
    const availH = Math.max(16, size[1] - 2 * paddingPx)
    // 두 축 중 더 많이 필요한 resolution 을 택해 양쪽 다 담기게
    const targetRes = Math.max(extW / availW, extH / availH)
    view.setResolution(targetRes)

    if (maxZoom != null && typeof view.getZoom === 'function') {
      const z = view.getZoom()
      if (z != null && z > maxZoom) view.setZoom(maxZoom)
    }
    return true
  }

  // 레이아웃 확정 + VWorld 내부 tile 로드 타이밍 보정
  // 여러 시점에서 시도해 반드시 성공시킴 (실패해도 재시도)
  requestAnimationFrame(() => requestAnimationFrame(() => { run() }))
  setTimeout(run, 120)
  setTimeout(run, 400)
}

function fitToAll() {
  if (!routeLayer) {
    fitToTerritories()
    return
  }
  const ext = routeLayer.getSource().getExtent()
  if (ext && isFinite(ext[0])) {
    applyFit(ext, { padding: [40, 40, 40, 40], maxZoom: 17 })
  } else {
    fitToTerritories()
  }
}

function fitToSelected() {
  if (!selectedHistory.value || !routeLayer) return
  const ext = routeLayer.getSource().getExtent()
  if (ext && isFinite(ext[0])) applyFit(ext, { padding: [50, 50, 50, 50], maxZoom: 19 })
}

watch(toneOthers, () => {})

onMounted(async () => {
  await nextTick()
  try { await initMap() } catch (e) { console.error('VWorld init failed', e) }
  await loadTeams()
  // 권역 먼저 로드 후 세션 (초기 뷰에서 권역이 보이도록)
  await loadTerritories()
  await loadSessions()
})
</script>
