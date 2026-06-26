<template>
  <AppLayout>
    <div class="space-y-4">
      <!-- 툴바 -->
      <div class="bg-white rounded-xl p-4 border border-gray-200 flex items-center gap-3 flex-wrap">
        <label class="px-3 py-2 text-sm rounded-lg bg-primary text-white cursor-pointer hover:bg-primary-dark">
          📥 GeoJSON 업로드
          <input type="file" accept=".geojson,.json" class="hidden" @change="onGeojsonUpload" />
        </label>

        <button @click="toggleDraw" :class="drawing ? 'bg-danger text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
          class="px-3 py-2 text-sm rounded-lg">
          {{ drawing ? '✕ 그리기 중단' : '✎ 새 권역 그리기' }}
        </button>

        <div class="flex-1"></div>
        <span class="text-xs text-gray-400">총 {{ territories.length }}개 권역</span>
      </div>

      <!-- 지도 + 사이드 패널 -->
      <div class="flex gap-5" style="height: 720px">
        <div class="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden relative">
          <div id="vw-territory-map" ref="mapEl" class="absolute inset-0" style="width:100%;height:100%"></div>
          <div v-if="mapError" class="absolute inset-0 flex items-center justify-center bg-white/90 z-20">
            <div class="max-w-sm text-center text-sm text-danger">{{ mapError }}</div>
          </div>
          <div v-if="drawing" class="absolute left-4 top-4 bg-gray-800 text-white text-xs px-3 py-1.5 rounded-lg shadow-lg z-10">
            지도를 클릭해 폴리곤을 그리세요. 마지막 점을 더블클릭하면 마무리됩니다.
          </div>
        </div>

        <!-- 사이드 패널 -->
        <div class="w-[400px] bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden">
          <div class="p-4 border-b border-gray-200">
            <h3 class="font-bold text-text mb-2">권역 목록</h3>
            <input v-model="search" placeholder="권역 코드 검색" type="text"
              class="w-full px-2 py-1.5 text-sm rounded border border-gray-200" />
          </div>

          <div class="flex-1 overflow-y-auto p-2 space-y-1">
            <div v-if="!filteredTerritories.length" class="text-center text-xs text-gray-400 py-6">
              등록된 권역이 없습니다
            </div>
            <button v-for="t in filteredTerritories" :key="t.id" @click="selectTerritory(t)"
              :class="selected && selected.id === t.id ? 'bg-primary-light border-primary' : 'bg-white border-gray-100 hover:border-primary'"
              class="w-full text-left p-3 rounded-lg border flex items-center gap-3 transition">
              <span class="w-3 h-3 rounded-sm flex-shrink-0" :style="{ background: t.color || '#2563EB' }"></span>
              <div class="flex-1">
                <div class="text-sm font-bold">{{ t.code }}</div>
                <div class="text-[11px] text-gray-500">조 {{ t.group_letter || '—' }} · 용차 {{ t.yongcha_delivery_count || 0 }}회</div>
              </div>
              <button @click.stop="removeTerritory(t)" class="text-danger text-xs hover:underline">삭제</button>
            </button>
          </div>

          <!-- 선택된 권역 상세 -->
          <div v-if="selected" class="p-4 border-t border-gray-200 bg-gray-50 space-y-3 max-h-[55%] overflow-y-auto">
            <div class="flex items-center justify-between">
              <div>
                <div class="text-sm font-bold">{{ selected.code }}</div>
                <div class="text-[11px] text-gray-500">조 {{ selected.group_letter || '—' }}</div>
              </div>
              <input type="color" :value="selected.color || '#2563EB'" @change="changeColor($event)"
                class="w-8 h-8 rounded border border-gray-200 cursor-pointer" title="표시 색상" />
            </div>

            <!-- 일별 박스수 -->
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-semibold text-gray-600">일별 박스수</span>
                <button @click="openBoxEditor" class="text-[10px] text-primary-dark hover:underline">+ 추가</button>
              </div>
              <div v-if="!boxSeries.length" class="text-[11px] text-gray-400 py-2">데이터 없음 · 배차표 업로드 또는 직접 추가</div>
              <div v-else class="flex items-end gap-0.5 h-16">
                <div v-for="b in boxSeries" :key="b.id" class="flex-1 bg-primary rounded-t"
                  :title="`${b.date} · ${b.box_count} 박스`"
                  :style="{ height: Math.min(100, (b.box_count / maxBox) * 100) + '%' }"></div>
              </div>
              <div v-if="boxSeries.length" class="flex justify-between text-[9px] text-gray-400 mt-0.5">
                <span>{{ boxSeries[0].date }}</span>
                <span>{{ boxSeries[boxSeries.length - 1].date }}</span>
              </div>
            </div>

            <!-- 사이클 통계 -->
            <div>
              <span class="text-xs font-semibold text-gray-600">권역 내 촬영 사이클</span>
              <div v-if="cyclesSummary" class="grid grid-cols-3 gap-2 mt-1">
                <div class="bg-white rounded p-2 border border-gray-100 text-center">
                  <div class="text-[10px] text-gray-400">평균 IV</div>
                  <div class="text-sm font-bold">{{ fmtSec(cyclesSummary.avg_iv_sec) }}</div>
                </div>
                <div class="bg-white rounded p-2 border border-gray-100 text-center">
                  <div class="text-[10px] text-gray-400">평균 SR</div>
                  <div class="text-sm font-bold text-warning">{{ fmtSec(cyclesSummary.avg_sr_sec) }}</div>
                </div>
                <div class="bg-white rounded p-2 border border-gray-100 text-center">
                  <div class="text-[10px] text-gray-400">평균 DL</div>
                  <div class="text-sm font-bold text-success">{{ fmtSec(cyclesSummary.avg_dl_sec) }}</div>
                </div>
              </div>
              <div class="mt-1 text-[10px] text-gray-500">
                촬영 {{ cyclesSummary?.capture_count || 0 }}건 · 사이클 {{ cyclesSummary?.cycle_count || 0 }}개
              </div>
            </div>

            <button @click="loadNearbyManpower" class="w-full px-3 py-2 rounded-lg bg-info text-white text-sm font-semibold hover:opacity-90">
              👥 근처 인력 풀
            </button>
            <div v-if="nearbyList.length" class="space-y-1">
              <div v-for="m in nearbyList" :key="m.id" class="bg-white rounded p-2 border border-gray-100 flex items-center gap-2 text-xs">
                <span class="font-bold">{{ m.name }}</span>
                <span v-if="m.has_vehicle" class="px-1.5 py-0.5 rounded bg-primary-light text-primary-dark text-[9px]">차량</span>
                <span class="text-gray-400">{{ m.experience_years }}년</span>
                <span class="ml-auto text-gray-500">{{ Math.round(m.distance_m) }}m</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 박스수 수동 입력 모달 -->
      <div v-if="boxEdit" class="fixed inset-0 bg-black/40 z-40 flex items-center justify-center" @click.self="boxEdit = null">
        <div class="w-[360px] bg-white rounded-xl p-5 border border-gray-200 space-y-3">
          <h3 class="font-bold text-text">{{ selected.code }} · 박스수 입력</h3>
          <label class="block text-sm">날짜<input v-model="boxEdit.date" type="date" class="mt-1 w-full px-2 py-1.5 border border-gray-200 rounded" /></label>
          <label class="block text-sm">박스 수<input v-model.number="boxEdit.box_count" type="number" min="0" class="mt-1 w-full px-2 py-1.5 border border-gray-200 rounded" /></label>
          <div class="flex justify-end gap-2">
            <button @click="boxEdit = null" class="px-3 py-1.5 rounded bg-gray-100 text-sm">취소</button>
            <button @click="saveBoxEdit" class="px-3 py-1.5 rounded bg-primary text-white text-sm font-semibold">저장</button>
          </div>
        </div>
      </div>

      <!-- 폴리곤 저장 모달 (드로잉 완료 시) -->
      <div v-if="pendingPolygon" class="fixed inset-0 bg-black/40 z-40 flex items-center justify-center" @click.self="cancelPending">
        <div class="w-[360px] bg-white rounded-xl p-5 border border-gray-200 space-y-3">
          <h3 class="font-bold text-text">권역 이름 입력</h3>
          <input v-model="pendingCode" placeholder="예: 30X4" type="text" class="w-full px-2 py-1.5 border border-gray-200 rounded" />
          <div class="text-[10px] text-gray-500">'30X4' 처럼 알파벳을 포함하면 자동으로 조(X)가 추출됩니다.</div>
          <div class="flex justify-end gap-2">
            <button @click="cancelPending" class="px-3 py-1.5 rounded bg-gray-100 text-sm">취소</button>
            <button @click="savePending" class="px-3 py-1.5 rounded bg-primary text-white text-sm font-semibold">저장</button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { loadVWorld } from '@/utils/vworld'
import {
  listTerritories, createTerritory, updateTerritory, deleteTerritory,
  importTerritoryGeoJSON, territoryBoxSeries, setTerritoryBoxes,
  territoryCyclesInside, territoryNearbyManpower,
} from '@/api/territory'

const mapEl = ref(null)
const mapError = ref('')
let vmap = null
let ol = null
let territoryLayer = null
let manpowerLayer = null
let drawInteraction = null
let modifyInteraction = null

const territories = ref([])
const selected = ref(null)
const search = ref('')
const boxSeries = ref([])
const cyclesSummary = ref(null)
const cyclesList = ref([])
const nearbyList = ref([])
const drawing = ref(false)
const pendingPolygon = ref(null)  // ol.Feature
const pendingCode = ref('')
const boxEdit = ref(null)

const filteredTerritories = computed(() => {
  const q = search.value.trim()
  if (!q) return territories.value
  return territories.value.filter(t => (t.code || '').includes(q) || (t.group_letter || '').includes(q))
})
const maxBox = computed(() => Math.max(1, ...boxSeries.value.map(b => b.box_count || 0)))

function fmtSec(s) {
  if (!s) return '00:00'
  const m = Math.floor(s / 60), r = s % 60
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
}

/* ------------------ 지도 ------------------ */
async function initMap() {
  try {
    const { vw, ol: _ol } = await loadVWorld()
    ol = _ol
    const opts = {
      basemapType: vw.ol3.BasemapType.GRAPHIC,
      controlDensity: vw.ol3.DensityType.EMPTY,
      interactionDensity: vw.ol3.DensityType.BASIC,
      controlsAutoArrange: true,
      homePosition: vw.ol3.CameraPosition,
      initPosition: vw.ol3.CameraPosition,
    }
    vmap = new vw.ol3.Map('vw-territory-map', opts)
    vmap.getView().setCenter(ol.proj.fromLonLat([126.9784, 37.5665]))
    vmap.getView().setZoom(11)

    territoryLayer = new ol.layer.Vector({ source: new ol.source.Vector(), zIndex: 5 })
    manpowerLayer = new ol.layer.Vector({ source: new ol.source.Vector(), zIndex: 8 })
    vmap.addLayer(territoryLayer)
    vmap.addLayer(manpowerLayer)

    vmap.on('click', (evt) => {
      if (drawing.value) return
      let hit = null
      vmap.forEachFeatureAtPixel(evt.pixel, (f) => {
        if (f.get('territoryId')) { hit = f; return true }
      })
      if (hit) {
        const t = territories.value.find(x => x.id === hit.get('territoryId'))
        if (t) selectTerritory(t)
      }
    })
  } catch (e) {
    mapError.value = e.message
  }
}

function renderTerritories() {
  if (!territoryLayer) return
  const src = territoryLayer.getSource()
  src.clear()
  for (const t of territories.value) {
    if (!t.geometry || !t.geometry.type) continue
    const feat = _featureFromGeometry(t.geometry, t)
    src.addFeatures(feat)
  }
}

function _featureFromGeometry(geom, t) {
  const feats = []
  const styleFn = (sel) => new ol.style.Style({
    stroke: new ol.style.Stroke({ color: sel ? '#111827' : '#374151', width: sel ? 3 : 1.5 }),
    fill: new ol.style.Fill({ color: hexToRgba(t.color || '#2563EB', sel ? 0.5 : 0.25) }),
  })

  if (geom.type === 'Polygon') {
    const coords = geom.coordinates.map(ring => ring.map(c => ol.proj.fromLonLat(c)))
    const f = new ol.Feature({ geometry: new ol.geom.Polygon(coords) })
    f.set('territoryId', t.id)
    f.setStyle(styleFn(selected.value && selected.value.id === t.id))
    feats.push(f)
  } else if (geom.type === 'MultiPolygon') {
    const coords = geom.coordinates.map(p => p.map(ring => ring.map(c => ol.proj.fromLonLat(c))))
    const f = new ol.Feature({ geometry: new ol.geom.MultiPolygon(coords) })
    f.set('territoryId', t.id)
    f.setStyle(styleFn(selected.value && selected.value.id === t.id))
    feats.push(f)
  }
  return feats
}

function hexToRgba(hex, a) {
  if (!hex || hex[0] !== '#' || hex.length !== 7) return `rgba(37,99,235,${a})`
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${a})`
}

function fitAll() {
  if (!vmap || !territoryLayer) return
  const ext = territoryLayer.getSource().getExtent()
  if (ext && isFinite(ext[0])) {
    vmap.updateSize()
    requestAnimationFrame(() => vmap.getView().fit(ext, { padding: [40, 40, 40, 40], maxZoom: 17 }))
  }
}

/* ------------------ 권역 CRUD ------------------ */
async function loadTerritories() {
  const r = await listTerritories()
  territories.value = r.data.results || r.data || []
  renderTerritories()
  if (territories.value.length) fitAll()
}

async function selectTerritory(t) {
  selected.value = t
  nearbyList.value = []
  boxSeries.value = []
  cyclesSummary.value = null
  renderTerritories()
  // zoom to selected
  if (t.centroid_lat && t.centroid_lon) {
    vmap.getView().setCenter(ol.proj.fromLonLat([t.centroid_lon, t.centroid_lat]))
  }
  try {
    const [bs, ci] = await Promise.all([
      territoryBoxSeries(t.id),
      territoryCyclesInside(t.id),
    ])
    boxSeries.value = bs.data || []
    cyclesSummary.value = ci.data.summary || null
    cyclesList.value = ci.data.cycles || []
  } catch (e) { /* ignore */ }
}

async function removeTerritory(t) {
  if (!confirm(`${t.code} 삭제할까요?`)) return
  await deleteTerritory(t.id)
  if (selected.value?.id === t.id) selected.value = null
  await loadTerritories()
}

async function changeColor(e) {
  if (!selected.value) return
  const color = e.target.value
  await updateTerritory(selected.value.id, { color })
  selected.value.color = color
  const i = territories.value.findIndex(x => x.id === selected.value.id)
  if (i >= 0) territories.value[i].color = color
  renderTerritories()
}

/* ------------------ GeoJSON 업로드 ------------------ */
async function onGeojsonUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''
  try {
    const r = await importTerritoryGeoJSON(file)
    alert(`업로드 완료 — 생성 ${r.data.created}, 갱신 ${r.data.updated}`)
    await loadTerritories()
  } catch (err) {
    alert('업로드 실패: ' + (err.response?.data?.detail || err.message))
  }
}

/* ------------------ 직접 그리기 ------------------ */
function toggleDraw() {
  if (drawing.value) {
    if (drawInteraction) vmap.removeInteraction(drawInteraction)
    drawInteraction = null
    drawing.value = false
    return
  }
  const src = territoryLayer.getSource()
  drawInteraction = new ol.interaction.Draw({ source: src, type: 'Polygon' })
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

async function savePending() {
  if (!pendingPolygon.value) return
  const code = pendingCode.value.trim()
  if (!code) { alert('권역 이름을 입력해주세요'); return }
  // OL Polygon → GeoJSON (WGS84)
  const geom = pendingPolygon.value.getGeometry()
  const coords = geom.getCoordinates().map(ring => ring.map(c => ol.proj.toLonLat(c)))
  try {
    await createTerritory({
      code,
      geometry: { type: 'Polygon', coordinates: coords },
    })
    pendingPolygon.value = null
    pendingCode.value = ''
    await loadTerritories()
  } catch (e) {
    alert('저장 실패: ' + (e.response?.data?.detail || JSON.stringify(e.response?.data || e.message)))
  }
}

function cancelPending() {
  if (pendingPolygon.value) {
    territoryLayer.getSource().removeFeature(pendingPolygon.value)
  }
  pendingPolygon.value = null
  pendingCode.value = ''
}

/* ------------------ 박스수 수동 입력 ------------------ */
function openBoxEditor() {
  boxEdit.value = { date: new Date().toISOString().slice(0, 10), box_count: 0 }
}
async function saveBoxEdit() {
  if (!selected.value || !boxEdit.value) return
  await setTerritoryBoxes(selected.value.id, boxEdit.value)
  boxEdit.value = null
  const r = await territoryBoxSeries(selected.value.id)
  boxSeries.value = r.data || []
}

/* ------------------ 근처 인력 ------------------ */
async function loadNearbyManpower() {
  if (!selected.value) return
  try {
    const r = await territoryNearbyManpower(selected.value.id, 3000)
    nearbyList.value = r.data || []
    // 지도에도 점 표시
    const src = manpowerLayer.getSource()
    src.clear()
    for (const m of nearbyList.value) {
      if (m.lat == null || m.lon == null) continue
      const f = new ol.Feature({ geometry: new ol.geom.Point(ol.proj.fromLonLat([m.lon, m.lat])) })
      f.setStyle(new ol.style.Style({
        image: new ol.style.Circle({
          radius: 6,
          fill: new ol.style.Fill({ color: '#2980B9' }),
          stroke: new ol.style.Stroke({ color: '#FFFFFF', width: 2 }),
        }),
      }))
      src.addFeature(f)
    }
  } catch (e) {
    alert('근처 인력 조회 실패: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(async () => {
  await nextTick()
  await initMap()
  await loadTerritories()
})
</script>
