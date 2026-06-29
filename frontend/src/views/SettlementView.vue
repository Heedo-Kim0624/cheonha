<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <div class="mb-5 flex items-center justify-between">
          <h3 class="text-lg font-bold text-text">
            {{ isOneShipper ? '오네 정산' : `${selectedDate || '날짜 선택'} 정산 목록` }}
          </h3>
          <div v-if="!isOneShipper" class="flex gap-2">
            <button
              @click="openOtherCostModal"
              class="rounded-lg bg-rose-500 px-4 py-2 font-medium text-white hover:opacity-90"
            >
              수정내역 추가
            </button>
            <RouterLink
              to="/dispatch"
              class="rounded-lg bg-primary px-4 py-2 font-medium text-white hover:opacity-90"
            >
              배차 업로드로 정산 생성
            </RouterLink>
          </div>
        </div>

        <div
          v-if="!isOneShipper || showInlineShipperSelector"
          class="mb-5 grid gap-3"
          :class="filterGridClass"
        >
          <TeamFilter v-if="!isOneShipper" v-model="selectedTeam" />
          <label v-if="showInlineShipperSelector" class="block">
            <span class="mb-1 block text-sm font-semibold text-gray-600">화주사</span>
            <select v-model="selectedShipper" class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2">
              <option v-if="!isMultiShipperCompany" value="">전체</option>
              <option v-for="shipper in shipperOptions" :key="shipper.code" :value="shipper.code">
                {{ shipper.name }}
              </option>
            </select>
          </label>
        </div>

        <OneSettlementPanel v-if="isOneShipper" :company-code="companyAppCode" />

        <template v-else>
        <div class="mb-6 overflow-hidden rounded-xl border border-gray-200">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 bg-gray-50 px-5 py-4">
            <div>
              <h4 class="font-bold text-text">달력</h4>
              <p class="text-sm text-gray-500">날짜를 클릭하면 해당 날짜 정산 목록을 표시합니다.</p>
            </div>
            <input
              v-model="calendarMonth"
              type="month"
              class="rounded-lg border border-gray-300 bg-white px-4 py-2 outline-none focus:border-primary"
            />
          </div>
          <div class="grid grid-cols-7 border-b border-gray-200 bg-white">
            <div v-for="day in weekLabels" :key="day" class="px-3 py-2 text-center text-sm font-bold text-gray-500">
              {{ day }}
            </div>
          </div>
          <div class="grid grid-cols-7 bg-white">
            <button
              v-for="cell in calendarCells"
              :key="cell.key"
              type="button"
              class="min-h-[112px] border-b border-r border-gray-100 p-3 text-left hover:bg-blue-50 disabled:hover:bg-white"
              :class="[
                cell.inMonth ? '' : 'bg-gray-50 text-gray-300',
                selectedDate === cell.date ? 'bg-blue-50 ring-2 ring-inset ring-primary' : '',
              ]"
              :disabled="!cell.inMonth"
              @click="selectDate(cell.date)"
            >
              <div class="flex items-center justify-between">
                <span class="font-bold">{{ cell.day }}</span>
                <span v-if="cell.settlements.length" class="rounded-full bg-primary px-2 py-0.5 text-xs text-white">
                  {{ cell.settlements.length }}건
                </span>
              </div>
              <div v-if="cell.settlements.length" class="mt-3 space-y-1 text-xs">
                <div
                  class="font-semibold"
                  :class="Number(cell.totalProfit || 0) >= 0 ? 'text-green-700' : 'text-red-600'"
                >
                  수익 {{ formatCurrency(cell.totalProfit || 0) }}원
                </div>
                <div class="truncate text-gray-500">{{ cell.teamNames.join(', ') }}</div>
              </div>
            </button>
          </div>
        </div>

        <div v-if="loading" class="py-12 text-center text-gray-400">
          <div class="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
          로딩 중...
        </div>

        <div v-else-if="filteredSettlements.length === 0" class="py-12 text-center text-gray-400">
          <p class="mb-3 text-4xl">&#128203;</p>
          <p class="mb-1 font-medium">정산 내역이 없습니다</p>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="settlement in filteredSettlements"
            :key="settlement.id"
            class="overflow-hidden rounded-xl border border-gray-200 transition-shadow hover:shadow-md"
          >
            <div class="cursor-pointer p-5" @click="toggleDetail(settlement.id)">
              <div class="mb-4 flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="flex h-10 min-w-14 items-center justify-center rounded-lg bg-blue-100">
                    <span class="whitespace-nowrap font-bold text-blue-700">
                      {{ settlement.period_start ? settlement.period_start.substring(5, 10) : '-' }}
                    </span>
                  </div>
                  <div>
                    <p class="font-bold text-text">{{ settlement.period_start }}</p>
                    <p class="text-gray-400">{{ settlement.team_name || '전체' }}</p>
                  </div>
                </div>
                <span class="text-gray-400">{{ expandedId === settlement.id ? '▲' : '▼' }}</span>
              </div>

              <div class="grid grid-cols-4 gap-4">
                <div class="rounded-lg bg-blue-50 p-3">
                  <p class="text-blue-500">정규 수신합계</p>
                  <p class="font-bold text-blue-800">{{ formatCurrency(Number(settlement.regular_total_receive ?? settlement.total_receive)) }}원</p>
                  <p v-if="Number(settlement.yongcha_total_receive || 0)" class="mt-1 text-xs font-semibold text-red-600">
                    용차 수신 {{ formatCurrency(Number(settlement.yongcha_total_receive || 0)) }}원
                  </p>
                </div>
                <div class="rounded-lg bg-orange-50 p-3">
                  <p class="text-orange-500">정규 지급합계</p>
                  <p class="font-bold text-orange-800">{{ formatCurrency(Number(settlement.regular_total_pay ?? settlement.total_pay)) }}원</p>
                  <p v-if="Number(settlement.yongcha_total_pay || 0)" class="mt-1 text-xs font-semibold text-fuchsia-700">
                    용차 지급 {{ formatCurrency(Number(settlement.yongcha_total_pay || 0)) }}원
                  </p>
                </div>
                <div class="rounded-lg bg-amber-50 p-3">
                  <p class="text-amber-500">조정비용(특근 등)</p>
                  <p class="font-bold text-amber-800">{{ formatCurrency(Number(settlement.regular_total_overtime ?? settlement.total_overtime)) }}원</p>
                </div>
                <div
                  class="rounded-lg p-3"
                  :class="Number(settlement.total_profit) >= 0 ? 'bg-green-50' : 'bg-red-50'"
                >
                  <p :class="Number(settlement.total_profit) >= 0 ? 'text-green-500' : 'text-red-500'">총 수익</p>
                  <p
                    class="font-bold"
                    :class="Number(settlement.total_profit) >= 0 ? 'text-green-800' : 'text-red-800'"
                  >
                    {{ formatCurrency(Number(settlement.total_profit)) }}원
                  </p>
                  <p v-if="Number(settlement.yongcha_total_profit || 0)" class="mt-1 text-xs font-semibold text-gray-600">
                    용차 수익 {{ formatCurrency(Number(settlement.yongcha_total_profit || 0)) }}원
                  </p>
                </div>
              </div>
            </div>

            <div v-if="expandedId === settlement.id" class="border-t border-gray-200 bg-gray-50">
              <div v-if="loadingDetails" class="py-6 text-center text-gray-400">상세 로딩 중...</div>
              <div v-else-if="uploadGroups.length === 0" class="py-6 text-center text-gray-400">상세 내역이 없습니다.</div>
              <div v-else class="space-y-3 p-5">
                <div
                  v-for="round in roundGroups"
                  :key="round.key"
                  class="overflow-hidden rounded-xl border border-gray-200 bg-white"
                >
                  <button
                    type="button"
                    class="flex w-full items-center justify-between border-b border-gray-200 bg-gray-50 px-5 py-3 text-left"
                    @click="toggleRound(round.key)"
                  >
                    <span class="font-bold text-text">{{ round.label }}</span>
                    <span class="text-sm text-gray-500">{{ round.groups.length }}개 파일 {{ isRoundExpanded(round.key) ? '▲' : '▼' }}</span>
                  </button>

                  <div v-if="isRoundExpanded(round.key)" class="space-y-4 p-4">
                    <div v-if="round.groups.length === 0" class="rounded-lg border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-center text-gray-400">
                      상세 내역이 없습니다.
                    </div>
                    <div
                      v-for="ug in round.groups"
                      :key="ug.uploadId"
                      class="overflow-hidden rounded-xl border border-gray-200 bg-white"
                    >
                      <div class="flex items-center justify-between border-b border-blue-100 bg-blue-50 px-5 py-3">
                        <div class="flex items-center gap-3">
                          <span class="font-bold text-blue-700">{{ ug.filename || '배차파일' }}</span>
                          <span class="text-blue-500">{{ formatTime(ug.uploadTime) }}</span>
                        </div>
                        <div class="flex items-center gap-4 text-blue-600">
                          <span>정규 수신 {{ formatCurrency(ug.regularTotalReceive) }}원</span>
                          <span>지급 {{ formatCurrency(ug.regularTotalPay) }}원</span>
                          <span class="font-bold">수익 {{ formatCurrency(ug.regularTotalProfit) }}원</span>
                          <span v-if="ug.yongchaTotalReceive" class="font-bold text-red-600">용차 수신 {{ formatCurrency(ug.yongchaTotalReceive) }}원</span>
                          <span v-if="ug.yongchaTotalPay" class="font-bold text-fuchsia-700">용차 지급 {{ formatCurrency(ug.yongchaTotalPay) }}원</span>
                          <span v-if="ug.yongchaTotalProfit" class="font-bold text-gray-700">용차 수익 {{ formatCurrency(ug.yongchaTotalProfit) }}원</span>
                        </div>
                      </div>

                      <table class="w-full">
                        <thead class="border-b border-gray-200 bg-gray-50">
                          <tr>
                            <th class="px-4 py-2 text-left font-semibold text-gray-600">배송원</th>
                            <th class="px-4 py-2 text-left font-semibold text-gray-600">권역</th>
                            <th class="px-4 py-2 text-right font-semibold text-gray-600">박스</th>
                            <th class="px-4 py-2 text-right font-semibold text-gray-600">가구</th>
                            <th class="px-4 py-2 text-right font-semibold text-blue-600">수신</th>
                            <th class="px-4 py-2 text-right font-semibold text-orange-600">지급</th>
                            <th class="px-4 py-2 text-right font-semibold text-amber-600">조정비용</th>
                            <th class="px-4 py-2 text-right font-semibold text-green-600">수익</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr class="bg-green-50">
                            <td colspan="8" class="px-4 py-2 font-bold text-green-700">정규 배송원</td>
                          </tr>
                          <tr
                            v-for="crew in ug.regularCrewList"
                            :key="`regular-${crew.name}`"
                            class="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                            @click.stop="openCrewPopup(crew, ug)"
                          >
                            <td class="px-4 py-3 font-bold text-primary-dark underline">{{ crew.name }}</td>
                            <td class="px-4 py-3">
                              <div class="flex flex-wrap gap-1">
                                <span
                                  v-for="r in crew.regions"
                                  :key="r"
                                  class="rounded bg-primary-light px-2 py-0.5 font-medium text-primary-dark"
                                >
                                  {{ r }}
                                </span>
                              </div>
                            </td>
                            <td class="px-4 py-3 text-right">
                              <input
                                type="number"
                                :value="crew.totalBoxes"
                                min="0"
                                class="w-20 rounded border border-blue-300 bg-blue-50 px-2 py-1 text-right font-bold outline-none focus:border-blue-400"
                                @click.stop
                                @change="updateBoxes(crew, $event)"
                              />
                            </td>
                            <td class="px-4 py-3 text-right font-bold">{{ crew.totalHouseholds }}</td>
                            <td class="px-4 py-3 text-right font-medium text-blue-700">{{ formatCurrency(crew.totalReceive) }}원</td>
                            <td class="px-4 py-3 text-right font-medium text-orange-700">{{ formatCurrency(crew.totalPay) }}원</td>
                            <td class="px-4 py-3 text-right text-amber-700">
                              <input
                                type="number"
                                :value="crew.totalOvertime"
                                class="w-24 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-right outline-none focus:border-amber-400"
                                @click.stop
                                @change="updateAdjustment(crew, $event)"
                              />
                            </td>
                            <td
                              class="px-4 py-3 text-right font-bold"
                              :class="crew.totalProfit >= 0 ? 'text-green-600' : 'text-red-600'"
                            >
                              {{ formatCurrency(crew.totalProfit) }}원
                            </td>
                          </tr>
                          <tr v-if="ug.regularCrewList.length === 0">
                            <td colspan="8" class="px-4 py-6 text-center text-gray-400">정규 배송원 정산이 없습니다.</td>
                          </tr>

                          <tr class="bg-red-50">
                            <td colspan="8" class="px-4 py-2 font-bold text-red-600">용차 배송원 (지급은 가구 기준)</td>
                          </tr>
                          <tr
                            v-for="crew in ug.yongchaCrewList"
                            :key="`yongcha-${crew.name}`"
                            class="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                            @click.stop="openCrewPopup(crew, ug)"
                          >
                            <td class="px-4 py-3 font-bold text-red-600 underline">{{ crew.name }}</td>
                            <td class="px-4 py-3">
                              <div class="flex flex-wrap gap-1">
                                <span
                                  v-for="r in crew.regions"
                                  :key="r"
                                  class="rounded bg-red-50 px-2 py-0.5 font-medium text-red-600"
                                >
                                  {{ r }}
                                </span>
                              </div>
                            </td>
                            <td class="px-4 py-3 text-right font-bold">{{ crew.totalBoxes }}</td>
                            <td class="px-4 py-3 text-right font-bold">{{ crew.totalHouseholds }}</td>
                            <td class="px-4 py-3 text-right font-medium text-blue-700">{{ formatCurrency(crew.totalReceive) }}원</td>
                            <td class="px-4 py-3 text-right font-medium text-orange-700">{{ formatCurrency(crew.totalPay) }}원</td>
                            <td class="px-4 py-3 text-right text-amber-700">
                              <input
                                type="number"
                                :value="crew.totalOvertime"
                                class="w-24 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-right outline-none focus:border-amber-400"
                                @click.stop
                                @change="updateAdjustment(crew, $event)"
                              />
                            </td>
                            <td
                              class="px-4 py-3 text-right font-bold"
                              :class="crew.totalProfit >= 0 ? 'text-green-600' : 'text-red-600'"
                            >
                              {{ formatCurrency(crew.totalProfit) }}원
                            </td>
                          </tr>
                          <tr v-if="ug.yongchaCrewList.length === 0">
                            <td colspan="8" class="px-4 py-6 text-center text-gray-400">용차 배송원 정산이 없습니다.</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        </template>
      </div>

      <div v-if="crewPopup" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50" @click.self="crewPopup = null">
        <div class="flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl bg-white">
          <div class="border-b border-gray-200 px-6 py-4">
            <div class="mb-3 flex items-center justify-between">
              <h3 class="text-xl font-bold text-text">{{ crewPopup.name }}</h3>
              <button @click="crewPopup = null" class="text-2xl text-gray-400 hover:text-gray-600">&times;</button>
            </div>
            <div class="flex items-center gap-3">
              <input
                v-model="popupMonth"
                type="month"
                class="rounded-lg border border-gray-300 bg-white px-4 py-2 outline-none focus:border-primary"
              />
              <p class="ml-auto text-lg font-bold text-orange-600">
                총 지급액: {{ formatCurrency(popupFilteredTotals.pay + popupFilteredTotals.overtime) }}원
              </p>
            </div>
          </div>
          <div class="flex-1 overflow-y-auto p-6">
            <div v-if="crewPopup.loading" class="py-8 text-center text-gray-400">로딩 중...</div>
            <table v-else-if="popupFilteredRows.length > 0" class="w-full">
              <thead class="sticky top-0 border-b border-gray-200 bg-gray-50">
                <tr>
                  <th class="px-4 py-2 text-left font-semibold text-gray-600">날짜</th>
                  <th class="px-4 py-2 text-left font-semibold text-gray-600">권역</th>
                  <th class="px-4 py-2 text-right font-semibold text-gray-600">박스</th>
                  <th class="px-4 py-2 text-right font-semibold text-gray-600">가구</th>
                  <th class="px-4 py-2 text-right font-semibold text-orange-600">지급</th>
                  <th class="px-4 py-2 text-right font-semibold text-amber-600">조정비용(특근 등)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in popupFilteredRows" :key="idx" class="border-b border-gray-100">
                  <td class="px-4 py-3">{{ row.date }}</td>
                  <td class="px-4 py-3">{{ row.regions }}</td>
                  <td class="px-4 py-3 text-right font-bold">{{ row.boxes }}</td>
                  <td class="px-4 py-3 text-right font-bold">{{ row.households }}</td>
                  <td class="px-4 py-3 text-right font-medium text-orange-700">{{ formatCurrency(row.pay) }}원</td>
                  <td class="px-4 py-3 text-right text-amber-700">{{ row.overtime !== 0 ? formatCurrency(row.overtime) + '원' : '-' }}</td>
                </tr>
              </tbody>
              <tfoot class="sticky bottom-0 bg-gray-50 font-bold">
                <tr>
                  <td colspan="2" class="px-4 py-3">합계 ({{ popupFilteredRows.length }}건)</td>
                  <td class="px-4 py-3 text-right">{{ popupFilteredTotals.boxes }}</td>
                  <td class="px-4 py-3 text-right">{{ popupFilteredTotals.households }}</td>
                  <td class="px-4 py-3 text-right text-orange-700">{{ formatCurrency(popupFilteredTotals.pay) }}원</td>
                  <td class="px-4 py-3 text-right text-amber-700">{{ popupFilteredTotals.overtime !== 0 ? formatCurrency(popupFilteredTotals.overtime) + '원' : '-' }}</td>
                </tr>
              </tfoot>
            </table>
            <div v-else class="py-8 text-center text-gray-400">해당 월의 데이터가 없습니다.</div>
          </div>
        </div>
      </div>

      <div
        v-if="otherCostModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
        @click.self="closeOtherCostModal"
      >
        <div class="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-xl bg-white">
          <div class="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <h3 class="text-xl font-bold text-text">수정내역 추가</h3>
            <button @click="closeOtherCostModal" class="text-2xl text-gray-400 hover:text-gray-600">×</button>
          </div>
          <div class="flex-1 space-y-4 overflow-y-auto p-6">
            <div>
              <label class="mb-2 block text-gray-500">날짜</label>
              <select
                v-model="ocForm.date"
                @change="ocForm.team = ''; ocForm.crewName = ''; ocForm.crewDetailId = null"
                class="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-primary"
              >
                <option value="">날짜 선택</option>
                <option v-for="d in ocAvailableDates" :key="d" :value="d">{{ d }}</option>
              </select>
            </div>
            <div v-if="ocForm.date">
              <label class="mb-2 block text-gray-500">조</label>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="t in ocAvailableTeams"
                  :key="t"
                  type="button"
                  @click="selectOcTeam(t)"
                  class="rounded-lg px-4 py-2 font-medium"
                  :class="ocForm.team === t ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
                >
                  {{ t }}
                </button>
              </div>
            </div>
            <div v-if="ocForm.team">
              <label class="mb-2 block text-gray-500">배송원 이름 검색</label>
              <input
                :value="ocForm.crewName"
                @input="onCrewNameInput"
                type="text"
                placeholder="이름 일부 입력"
                class="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-primary"
              />
              <div
                v-if="ocForm.crewName && ocFilteredCrews.length > 0"
                class="mt-2 max-h-48 overflow-y-auto rounded-lg border border-gray-200"
              >
                <div
                  v-for="c in ocFilteredCrews"
                  :key="c.detailId"
                  @click="selectOcCrew(c)"
                  class="cursor-pointer border-b border-gray-100 px-4 py-2 hover:bg-gray-50"
                  :class="ocForm.crewDetailId === c.detailId ? 'bg-primary-light' : ''"
                >
                  <span class="font-medium">{{ c.name }}</span>
                  <span
                    class="ml-2 rounded px-2 py-0.5 text-xs font-bold"
                    :class="c.isYongcha ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700'"
                  >
                    {{ c.isYongcha ? '용차' : '정규' }}
                  </span>
                  <span class="ml-2 text-gray-400">{{ c.boxes }}박스</span>
                </div>
              </div>
              <p v-else-if="ocForm.crewName && ocFilteredCrews.length === 0" class="mt-2 text-gray-400">
                일치하는 배송원이 없습니다.
              </p>
            </div>
            <div v-if="ocForm.crewDetailId" class="grid grid-cols-2 gap-4">
              <div>
                <label class="mb-2 block font-medium text-blue-600">박스수</label>
                <input
                  v-model.number="ocForm.boxes"
                  type="number"
                  min="0"
                  placeholder="0"
                  class="w-full rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 text-right outline-none focus:border-blue-400"
                />
              </div>
              <div>
                <label class="mb-2 block font-medium text-amber-600">조정비용</label>
                <input
                  v-model.number="ocForm.adjustment"
                  type="number"
                  placeholder="0"
                  class="w-full rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-right outline-none focus:border-amber-400"
                />
              </div>
            </div>
          </div>
          <div class="flex justify-end gap-3 border-t border-gray-200 px-6 py-4">
            <button
              @click="closeOtherCostModal"
              class="rounded-lg border border-gray-300 px-5 py-3 hover:bg-gray-50"
            >
              취소
            </button>
            <button
              @click="saveOtherCost"
              :disabled="!ocForm.crewDetailId"
              class="rounded-lg bg-rose-500 px-5 py-3 font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              저장
            </button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { formatCurrency } from '@/utils/format'
import AppLayout from '@/components/common/AppLayout.vue'
import {
  fetchSettlementCrewHistory,
  fetchSettlementDetailGroups,
  fetchSettlementWebOverview,
  getSettlementDetails,
} from '@/api/settlement'
import client from '@/api/client'
import { fetchPublicCompanyApp, fetchShippers } from '@/api/companyAdmin'
import TeamFilter from '@/components/common/TeamFilter.vue'
import OneSettlementPanel from '@/components/oneSettlement/OneSettlementPanel.vue'
import { getCompanyAppFromRoute } from '@/utils/companyApp'
import {
  ensureSelectedShipperCode,
  setSelectedShipperCode,
  SHIPPER_CONTEXT_CHANGED_EVENT,
} from '@/utils/shipperContext'

const route = useRoute()
const companyAppCode = computed(() => getCompanyAppFromRoute(route).code)
const overview = ref({
  settlements: [],
  settlements_by_date: {},
  calendar_cells: [],
  initial_selected_date: null,
})
const loading = ref(true)
const expandedId = ref(null)
const uploadGroups = ref([])
const expandedRoundKeys = ref(new Set())
const loadingDetails = ref(false)
const selectedTeam = ref('')
const selectedShipper = ref('')
const enabledShipperCodes = ref(['kurly'])
const shipperCatalog = ref([{ code: 'kurly', name: '컬리', status: 'ACTIVE' }])
const calendarMonth = ref(new Date().toISOString().substring(0, 7))
const selectedDate = ref('')
const weekLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const crewPopup = ref(null)
const popupMonth = ref(new Date().toISOString().substring(0, 7))
const otherCostModal = ref(false)
const ocForm = reactive({ date: '', team: '', crewName: '', crewDetailId: null, boxes: 0, adjustment: 0 })
const ocSettlementDetails = ref([])

const isOneShipper = computed(() => selectedShipper.value === 'one')
const settlements = computed(() => overview.value.settlements || [])
const settlementsByDate = computed(() => overview.value.settlements_by_date || {})
const normalizeList = (payload) => payload?.results || payload || []
const shipperOptions = computed(() => {
  const enabled = new Set(enabledShipperCodes.value.length ? enabledShipperCodes.value : ['kurly'])
  const rows = normalizeList(shipperCatalog.value)
    .filter((item) => enabled.has(item.code) && item.status !== 'INACTIVE')
  if (rows.length > 0) return rows
  return [{ code: 'kurly', name: '컬리', status: 'ACTIVE' }]
})
const calendarCells = computed(() => {
  return (overview.value.calendar_cells || []).map((cell) => ({
    ...cell,
    settlements: Array.from({ length: Number(cell.settlementCount || 0) }),
  }))
})
const filteredSettlements = computed(() => {
  if (!selectedDate.value) return []
  return settlementsByDate.value[selectedDate.value] || []
})
const isMultiShipperCompany = computed(() => shipperOptions.value.length > 1)
const showInlineShipperSelector = computed(() => false)
const filterGridClass = computed(() => {
  if (showInlineShipperSelector.value && !isOneShipper.value) return 'md:grid-cols-[1fr,180px]'
  return 'md:grid-cols-[1fr]'
})
const popupFilteredRows = computed(() => crewPopup.value?.rows || [])
const popupFilteredTotals = computed(() => crewPopup.value?.totals || { boxes: 0, households: 0, pay: 0, overtime: 0 })
const roundGroups = computed(() => {
  const grouped = new Map()

  for (const group of uploadGroups.value) {
    const roundNo = Number(group.roundNo || group.round_no || 0)
    const key = [1, 2, 3].includes(roundNo) ? String(roundNo) : 'other'
    if (!grouped.has(key)) {
      grouped.set(key, {
        key,
        label: key === 'other' ? '기타 회차' : `${roundNo}회차`,
        groups: [],
      })
    }
    grouped.get(key).groups.push(group)
  }

  const orderedRounds = ['1', '2', '3'].map((key) => (
    grouped.get(key) || { key, label: `${key}회차`, groups: [] }
  ))
  if (grouped.has('other')) orderedRounds.push(grouped.get('other'))
  return orderedRounds
})

const onCrewNameInput = (event) => {
  ocForm.crewName = event.target.value
  ocForm.crewDetailId = null
}

const loadShipperOptions = async () => {
  try {
    const companyApp = getCompanyAppFromRoute(route)
    const [companyResp, shipperResp] = await Promise.all([
      fetchPublicCompanyApp(companyApp.code),
      fetchShippers(),
    ])
    enabledShipperCodes.value = companyResp.data?.enabled_shippers?.length
      ? companyResp.data.enabled_shippers
      : ['kurly']
    shipperCatalog.value = normalizeList(shipperResp.data)
    selectedShipper.value = ensureSelectedShipperCode(
      companyApp.code,
      enabledShipperCodes.value,
      selectedShipper.value || enabledShipperCodes.value[0] || 'kurly',
    )
  } catch {
    enabledShipperCodes.value = ['kurly']
    shipperCatalog.value = [{ code: 'kurly', name: '컬리', status: 'ACTIVE' }]
    if (selectedShipper.value && selectedShipper.value !== 'kurly') {
      selectedShipper.value = ''
    }
  }
}

const handleShipperContextChanged = (event) => {
  const detail = event?.detail || {}
  if (detail.companyCode !== companyAppCode.value) return
  if (!detail.shipperCode || selectedShipper.value === detail.shipperCode) return
  selectedShipper.value = detail.shipperCode
}

const ocAvailableDates = computed(() => {
  const dates = new Set()
  for (const settlement of settlements.value) {
    if (settlement.period_start) dates.add(settlement.period_start)
  }
  return Array.from(dates).sort().reverse()
})

const ocAvailableTeams = computed(() => {
  if (!ocForm.date) return []
  const teams = new Set()
  for (const settlement of settlements.value) {
    if (settlement.period_start === ocForm.date && settlement.team_name) {
      teams.add(settlement.team_name)
    }
  }
  return Array.from(teams)
})

const ocFilteredCrews = computed(() => {
  const query = (ocForm.crewName || '').toLowerCase().trim()
  if (!query) return []

  const seen = new Map()
  for (const detail of ocSettlementDetails.value) {
    const name = detail.crew_member_name || detail.crew_member_code
    if (!name || !name.toLowerCase().includes(query)) continue

    const isYongcha = Boolean(detail.is_yongcha)
    const key = `${detail.crew_member || name}-${isYongcha ? 'yongcha' : 'regular'}`
    if (!seen.has(key)) {
      seen.set(key, {
        name,
        isYongcha,
        detailId: detail.id,
        boxes: 0,
        firstBoxes: detail.boxes || 0,
        adjustment: Number(detail.overtime_cost || 0),
      })
    }
    seen.get(key).boxes += detail.boxes || 0
  }

  return Array.from(seen.values())
})

const selectOcCrew = (crew) => {
  ocForm.crewName = crew.name
  ocForm.crewDetailId = crew.detailId
  ocForm.boxes = crew.firstBoxes || 0
  ocForm.adjustment = crew.adjustment || 0
}

const selectOcTeam = async (teamName) => {
  ocForm.team = teamName
  ocForm.crewName = ''
  ocForm.crewDetailId = null
  ocForm.boxes = 0
  ocForm.adjustment = 0
  await loadOcDetails()
}

const openOtherCostModal = () => {
  ocForm.date = ''
  ocForm.team = ''
  ocForm.crewName = ''
  ocForm.crewDetailId = null
  ocForm.boxes = 0
  ocForm.adjustment = 0
  ocSettlementDetails.value = []
  otherCostModal.value = true
}

const closeOtherCostModal = () => {
  otherCostModal.value = false
}

const formatTime = (value) => {
  if (!value) return ''
  const parsed = new Date(value)
  return `${parsed.getHours()}시 ${String(parsed.getMinutes()).padStart(2, '0')}분`
}

const loadOcDetails = async () => {
  if (!ocForm.date || !ocForm.team) return
  const target = settlements.value.find(
    (settlement) => settlement.period_start === ocForm.date && settlement.team_name === ocForm.team,
  )
  if (!target) {
    ocSettlementDetails.value = []
    return
  }

  try {
    const response = await getSettlementDetails(target.id)
    ocSettlementDetails.value = response.data.results || response.data || []
  } catch {
    ocSettlementDetails.value = []
  }
}

const saveOtherCost = async () => {
  if (!ocForm.crewDetailId) return

  try {
    await client.patch(`/settlement/details/${ocForm.crewDetailId}`, {
      boxes: Number(ocForm.boxes || 0),
      overtime_cost: Number(ocForm.adjustment || 0),
    })

    const target = settlements.value.find(
      (settlement) => settlement.period_start === ocForm.date && settlement.team_name === ocForm.team,
    )
    if (target) {
      await client.post(`/settlement/settlements/${target.id}/recalc/`)
    }

    closeOtherCostModal()
    await loadSettlements()
    await reloadDetails()
  } catch (error) {
    alert(`저장 실패: ${error?.response?.data?.detail || error?.message || '알 수 없는 오류'}`)
  }
}

const loadCrewPopup = async (crew) => {
  const params = {
    month: popupMonth.value || undefined,
    crew_member_id: crew.crewMemberId || undefined,
    crew_name: crew.crewMemberId ? undefined : crew.name,
  }
  const response = await fetchSettlementCrewHistory(params)
  const payload = response.data || {}
  crewPopup.value = {
    ...crew,
    rows: payload.rows || [],
    totals: payload.totals || { boxes: 0, households: 0, pay: 0, overtime: 0 },
    loading: false,
  }
}

const openCrewPopup = async (crew) => {
  crewPopup.value = {
    ...crew,
    rows: [],
    totals: { boxes: 0, households: 0, pay: 0, overtime: 0 },
    loading: true,
  }
  try {
    await loadCrewPopup(crew)
  } catch {
    crewPopup.value = {
      ...crew,
      rows: [],
      totals: { boxes: 0, households: 0, pay: 0, overtime: 0 },
      loading: false,
    }
  }
}

const refreshOpenCrewPopup = async () => {
  if (!crewPopup.value) return
  const crew = { ...crewPopup.value }
  crewPopup.value = {
    ...crew,
    loading: true,
  }
  try {
    await loadCrewPopup(crew)
  } catch {
    crewPopup.value = {
      ...crew,
      loading: false,
    }
  }
}

const selectDate = async (date) => {
  selectedDate.value = date
  uploadGroups.value = []
  expandedId.value = null
  expandedRoundKeys.value = new Set()
}

const toggleDetail = async (id, forceOpen = false) => {
  if (!forceOpen && expandedId.value === id) {
    expandedId.value = null
    uploadGroups.value = []
    expandedRoundKeys.value = new Set()
    return
  }

  expandedId.value = id
  expandedRoundKeys.value = new Set()
  loadingDetails.value = true
  try {
    const response = await fetchSettlementDetailGroups(id)
    uploadGroups.value = response.data.groups || []
  } catch {
    uploadGroups.value = []
  } finally {
    loadingDetails.value = false
  }
}

const isRoundExpanded = (key) => expandedRoundKeys.value.has(key)

const toggleRound = (key) => {
  const next = new Set(expandedRoundKeys.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  expandedRoundKeys.value = next
}

const updateAdjustment = async (crew, event) => {
  const newCost = Number(event.target.value) || 0
  try {
    for (let index = 0; index < crew.detailIds.length; index += 1) {
      await client.patch(`/settlement/details/${crew.detailIds[index]}`, {
        overtime_cost: index === 0 ? newCost : 0,
      })
    }
    if (expandedId.value) {
      await client.post(`/settlement/settlements/${expandedId.value}/recalc/`)
    }
    await reloadDetails()
  } catch (error) {
    console.error('Failed to update adjustment cost', error)
  }
}

const updateBoxes = async (crew, event) => {
  const newBoxes = Number(event.target.value) || 0
  try {
    if (crew.detailIds.length > 0) {
      await client.patch(`/settlement/details/${crew.detailIds[0]}`, { boxes: newBoxes })
      for (let index = 1; index < crew.detailIds.length; index += 1) {
        await client.patch(`/settlement/details/${crew.detailIds[index]}`, { boxes: 0 })
      }
    }
    if (expandedId.value) {
      await client.post(`/settlement/settlements/${expandedId.value}/recalc/`)
    }
    await reloadDetails()
  } catch (error) {
    console.error('Failed to update boxes', error)
  }
}

const reloadDetails = async () => {
  if (expandedId.value) {
    await toggleDetail(expandedId.value, true)
  }
  await loadSettlements({ preserveExpansion: Boolean(expandedId.value) })
  await refreshOpenCrewPopup()
}

const loadSettlements = async (options = {}) => {
  if (isOneShipper.value) {
    overview.value = {
      settlements: [],
      settlements_by_date: {},
      calendar_cells: [],
      initial_selected_date: null,
    }
    selectedDate.value = ''
    uploadGroups.value = []
    expandedId.value = null
    expandedRoundKeys.value = new Set()
    loading.value = false
    return
  }

  loading.value = true
  try {
    const previousExpandedId = expandedId.value
    const response = await fetchSettlementWebOverview({
      team_name: selectedTeam.value || undefined,
      shipper_code: selectedShipper.value || undefined,
      month: calendarMonth.value || undefined,
    })
    overview.value = response.data || overview.value

    const dateMap = overview.value.settlements_by_date || {}
    const nextDate = (
      selectedDate.value && dateMap[selectedDate.value]
        ? selectedDate.value
        : overview.value.initial_selected_date || Object.keys(dateMap)[0] || ''
    )
    selectedDate.value = nextDate

    const nextSettlements = nextDate ? (dateMap[nextDate] || []) : []
    if (options.preserveExpansion && previousExpandedId && nextSettlements.some((item) => item.id === previousExpandedId)) {
      expandedId.value = previousExpandedId
    } else {
      expandedId.value = null
      uploadGroups.value = []
      expandedRoundKeys.value = new Set()
    }
  } catch {
    overview.value = {
      settlements: [],
      settlements_by_date: {},
      calendar_cells: [],
      initial_selected_date: null,
    }
    uploadGroups.value = []
    expandedId.value = null
    expandedRoundKeys.value = new Set()
  } finally {
    loading.value = false
  }
}

watch([selectedTeam, selectedShipper, calendarMonth], () => {
  void loadSettlements()
})

watch(selectedShipper, (shipper) => {
  if (!shipper) return
  setSelectedShipperCode(companyAppCode.value, shipper)
})

watch(popupMonth, () => {
  void refreshOpenCrewPopup()
})

onMounted(async () => {
  window.addEventListener(SHIPPER_CONTEXT_CHANGED_EVENT, handleShipperContextChanged)
  await loadShipperOptions()
  await loadSettlements()
})

onBeforeUnmount(() => {
  window.removeEventListener(SHIPPER_CONTEXT_CHANGED_EVENT, handleShipperContextChanged)
})
</script>
