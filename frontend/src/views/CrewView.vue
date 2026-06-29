<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold text-text">배송원 관리</h2>
      </div>

      <TeamFilter v-if="authStore.isAdmin && activeTab !== 'yongchaGroups'" v-model="selectedTeamName" />

      <div class="flex gap-2 rounded-lg border border-gray-200 bg-white p-2">
        <button
          class="px-4 py-2 rounded-md font-medium"
          :class="activeTab === 'regular' ? 'bg-primary text-white' : 'text-gray-600 hover:bg-gray-50'"
          @click="activeTab = 'regular'"
        >
          정규 배송원
        </button>
        <button
          class="px-4 py-2 rounded-md font-medium"
          :class="activeTab === 'yongcha' ? 'bg-primary text-white' : 'text-gray-600 hover:bg-gray-50'"
          @click="activeTab = 'yongcha'"
        >
          용차 관리
        </button>
        <button
          class="px-4 py-2 rounded-md font-medium"
          :class="activeTab === 'yongchaGroups' ? 'bg-primary text-white' : 'text-gray-600 hover:bg-gray-50'"
          @click="activeTab = 'yongchaGroups'"
        >
          용차팀 관리
        </button>
      </div>

      <div v-if="activeTab !== 'yongchaGroups'">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="이름, 코드, 전화번호 검색"
          class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none"
        />
        <div v-if="activeTab === 'yongcha'" class="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            class="rounded-lg border px-4 py-2 text-sm font-bold"
            :class="yongchaBulkMode ? 'border-fuchsia-300 bg-fuchsia-50 text-fuchsia-700' : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'"
            @click="toggleYongchaBulkMode"
          >
            {{ yongchaBulkMode ? '용차팀 변경 종료' : '용차팀 변경' }}
          </button>
          <span v-if="yongchaBulkMode" class="text-sm text-gray-500">
            검색이나 페이지 이동 후에도 선택한 배송원은 유지됩니다.
          </span>
        </div>
      </div>

      <div
        v-if="!authStore.isAdmin && !authStore.user?.team"
        class="bg-amber-50 rounded-xl p-8 border border-amber-200 text-center"
      >
        <p class="text-lg font-medium text-amber-700 mb-2">소속 조가 지정되어 있지 않습니다.</p>
        <p class="text-amber-600">관리자에게 조 배정을 요청하세요.</p>
      </div>

      <div
        v-else-if="crewStore.loading && activeTab === 'regular' && regularRows.length === 0"
        class="text-center py-8 text-gray-500"
      >
        불러오는 중...
      </div>

      <div v-else-if="activeTab === 'regular'" class="grid grid-cols-1 gap-4 xl:h-[calc(100vh-260px)]">
        <section class="bg-white rounded-xl border border-gray-200 overflow-hidden xl:flex xl:min-h-0 xl:flex-col">
          <div class="px-5 py-4 border-b border-gray-200 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 class="font-bold text-text">정규 배송원</h3>
              <p class="text-sm text-gray-500">이름을 클릭하면 해당 월 정산 내역을 확인할 수 있습니다.</p>
            </div>
            <input
              v-model="regularMonth"
              type="month"
              class="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 outline-none focus:border-primary"
            />
          </div>
        <div class="min-h-0 overflow-auto xl:flex-1">
          <table class="min-w-[1080px] w-full table-fixed text-sm">
            <colgroup>
              <col class="w-[16%]" />
              <col class="w-[15%]" />
              <col class="w-[9%]" />
              <col class="w-[9%]" />
              <col class="w-[13%]" />
              <col class="w-[13%]" />
              <col class="w-[13%]" />
              <col class="w-[12%]" />
            </colgroup>
            <thead class="sticky top-0 z-10 bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="px-3 py-3 text-left font-semibold text-gray-600">배송원</th>
                <th class="px-3 py-3 text-left font-semibold text-gray-600">차량/계좌</th>
                <th class="px-3 py-3 text-center font-semibold text-gray-600">앱 설치</th>
                <th class="px-3 py-3 text-right font-semibold text-orange-600">지급단가</th>
                <th class="px-3 py-3 text-center font-semibold text-gray-600">1회차</th>
                <th class="px-3 py-3 text-center font-semibold text-gray-600">2회차</th>
                <th class="px-3 py-3 text-center font-semibold text-gray-600">3회차</th>
                <th class="px-3 py-3 text-center font-semibold text-gray-600">관리</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="member in regularRows"
                :key="member.id"
                class="border-b border-gray-100 hover:bg-gray-50 align-top"
              >
                <td class="px-2.5 py-3">
                  <button type="button" class="font-bold text-text hover:text-primary hover:underline" @click="openCrewSettlementCalendar(member, regularMonth)">
                    {{ member.name }}
                  </button>
                  <div class="mt-1 flex flex-wrap items-center gap-1.5 text-xs">
                    <span class="px-2 py-0.5 bg-primary-light text-primary-dark rounded font-semibold">
                      {{ member.team_name || '-' }}
                    </span>
                    <span class="text-gray-500">{{ member.phone || '-' }}</span>
                  </div>
                  <div v-if="member.yongcha_pay_group_name" class="mt-1 text-xs font-semibold text-fuchsia-700">
                    용차팀: {{ member.yongcha_pay_group_name }}
                  </div>
                </td>
                <td class="px-3 py-3">
                  <div class="font-semibold text-gray-800">{{ member.vehicle_number || '-' }}</div>
                  <div class="mt-1 text-xs text-gray-500">
                    {{ member.bank_name || '-' }}
                    <span v-if="member.bank_account_number"> · {{ member.bank_account_number }}</span>
                  </div>
                  <span
                    class="mt-1 inline-flex px-2 py-0.5 rounded text-xs font-semibold"
                    :class="member.inspection_status?.class_name || 'bg-gray-100 text-gray-500'"
                  >
                    {{ member.inspection_status?.label || '-' }}
                  </span>
                </td>
                <td class="px-3 py-3 text-center">
                  <span
                    class="inline-flex items-center justify-center rounded-full px-2.5 py-1 text-xs font-bold whitespace-nowrap"
                    :class="member.app_install_status_class_name || 'bg-gray-100 text-gray-500 border border-gray-200'"
                  >
                    {{ member.app_install_status_label || '-' }}
                  </span>
                  <div v-if="member.app_version" class="mt-1 text-[11px] text-gray-500 whitespace-nowrap">
                    {{ member.app_version }}
                  </div>
                </td>
                <td class="px-2.5 py-3 text-right text-orange-700 font-bold whitespace-nowrap">
                  {{ formatCurrency(Number(member.pay_price || 0)) }}원
                </td>
                <td class="px-3 py-3">
                  <RoundPriceCell
                    :amount="member.regular_round_1_display_pay_price"
                    :active="member.round_1_is_yongcha"
                    :group-name="member.round_1_is_yongcha ? member.yongcha_pay_group_round_1_name : ''"
                    :group-detail="member.round_1_is_yongcha ? member.yongcha_pay_group_round_1_detail : null"
                    @toggle="handleRegularRoundToggle(member, 1)"
                    @edit="openRegularRoundEdit(member, 1)"
                  />
                </td>
                <td class="px-2.5 py-3">
                  <RoundPriceCell
                    :amount="member.regular_round_2_display_pay_price"
                    :active="member.round_2_is_yongcha"
                    :group-name="member.round_2_is_yongcha ? member.yongcha_pay_group_round_2_name : ''"
                    :group-detail="member.round_2_is_yongcha ? member.yongcha_pay_group_round_2_detail : null"
                    @toggle="handleRegularRoundToggle(member, 2)"
                    @edit="openRegularRoundEdit(member, 2)"
                  />
                </td>
                <td class="px-2.5 py-3">
                  <RoundPriceCell
                    :amount="member.regular_round_3_display_pay_price"
                    :active="member.round_3_is_yongcha"
                    :group-name="member.round_3_is_yongcha ? member.yongcha_pay_group_round_3_name : ''"
                    :group-detail="member.round_3_is_yongcha ? member.yongcha_pay_group_round_3_detail : null"
                    @toggle="handleRegularRoundToggle(member, 3)"
                    @edit="openRegularRoundEdit(member, 3)"
                  />
                </td>
                <td class="px-2.5 py-3 text-center">
                  <div class="flex flex-col gap-1.5">
                    <button
                      @click="editCrew(member)"
                      class="px-2 py-1.5 bg-primary text-white rounded-md text-xs font-bold hover:opacity-90"
                    >
                      수정
                    </button>
                    <button
                      @click="openFixedPayModal(member)"
                      class="px-2 py-1.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-md text-xs font-bold hover:bg-amber-100"
                    >
                      기본급
                    </button>
                    <button
                      @click="openConvertYongchaModal(member)"
                      class="px-2 py-1.5 bg-red-50 text-red-600 border border-red-200 rounded-md text-xs font-bold hover:bg-red-100 whitespace-nowrap"
                    >
                      용차전환
                    </button>
                    <button
                      @click="deleteCrew(member)"
                      class="px-2 py-1.5 bg-red-500 text-white rounded-md text-xs font-bold hover:opacity-90"
                    >
                      삭제
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="regularCount === 0">
                <td colspan="8" class="px-5 py-12 text-center text-gray-400">배송원이 없습니다.</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="regularTotalPages > 1" class="flex items-center justify-between px-5 py-4 border-t border-gray-200">
          <span class="text-gray-500">총 {{ regularCount }}명 ({{ regularPage }}/{{ regularTotalPages }}페이지)</span>
          <PaginationButtons :page="regularPage" :pages="regularVisiblePages" :total-pages="regularTotalPages"
            @change="regularPage = $event" />
        </div>
        </section>

        <aside v-if="false" class="bg-white rounded-xl border border-gray-200 overflow-hidden h-fit xl:sticky xl:top-4 xl:max-h-full">
          <div class="px-5 py-4 border-b border-gray-200">
            <h3 class="font-bold text-text">{{ selectedCrewSettlement?.name || '정산 내역' }}</h3>
            <p class="text-sm text-gray-500">{{ regularMonth }} 월별 정산</p>
          </div>
          <div v-if="!selectedCrewSettlement" class="px-5 py-12 text-center text-gray-400">왼쪽 목록에서 이름을 클릭하세요.</div>
          <div v-else-if="crewSettlementLoading" class="px-5 py-12 text-center text-gray-500">불러오는 중...</div>
          <div v-else>
            <div class="grid grid-cols-2 gap-2 border-b border-gray-100 p-4 text-sm">
              <div class="rounded-lg bg-gray-50 p-3">
                <p class="text-xs text-gray-500">월 지급액</p>
                <p class="mt-1 font-extrabold text-primary">{{ formatCurrency(Number(crewSettlementTotals.pay_amount || 0)) }}원</p>
              </div>
              <div class="rounded-lg bg-gray-50 p-3">
                <p class="text-xs text-gray-500">가구 / 박스</p>
                <p class="mt-1 font-bold text-text">{{ Number(crewSettlementTotals.households || 0).toLocaleString() }} / {{ Number(crewSettlementTotals.boxes || 0).toLocaleString() }}</p>
              </div>
            </div>
            <div class="max-h-[520px] divide-y divide-gray-100 overflow-y-auto">
              <div
                v-for="row in crewSettlementRows"
                :key="`regular-history-${row.date}`"
                class="px-5 py-4 text-sm hover:bg-gray-50"
              >
                <button type="button" class="mb-2 flex w-full items-center justify-between gap-3 text-left" @click="toggleSettlementDate(row)">
                  <span class="flex items-center gap-2 font-bold text-text">
                    {{ row.date }}
                    <span class="text-[11px] font-semibold text-gray-400">{{ isSettlementDateExpanded(row) ? '접기' : '회차 상세' }}</span>
                  </span>
                  <span class="rounded-full px-2 py-0.5 text-xs font-bold" :class="row.is_yongcha ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-600'">
                    용차 {{ yongchaStatusMark(row) }}
                  </span>
                </button>
                <div class="grid grid-cols-2 gap-x-3 gap-y-1 text-gray-600">
                  <span>가구 {{ Number(row.households || 0).toLocaleString() }}</span>
                  <span>박스 {{ Number(row.boxes || 0).toLocaleString() }}</span>
                  <span>
                    용차팀
                    <strong v-if="row.has_yongcha_pay_group && row.yongcha_pay_group_name" class="font-extrabold text-fuchsia-700">
                      {{ row.yongcha_pay_group_name }}
                    </strong>
                    <span v-else>{{ row.has_yongcha_pay_group ? 'O' : 'X' }}</span>
                  </span>
                  <span class="font-bold text-blue-700">{{ formatCurrency(Number(row.pay_amount || 0)) }}원</span>
                </div>
                <div v-if="isSettlementDateExpanded(row)" class="mt-3 overflow-hidden rounded-lg border border-gray-200 bg-white">
                  <div
                    v-for="round in (row.rounds || [])"
                    :key="`regular-history-${row.date}-${round.round_label}`"
                    class="border-b border-gray-100 px-3 py-3 last:border-b-0"
                  >
                    <div class="mb-2 flex items-center justify-between gap-2">
                      <strong class="text-text">{{ round.round_label }}</strong>
                      <span class="text-xs font-semibold text-gray-500">{{ round.team_name || '-' }}</span>
                    </div>
                    <div class="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-gray-600">
                      <span>가구 {{ Number(round.households || 0).toLocaleString() }}</span>
                      <span>박스 {{ Number(round.boxes || 0).toLocaleString() }}</span>
                      <span>용차 {{ yongchaStatusMark(round) }}</span>
                      <span>
                        용차팀
                        <strong v-if="round.has_yongcha_pay_group && round.yongcha_pay_group_name" class="font-extrabold text-fuchsia-700">
                          {{ round.yongcha_pay_group_name }}
                        </strong>
                        <span v-else>{{ round.has_yongcha_pay_group ? 'O' : 'X' }}</span>
                      </span>
                      <span>수신 {{ formatCurrency(Number(round.receive_amount || 0)) }}원</span>
                      <span class="font-bold text-blue-700">지급 {{ formatCurrency(Number(round.pay_amount || 0)) }}원</span>
                    </div>
                  </div>
                  <div v-if="!(row.rounds || []).length" class="px-3 py-4 text-center text-xs text-gray-400">
                    회차 상세가 없습니다.
                  </div>
                </div>
              </div>
              <div v-if="crewSettlementRows.length === 0" class="px-5 py-12 text-center text-gray-400">정산 내역이 없습니다.</div>
            </div>
          </div>
        </aside>
      </div>

      <div
        v-else-if="activeTab === 'yongcha'"
        class="grid grid-cols-1 gap-5 xl:h-[calc(100vh-260px)]"
        :class="yongchaBulkMode ? 'xl:grid-cols-[minmax(0,1fr)_420px]' : ''"
      >
        <div class="bg-white rounded-xl border border-gray-200 overflow-hidden xl:flex xl:min-h-0 xl:flex-col">
          <div class="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h3 class="font-bold text-text">용차 인원</h3>
              <p class="text-sm text-gray-500">조 기본값을 가져오되, 배송원별 1/2/3회차 단가를 따로 수정할 수 있습니다.</p>
            </div>
            <div class="flex items-center gap-3">
              <input
                v-model="yongchaMonth"
                type="month"
                class="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 outline-none focus:border-primary"
              />
              <span class="text-sm text-gray-500">{{ yongchaCount }}</span>
            </div>
          </div>

          <div class="min-h-0 overflow-auto xl:flex-1">
            <table class="min-w-[980px] w-full text-sm">
              <thead class="sticky top-0 z-10 bg-gray-50 border-b border-gray-200">
                <tr>
                  <th v-if="yongchaBulkMode" class="px-3 py-3 text-center font-semibold text-gray-600">선택</th>
                  <th class="px-3 py-3 text-left font-semibold text-gray-600">배송원</th>
                  <th class="px-3 py-3 text-right font-semibold text-gray-600">박스</th>
                  <th class="px-3 py-3 text-right font-semibold text-gray-600">수신 합계</th>
                  <th class="px-3 py-3 text-center font-semibold text-gray-600">1회차</th>
                  <th class="px-3 py-3 text-center font-semibold text-gray-600">2회차</th>
                  <th class="px-3 py-3 text-center font-semibold text-gray-600">3회차</th>
                  <th class="px-3 py-3 text-center font-semibold text-gray-600">관리</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="member in yongchaRows"
                  :key="member.id"
                  class="border-b border-gray-100 hover:bg-gray-50 cursor-pointer align-top"
                  :class="selectedYongcha?.id === member.id ? 'bg-red-50' : ''"
                  @click="openCrewSettlementCalendar(member, yongchaMonth)"
                >
                  <td v-if="yongchaBulkMode" class="px-3 py-3 text-center" @click.stop>
                    <input
                      type="checkbox"
                      class="h-4 w-4 rounded border-gray-300 text-primary"
                      :checked="Boolean(yongchaBulkSelections[member.id])"
                      @change="toggleBulkSelection(member, $event.target.checked)"
                    />
                  </td>
                <td class="px-2.5 py-3">
                    <button type="button" class="font-bold text-text hover:text-primary hover:underline" @click.stop="openCrewSettlementCalendar(member, yongchaMonth)">
                      {{ member.name }}
                    </button>
                    <div class="mt-1 flex flex-wrap items-center gap-1.5 text-xs">
                      <span class="px-2 py-0.5 bg-red-50 text-red-600 rounded font-semibold">{{ member.team_name || '-' }}</span>
                      <span class="text-gray-500">{{ member.vehicle_number || '-' }}</span>
                    </div>
                    <div v-if="member.yongcha_pay_group_name" class="mt-1 text-xs font-semibold text-fuchsia-700">
                      용차팀: {{ member.yongcha_pay_group_name }}
                    </div>
                    <select
                      v-if="yongchaBulkMode"
                      class="mt-2 w-full rounded-lg border border-fuchsia-200 bg-white px-2 py-1.5 text-xs font-semibold text-gray-700"
                      :value="bulkSelectionGroupId(member)"
                      @click.stop
                      @change="setBulkSelectionGroup(member, $event.target.value)"
                    >
                      <option value="">개인/조별 단가</option>
                      <option v-for="group in yongchaPayGroups" :key="`bulk-row-group-${member.id}-${group.id}`" :value="group.id">
                        {{ group.name }}
                      </option>
                    </select>
                  </td>
                  <td class="px-3 py-3 text-right font-semibold">{{ Number(member.total_boxes || 0).toLocaleString() }}</td>
                  <td class="px-3 py-3 text-right font-bold text-blue-700 whitespace-nowrap">
                    {{ formatCurrency(Number(member.total_receive || 0)) }}원
                  </td>
                <td class="px-2.5 py-3">
                    <InlineRateEditor
                      :amount="member.yongcha_round_1_display_pay_price"
                      :group-name="member.yongcha_pay_group_round_1_name"
                      :group-detail="member.yongcha_pay_group_round_1_detail"
                      @edit="openYongchaRoundEdit(member, 1)"
                      @group="openYongchaPayGroupModal(member)"
                    />
                  </td>
                  <td class="px-3 py-3">
                    <InlineRateEditor
                      :amount="member.yongcha_round_2_display_pay_price"
                      :group-name="member.yongcha_pay_group_round_2_name"
                      :group-detail="member.yongcha_pay_group_round_2_detail"
                      @edit="openYongchaRoundEdit(member, 2)"
                      @group="openYongchaPayGroupModal(member)"
                    />
                  </td>
                  <td class="px-3 py-3">
                    <InlineRateEditor
                      :amount="member.yongcha_round_3_display_pay_price"
                      :group-name="member.yongcha_pay_group_round_3_name"
                      :group-detail="member.yongcha_pay_group_round_3_detail"
                      @edit="openYongchaRoundEdit(member, 3)"
                      @group="openYongchaPayGroupModal(member)"
                    />
                  </td>
                <td class="px-2.5 py-3 text-center">
                    <div class="grid grid-cols-2 gap-1.5">
                      <button
                        class="px-2.5 py-1.5 bg-fuchsia-50 text-fuchsia-700 border border-fuchsia-200 rounded-md text-xs font-bold hover:bg-fuchsia-100 whitespace-nowrap"
                        @click.stop="openYongchaPayGroupModal(member)"
                      >
                        용차팀 설정
                      </button>
                      <button
                        class="px-2.5 py-1.5 bg-gray-800 text-white rounded-md text-xs font-bold hover:opacity-90 whitespace-nowrap"
                        @click.stop="convertYongcha(member)"
                      >
                        정규전환
                      </button>
                      <button
                        class="col-span-2 px-2.5 py-1.5 bg-red-500 text-white rounded-md text-xs font-bold hover:opacity-90"
                        @click.stop="deleteYongcha(member)"
                      >
                        삭제
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="yongchaCount === 0">
                  <td :colspan="yongchaBulkMode ? 8 : 7" class="px-5 py-12 text-center text-gray-400">용차 인원이 없습니다.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="yongchaTotalPages > 1" class="flex items-center justify-between px-5 py-4 border-t border-gray-200">
            <span class="text-gray-500">총 {{ yongchaCount }}명 ({{ yongchaPage }}/{{ yongchaTotalPages }}페이지)</span>
            <PaginationButtons :page="yongchaPage" :pages="yongchaVisiblePages" :total-pages="yongchaTotalPages"
              @change="yongchaPage = $event" />
          </div>
        </div>

        <div v-if="yongchaBulkMode" class="bg-white rounded-xl border border-gray-200 overflow-hidden h-fit xl:sticky xl:top-4 xl:max-h-full">
          <div class="px-5 py-4 border-b border-gray-200">
            <h3 class="font-bold text-text">선택한 배송원</h3>
            <p class="text-sm text-gray-500">{{ yongchaBulkSelectedRows.length }}명 선택됨</p>
          </div>
          <div v-if="yongchaBulkSelectedRows.length === 0" class="px-5 py-12 text-center text-gray-400">
            왼쪽 목록에서 배송원을 선택하세요.
          </div>
          <div v-else class="divide-y divide-gray-100">
            <div v-for="item in yongchaBulkSelectedRows" :key="`bulk-selected-${item.member.id}`" class="px-5 py-4">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="font-bold text-text">{{ item.member.name }}</div>
                  <div class="mt-1 text-xs text-gray-500">{{ item.member.team_name || '-' }} · {{ item.member.vehicle_number || '-' }}</div>
                  <div class="mt-1 text-xs font-semibold text-fuchsia-700">
                    {{ bulkGroupName(item.groupId) }}
                  </div>
                </div>
                <button type="button" class="text-xs font-bold text-red-500" @click="removeBulkSelection(item.member.id)">삭제</button>
              </div>
            </div>
            <div class="p-5">
              <button type="button" class="w-full rounded-lg bg-primary px-4 py-3 font-bold text-white disabled:opacity-50" :disabled="yongchaBulkSelectedRows.length === 0" @click="submitBulkYongchaPayGroups">
                용차팀 설정
              </button>
            </div>
          </div>
        </div>

        <div v-else-if="false" class="bg-white rounded-xl border border-gray-200 overflow-hidden h-fit xl:sticky xl:top-4 xl:max-h-full">
          <div class="px-5 py-4 border-b border-gray-200">
            <h3 class="font-bold text-text">{{ selectedCrewSettlement?.name || '용차 상세' }}</h3>
            <p class="text-sm text-gray-500">{{ yongchaMonth }} 월별 정산</p>
          </div>
          <div v-if="!selectedCrewSettlement" class="px-5 py-12 text-center text-gray-400">왼쪽 목록에서 이름을 클릭하세요.</div>
          <div v-else-if="crewSettlementLoading" class="px-5 py-12 text-center text-gray-500">불러오는 중...</div>
          <div v-else>
            <div class="grid grid-cols-2 gap-2 border-b border-gray-100 p-4 text-sm">
              <div class="rounded-lg bg-gray-50 p-3">
                <p class="text-xs text-gray-500">월 지급액</p>
                <p class="mt-1 font-extrabold text-primary">{{ formatCurrency(Number(crewSettlementTotals.pay_amount || 0)) }}원</p>
              </div>
              <div class="rounded-lg bg-gray-50 p-3">
                <p class="text-xs text-gray-500">가구 / 박스</p>
                <p class="mt-1 font-bold text-text">{{ Number(crewSettlementTotals.households || 0).toLocaleString() }} / {{ Number(crewSettlementTotals.boxes || 0).toLocaleString() }}</p>
              </div>
            </div>
            <div class="max-h-[520px] divide-y divide-gray-100 overflow-y-auto">
              <div
                v-for="row in crewSettlementRows"
                :key="`yongcha-history-${row.date}`"
                class="px-5 py-4 text-sm hover:bg-gray-50"
              >
                <button type="button" class="mb-2 flex w-full items-center justify-between gap-3 text-left" @click="toggleSettlementDate(row)">
                  <span class="flex items-center gap-2 font-bold text-text">
                    {{ row.date }}
                    <span class="text-[11px] font-semibold text-gray-400">{{ isSettlementDateExpanded(row) ? '접기' : '회차 상세' }}</span>
                  </span>
                  <span class="rounded-full px-2 py-0.5 text-xs font-bold" :class="row.is_yongcha ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-600'">
                    용차 {{ yongchaStatusMark(row) }}
                  </span>
                </button>
                <div class="grid grid-cols-2 gap-x-3 gap-y-1 text-gray-600">
                  <span>가구 {{ Number(row.households || 0).toLocaleString() }}</span>
                  <span>박스 {{ Number(row.boxes || 0).toLocaleString() }}</span>
                  <span>
                    용차팀
                    <strong v-if="row.has_yongcha_pay_group && row.yongcha_pay_group_name" class="font-extrabold text-fuchsia-700">
                      {{ row.yongcha_pay_group_name }}
                    </strong>
                    <span v-else>{{ row.has_yongcha_pay_group ? 'O' : 'X' }}</span>
                  </span>
                  <span class="font-bold text-blue-700">{{ formatCurrency(Number(row.pay_amount || 0)) }}원</span>
                </div>
                <div v-if="isSettlementDateExpanded(row)" class="mt-3 overflow-hidden rounded-lg border border-gray-200 bg-white">
                  <div
                    v-for="round in (row.rounds || [])"
                    :key="`yongcha-history-${row.date}-${round.round_label}`"
                    class="border-b border-gray-100 px-3 py-3 last:border-b-0"
                  >
                    <div class="mb-2 flex items-center justify-between gap-2">
                      <strong class="text-text">{{ round.round_label }}</strong>
                      <span class="text-xs font-semibold text-gray-500">{{ round.team_name || '-' }}</span>
                    </div>
                    <div class="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-gray-600">
                      <span>가구 {{ Number(round.households || 0).toLocaleString() }}</span>
                      <span>박스 {{ Number(round.boxes || 0).toLocaleString() }}</span>
                      <span>용차 {{ yongchaStatusMark(round) }}</span>
                      <span>
                        용차팀
                        <strong v-if="round.has_yongcha_pay_group && round.yongcha_pay_group_name" class="font-extrabold text-fuchsia-700">
                          {{ round.yongcha_pay_group_name }}
                        </strong>
                        <span v-else>{{ round.has_yongcha_pay_group ? 'O' : 'X' }}</span>
                      </span>
                      <span>수신 {{ formatCurrency(Number(round.receive_amount || 0)) }}원</span>
                      <span class="font-bold text-blue-700">지급 {{ formatCurrency(Number(round.pay_amount || 0)) }}원</span>
                    </div>
                  </div>
                  <div v-if="!(row.rounds || []).length" class="px-3 py-4 text-center text-xs text-gray-400">
                    회차 상세가 없습니다.
                  </div>
                </div>
              </div>
              <div v-if="crewSettlementRows.length === 0" class="px-5 py-12 text-center text-gray-400">정산 내역이 없습니다.</div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="activeTab === 'yongchaGroups'" class="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px] gap-5">
        <section class="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-200 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 class="font-bold text-text">용차팀 목록</h3>
              <p class="text-sm text-gray-500">용차팀별 회차 기본급, 기준 가구수, 추가 착당 금액을 관리합니다.</p>
            </div>
            <div class="flex items-center gap-2">
              <input
                v-model="yongchaMonth"
                type="month"
                class="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 outline-none focus:border-primary"
              />
              <button type="button" class="rounded-lg bg-gray-900 px-4 py-2 text-sm font-bold text-white hover:bg-gray-800" @click="openNewYongchaPayGroup">
                용차팀 추가
              </button>
              <button type="button" class="px-4 py-2 rounded-lg border border-gray-300 text-sm font-semibold text-gray-700 hover:bg-gray-50" @click="loadYongchaPayGroups">
                새로고침
              </button>
            </div>
          </div>

          <div v-if="yongchaGroupLoading" class="px-5 py-12 text-center text-gray-400">불러오는 중...</div>
          <div v-else-if="yongchaPayGroups.length === 0" class="px-5 py-12 text-center text-gray-400">
            등록된 용차팀이 없습니다. 상단의 용차팀 추가 버튼으로 새 팀을 등록하세요.
          </div>
          <div v-else class="divide-y divide-gray-100">
            <article
              v-for="group in yongchaPayGroups"
              :key="group.id"
              class="cursor-pointer px-5 py-4 hover:bg-gray-50"
              :class="selectedYongchaGroup?.id === group.id ? 'bg-fuchsia-50' : ''"
              @click="selectYongchaGroup(group)"
            >
              <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div class="flex flex-wrap items-center gap-2">
                    <h4 class="font-bold text-text">{{ group.name }}</h4>
                    <span
                      v-if="group.exclude_base_pay_on_multi_round"
                      class="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-700"
                    >
                      다회차 기본급 미적용
                    </span>
                  </div>
                  <p class="mt-1 text-xs text-gray-500">
                    {{ group.exclude_base_pay_on_multi_round
                      ? '다회차 용차일 때는 기본급 없이 추가 착당 단가만 적용합니다.'
                      : '다회차 용차여도 기본급과 추가 착당 단가를 그대로 적용합니다.' }}
                  </p>
                </div>
                <div class="flex shrink-0 items-center gap-2">
                  <button type="button" class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50" @click.stop="startEditYongchaPayGroup(group)">
                    수정
                  </button>
                  <button type="button" class="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50" @click.stop="removeYongchaPayGroup(group)">
                    삭제
                  </button>
                </div>
              </div>
              <div class="mt-3 grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-gray-600">
                <div v-for="roundNo in [1, 2, 3]" :key="`${group.id}-${roundNo}`" class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <div class="font-bold text-gray-800">{{ roundNo }}회차</div>
                  <div>기본급 {{ formatCurrency(Number(group[`round_${roundNo}_base_pay`] || 0)) }}원</div>
                  <div>기준 {{ Number(group[`round_${roundNo}_base_households`] || 0).toLocaleString() }}가구</div>
                  <div>추가 착당 {{ formatCurrency(Number(group[`round_${roundNo}_extra_household_pay`] || 0)) }}원</div>
                </div>
              </div>
            </article>
          </div>
        </section>

        <aside class="bg-white rounded-xl border border-gray-200 p-5 h-fit">
          <section v-if="selectedYongchaGroup" class="mb-5 rounded-xl border border-fuchsia-100 bg-fuchsia-50/40">
            <div class="border-b border-fuchsia-100 px-4 py-3">
              <h3 class="font-bold text-text">{{ selectedYongchaGroup.name }} 정산 내역</h3>
              <p class="text-sm text-gray-500">{{ yongchaMonth }} 기준</p>
            </div>
            <div v-if="yongchaGroupSettlementLoading" class="px-4 py-8 text-center text-gray-500">불러오는 중...</div>
            <div v-else>
              <div class="grid grid-cols-2 gap-2 p-4 text-sm">
                <div class="rounded-lg bg-white p-3">
                  <p class="text-xs text-gray-500">월 가구수</p>
                  <p class="font-bold text-text">{{ Number(yongchaGroupSettlement.totals.households || 0).toLocaleString() }}</p>
                </div>
                <div class="rounded-lg bg-white p-3">
                  <p class="text-xs text-gray-500">월 박스수</p>
                  <p class="font-bold text-text">{{ Number(yongchaGroupSettlement.totals.boxes || 0).toLocaleString() }}</p>
                </div>
                <div class="rounded-lg bg-white p-3">
                  <p class="text-xs text-gray-500">수신가격</p>
                  <p class="font-bold text-blue-700">{{ formatCurrency(Number(yongchaGroupSettlement.totals.receive_amount || 0)) }}원</p>
                </div>
                <div class="rounded-lg bg-white p-3">
                  <p class="text-xs text-gray-500">지급가격</p>
                  <p class="font-bold text-primary">{{ formatCurrency(Number(yongchaGroupSettlement.totals.pay_amount || 0)) }}원</p>
                </div>
              </div>
              <div class="border-t border-fuchsia-100">
                <div v-for="row in yongchaGroupDailyRows" :key="`group-daily-${row.date}`" class="border-b border-fuchsia-50 px-4 py-3 text-sm last:border-b-0">
                  <div class="flex items-center justify-between">
                    <strong>{{ row.date }}</strong>
                    <span class="font-bold text-primary">{{ formatCurrency(Number(row.pay_amount || 0)) }}원</span>
                  </div>
                  <div class="mt-1 grid grid-cols-2 gap-1 text-xs text-gray-600">
                    <span>가구 {{ Number(row.households || 0).toLocaleString() }}</span>
                    <span>박스 {{ Number(row.boxes || 0).toLocaleString() }}</span>
                    <span>수신 {{ formatCurrency(Number(row.receive_amount || 0)) }}원</span>
                    <span>지급 {{ formatCurrency(Number(row.pay_amount || 0)) }}원</span>
                  </div>
                </div>
                <div v-if="yongchaGroupDailyRows.length === 0" class="px-4 py-8 text-center text-sm text-gray-400">팀 정산 내역이 없습니다.</div>
              </div>
              <div v-if="yongchaGroupDailyTotalPages > 1" class="flex items-center justify-center gap-1 border-t border-fuchsia-100 p-3">
                <PaginationButtons :page="yongchaGroupSettlementPage" :pages="yongchaGroupDailyVisiblePages" :total-pages="yongchaGroupDailyTotalPages"
                  @change="changeYongchaGroupSettlementPage" />
              </div>
              <div class="border-t border-fuchsia-100 p-4">
                <h4 class="mb-2 text-sm font-bold text-text">소속 배송원</h4>
                <div class="space-y-2">
                  <button
                    v-for="member in yongchaGroupSettlement.members"
                    :key="`group-member-${member.id}`"
                    type="button"
                    class="flex w-full items-center justify-between rounded-lg bg-white px-3 py-2 text-left text-sm hover:bg-gray-50"
                    @click="openGroupMemberSettlement(member)"
                  >
                    <span class="font-semibold text-text">{{ member.name }}</span>
                    <span class="text-xs font-bold text-primary">{{ formatCurrency(Number(member.pay_amount || 0)) }}원</span>
                  </button>
                </div>
              </div>
            </div>
          </section>

          <div v-if="!selectedYongchaGroup" class="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-10 text-center">
            <h3 class="font-bold text-text">용차팀을 선택하세요</h3>
            <p class="mt-2 text-sm text-gray-500">왼쪽 목록에서 팀을 클릭하면 월별 팀 정산과 소속 배송원을 확인할 수 있습니다.</p>
            <button type="button" class="mt-4 rounded-lg bg-gray-900 px-4 py-2 text-sm font-bold text-white hover:bg-gray-800" @click="openNewYongchaPayGroup">
              용차팀 추가
            </button>
          </div>
        </aside>
      </div>

      <div v-if="showYongchaGroupEditorModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white">
          <div class="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-gray-200 bg-white px-6 py-5">
            <div>
              <h3 class="text-xl font-bold text-text">{{ yongchaGroupEditingId ? '용차팀 수정' : '용차팀 추가' }}</h3>
              <p class="mt-1 text-sm text-gray-500">팀 이름과 회차별 기본급, 기준 가구수, 추가 착당 금액을 입력하세요.</p>
            </div>
            <button type="button" class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50" @click="cancelYongchaGroupEdit">
              닫기
            </button>
          </div>
          <div class="p-6">
            <label class="block">
              <span class="block text-sm font-semibold text-gray-600 mb-2">팀 이름</span>
              <input v-model="yongchaGroupForm.name" type="text" class="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-primary" placeholder="예: 신화" />
            </label>
            <label class="mt-4 flex cursor-pointer items-start gap-3 rounded-xl border border-amber-100 bg-amber-50/60 p-4">
              <input
                v-model="yongchaGroupForm.exclude_base_pay_on_multi_round"
                type="checkbox"
                class="mt-1 h-4 w-4 rounded border-gray-300 text-primary"
              />
              <span>
                <span class="block text-sm font-bold text-amber-900">다회차일 시 기본급 미적용</span>
                <span class="mt-1 block text-xs leading-5 text-amber-700">
                  체크하면 같은 날짜에 여러 용차 회차를 배송한 경우 기본급을 빼고 추가 착당 단가만 적용합니다.
                </span>
              </span>
            </label>
            <div class="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
              <section v-for="roundNo in [1, 2, 3]" :key="`editor-round-${roundNo}`" class="rounded-xl border border-gray-200 bg-gray-50 p-4">
                <strong class="block text-sm text-gray-800 mb-4">{{ roundNo }}회차</strong>
                <div class="space-y-3">
                  <label class="block">
                    <span class="block text-xs text-gray-500 mb-1">기본급</span>
                    <input v-model.number="yongchaGroupForm[`round_${roundNo}_base_pay`]" type="number" min="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-right" @wheel.prevent />
                  </label>
                  <label class="block">
                    <span class="block text-xs text-gray-500 mb-1">기준 가구수</span>
                    <input v-model.number="yongchaGroupForm[`round_${roundNo}_base_households`]" type="number" min="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-right" @wheel.prevent />
                  </label>
                  <label class="block">
                    <span class="block text-xs text-gray-500 mb-1">추가 착당 금액</span>
                    <input v-model.number="yongchaGroupForm[`round_${roundNo}_extra_household_pay`]" type="number" min="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-right" @wheel.prevent />
                  </label>
                </div>
              </section>
            </div>
          </div>
          <div class="sticky bottom-0 flex justify-end gap-2 border-t border-gray-200 bg-white px-6 py-4">
            <button type="button" class="rounded-lg border border-gray-300 px-5 py-3 font-semibold text-gray-700 hover:bg-gray-50" @click="cancelYongchaGroupEdit">
              취소
            </button>
            <button type="button" class="rounded-lg bg-gray-900 px-5 py-3 font-semibold text-white disabled:opacity-50" :disabled="yongchaGroupSaving" @click="submitSaveYongchaPayGroup">
              {{ yongchaGroupEditingId ? '수정 저장' : '용차팀 추가' }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="showEditModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl p-6 w-full max-w-md">
          <h3 class="text-xl font-bold text-text mb-5">배송원 수정</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-gray-500 mb-2">이름</label>
              <input v-model="crewForm.name" type="text" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
            </div>
            <div>
              <label class="block text-gray-500 mb-2">전화번호</label>
              <input v-model="crewForm.phone" type="tel" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
            </div>
            <div>
              <label class="block text-gray-500 mb-2">차량번호</label>
              <input v-model="crewForm.vehicle_number" type="text" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-gray-500 mb-2">급여 은행</label>
                <input v-model="crewForm.bank_name" type="text" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
              </div>
              <div>
                <label class="block text-gray-500 mb-2">예금주</label>
                <input v-model="crewForm.bank_account_holder" type="text" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
              </div>
            </div>
            <div>
              <label class="block text-gray-500 mb-2">급여 계좌번호</label>
              <input v-model="crewForm.bank_account_number" type="text" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
            </div>
            <div>
              <label class="block text-gray-500 mb-2">자동차 검사일</label>
              <input v-model="crewForm.vehicle_inspection_date" type="date" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
            </div>
            <div>
              <label class="block text-orange-600 font-medium mb-2">지급단가 (박스당)</label>
              <input
                v-model.number="crewForm.pay_price"
                type="number"
                min="0"
                class="w-full px-4 py-3 border border-orange-300 rounded-lg text-right text-lg bg-orange-50 focus:border-orange-400 outline-none"
              />
            </div>
          </div>
          <div class="flex justify-end gap-3 mt-6">
            <button @click="showEditModal = false" class="px-5 py-3 border border-gray-300 rounded-lg hover:bg-gray-50">취소</button>
            <button @click="submitEditCrew" class="px-5 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">저장</button>
          </div>
        </div>
      </div>

      <div v-if="showRoundModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl p-6 w-full max-w-md">
          <h3 class="text-xl font-bold text-text mb-2">{{ roundModalTitle }}</h3>
          <p class="text-sm text-gray-500 mb-5">{{ roundModalDescription }}</p>
          <div>
            <label class="block text-gray-500 mb-2">용차 지급단가 (가구당)</label>
            <input
              v-model.number="roundModalForm.amount"
              type="number"
              min="0"
              class="w-full px-4 py-3 border border-fuchsia-300 rounded-lg text-right text-lg bg-fuchsia-50 focus:border-fuchsia-400 outline-none"
            />
          </div>
          <div class="flex justify-end gap-3 mt-6">
            <button @click="showRoundModal = false" class="px-5 py-3 border border-gray-300 rounded-lg hover:bg-gray-50">취소</button>
            <button @click="submitRoundModal" class="px-5 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">적용</button>
          </div>
        </div>
      </div>

      <div v-if="showConvertModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl p-6 w-full max-w-2xl">
          <h3 class="text-xl font-bold text-text mb-2">용차 전환</h3>
          <p class="text-sm text-gray-500 mb-5">
            조 관리의 기본 단가를 불러왔습니다. 필요하면 배송원별로 수정해서 적용하세요.
          </p>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-gray-500 mb-2">1회차</label>
              <input
                v-model.number="convertForm.round1"
                type="number"
                min="0"
                class="w-full px-4 py-3 border border-fuchsia-300 rounded-lg text-right bg-fuchsia-50 focus:border-fuchsia-400 outline-none"
              />
            </div>
            <div>
              <label class="block text-gray-500 mb-2">2회차</label>
              <input
                v-model.number="convertForm.round2"
                type="number"
                min="0"
                class="w-full px-4 py-3 border border-fuchsia-300 rounded-lg text-right bg-fuchsia-50 focus:border-fuchsia-400 outline-none"
              />
            </div>
            <div>
              <label class="block text-gray-500 mb-2">3회차</label>
              <input
                v-model.number="convertForm.round3"
                type="number"
                min="0"
                class="w-full px-4 py-3 border border-fuchsia-300 rounded-lg text-right bg-fuchsia-50 focus:border-fuchsia-400 outline-none"
              />
            </div>
          </div>
          <div class="flex justify-end gap-3 mt-6">
            <button @click="showConvertModal = false" class="px-5 py-3 border border-gray-300 rounded-lg hover:bg-gray-50">취소</button>
            <button @click="submitConvertYongcha" class="px-5 py-3 bg-red-600 text-white rounded-lg font-medium hover:opacity-90">용차로 적용</button>
          </div>
        </div>
      </div>

      <div v-if="showFixedPayModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl p-6 w-full max-w-2xl">
          <h3 class="text-xl font-bold text-text mb-2">{{ fixedPayForm.memberName }} 기본급 설정</h3>
          <p class="text-sm text-gray-500 mb-5">입력한 회차는 박스 수와 무관하게 고정 급여로 계산합니다. 0원으로 두면 기존 박스당 단가를 사용합니다.</p>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-gray-500 mb-2">1회차 기본급</label>
              <input v-model.number="fixedPayForm.round1" type="number" min="0" class="w-full px-4 py-3 border border-amber-300 rounded-lg text-right bg-amber-50 focus:border-amber-400 outline-none" />
            </div>
            <div>
              <label class="block text-gray-500 mb-2">2회차 기본급</label>
              <input v-model.number="fixedPayForm.round2" type="number" min="0" class="w-full px-4 py-3 border border-amber-300 rounded-lg text-right bg-amber-50 focus:border-amber-400 outline-none" />
            </div>
            <div>
              <label class="block text-gray-500 mb-2">3회차 기본급</label>
              <input v-model.number="fixedPayForm.round3" type="number" min="0" class="w-full px-4 py-3 border border-amber-300 rounded-lg text-right bg-amber-50 focus:border-amber-400 outline-none" />
            </div>
          </div>
          <div class="flex justify-end gap-3 mt-6">
            <button @click="showFixedPayModal = false" class="px-5 py-3 border border-gray-300 rounded-lg hover:bg-gray-50">취소</button>
            <button @click="submitFixedPay" class="px-5 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">적용</button>
          </div>
        </div>
      </div>

      <div v-if="showYongchaPayGroupModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
          <h3 class="text-xl font-bold text-text mb-2">{{ yongchaGroupTargetMember?.name || '배송원' }} 용차팀 설정</h3>
          <p class="text-sm text-gray-500 mb-5">적용할 용차팀을 선택하세요. 팀 조건 추가와 수정은 용차팀 관리 탭에서 처리합니다.</p>

          <div class="rounded-xl border border-gray-200 overflow-hidden">
            <div class="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
              <strong class="text-text">용차팀 목록</strong>
              <button type="button" class="text-sm font-semibold text-primary" @click="loadYongchaPayGroups">새로고침</button>
            </div>
            <div v-if="yongchaGroupLoading" class="p-6 text-center text-gray-400">불러오는 중...</div>
            <div v-else-if="yongchaPayGroups.length === 0" class="p-6 text-center text-gray-400">
              등록된 용차팀이 없습니다. 용차팀 관리 탭에서 먼저 추가하세요.
            </div>
            <div v-else class="divide-y divide-gray-100">
              <label
                v-for="group in yongchaPayGroups"
                :key="group.id"
                class="block cursor-pointer p-4 hover:bg-gray-50"
                :class="String(yongchaGroupSelectedId) === String(group.id) ? 'bg-fuchsia-50' : ''"
              >
                <div class="flex items-center gap-3">
                  <input v-model="yongchaGroupSelectedId" type="radio" :value="group.id" />
                  <div class="min-w-0">
                    <div class="font-bold text-text">{{ group.name }}</div>
                    <div
                      v-if="group.exclude_base_pay_on_multi_round"
                      class="mt-1 inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-700"
                    >
                      다회차 기본급 미적용
                    </div>
                  </div>
                </div>
                <div class="mt-3 grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-gray-600">
                  <div v-for="roundNo in [1, 2, 3]" :key="`${group.id}-${roundNo}`" class="rounded-lg border border-gray-200 bg-white p-3">
                    <div class="font-bold text-gray-800">{{ roundNo }}회차</div>
                    <div>기본급 {{ formatCurrency(Number(group[`round_${roundNo}_base_pay`] || 0)) }}원</div>
                    <div>기준 {{ Number(group[`round_${roundNo}_base_households`] || 0).toLocaleString() }}가구</div>
                    <div>추가 착당 {{ formatCurrency(Number(group[`round_${roundNo}_extra_household_pay`] || 0)) }}원</div>
                  </div>
                </div>
              </label>
            </div>
            <label class="flex cursor-pointer items-center gap-3 border-t border-gray-200 p-4 text-sm text-gray-600 hover:bg-gray-50">
              <input v-model="yongchaGroupSelectedId" type="radio" value="" />
              개인/조별 가구당 단가 사용
            </label>
          </div>

          <div v-if="isRegularYongchaGroupTarget" class="mt-4 rounded-xl border border-fuchsia-100 bg-fuchsia-50/60 p-4">
            <div class="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <strong class="text-sm font-bold text-fuchsia-900">용차 전환 회차 선택</strong>
                <p class="mt-1 text-xs text-fuchsia-700">정규 배송원은 용차로 처리할 회차를 복수 선택할 수 있습니다.</p>
              </div>
              <button type="button" class="self-start rounded-md border border-fuchsia-200 bg-white px-3 py-1.5 text-xs font-bold text-fuchsia-700 hover:bg-fuchsia-50" @click="clearYongchaGroupRoundSelection">
                선택 해제
              </button>
            </div>
            <div class="mt-3 grid grid-cols-1 gap-2 md:grid-cols-3">
              <label
                v-for="roundNo in [1, 2, 3]"
                :key="`group-round-select-${roundNo}`"
                class="cursor-pointer rounded-lg border bg-white p-3 transition"
                :class="yongchaGroupRoundSelection[roundNo] ? 'border-fuchsia-300 ring-2 ring-fuchsia-100' : 'border-gray-200 hover:border-fuchsia-200'"
              >
                <div class="flex items-center gap-2">
                  <input v-model="yongchaGroupRoundSelection[roundNo]" type="checkbox" class="h-4 w-4 rounded border-gray-300 text-primary" />
                  <span class="font-bold text-gray-900">{{ roundNo }}회차</span>
                </div>
                <p class="mt-2 text-xs leading-5 text-gray-600">{{ selectedYongchaGroupRoundSummary(roundNo) }}</p>
              </label>
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button @click="openYongchaGroupManagement" class="mr-auto px-5 py-3 border border-fuchsia-200 text-fuchsia-700 rounded-lg font-semibold hover:bg-fuchsia-50">용차팀 관리</button>
            <button @click="showYongchaPayGroupModal = false" class="px-5 py-3 border border-gray-300 rounded-lg hover:bg-gray-50">취소</button>
            <button @click="submitYongchaPayGroup" class="px-5 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">선택 적용</button>
          </div>
        </div>
      </div>

      <div v-if="groupMemberModal.show" class="fixed inset-0 z-[55] flex items-center justify-center bg-black/50 p-4">
        <div class="w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-xl">
          <div class="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-5">
            <div>
              <h3 class="text-xl font-bold text-text">{{ groupMemberModal.member?.name || '배송원' }} 정산 내역</h3>
              <p class="text-sm text-gray-500">{{ yongchaMonth }} 기준</p>
            </div>
            <button class="rounded-lg border border-gray-300 px-4 py-2 font-semibold hover:bg-gray-50" @click="groupMemberModal.show = false">닫기</button>
          </div>
          <div v-if="groupMemberModal.loading" class="px-6 py-12 text-center text-gray-500">불러오는 중...</div>
          <div v-else>
            <div class="grid grid-cols-2 gap-3 border-b border-gray-100 p-5 md:grid-cols-4">
              <div class="rounded-lg bg-gray-50 p-3">
                <p class="text-xs text-gray-500">총 지급액</p>
                <p class="font-extrabold text-primary">{{ formatCurrency(Number(groupMemberModal.totals.pay_amount || 0)) }}원</p>
              </div>
              <div class="rounded-lg bg-gray-50 p-3">
                <p class="text-xs text-gray-500">가구수</p>
                <p class="font-bold text-text">{{ Number(groupMemberModal.totals.households || 0).toLocaleString() }}</p>
              </div>
              <div class="rounded-lg bg-gray-50 p-3">
                <p class="text-xs text-gray-500">박스수</p>
                <p class="font-bold text-text">{{ Number(groupMemberModal.totals.boxes || 0).toLocaleString() }}</p>
              </div>
              <div class="rounded-lg bg-gray-50 p-3">
                <p class="text-xs text-gray-500">수신가격</p>
                <p class="font-bold text-blue-700">{{ formatCurrency(Number(groupMemberModal.totals.receive_amount || 0)) }}원</p>
              </div>
            </div>
            <div class="max-h-[55vh] overflow-y-auto">
              <table class="w-full text-sm">
                <thead class="sticky top-0 bg-white border-b border-gray-200">
                  <tr>
                    <th class="px-4 py-3 text-left font-semibold text-gray-600">날짜</th>
                    <th class="px-4 py-3 text-right font-semibold text-gray-600">가구수</th>
                    <th class="px-4 py-3 text-right font-semibold text-gray-600">박스수</th>
                    <th class="px-4 py-3 text-right font-semibold text-gray-600">지급액</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in groupMemberModal.rows" :key="`group-member-row-${row.date}`" class="border-b border-gray-100">
                    <td class="px-4 py-3 font-semibold">{{ row.date }}</td>
                    <td class="px-4 py-3 text-right">{{ Number(row.households || 0).toLocaleString() }}</td>
                    <td class="px-4 py-3 text-right">{{ Number(row.boxes || 0).toLocaleString() }}</td>
                    <td class="px-4 py-3 text-right font-bold text-primary">{{ formatCurrency(Number(row.pay_amount || 0)) }}원</td>
                  </tr>
                  <tr v-if="groupMemberModal.rows.length === 0">
                    <td colspan="4" class="px-4 py-10 text-center text-gray-400">정산 내역이 없습니다.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div v-if="historyConfirm.show" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4">
        <div class="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
          <h3 class="mb-3 text-lg font-bold text-text">과거 정산에도 반영하시겠습니까?</h3>
          <p class="text-sm leading-6 text-gray-600">
            예를 누르면 바뀐 단가로 과거 정산내역을 다시 계산합니다. 아니요를 누르면 이후 정산부터 반영됩니다.
          </p>
          <div class="mt-6 flex justify-end gap-3">
            <button @click="answerHistoryConfirm(false)" class="rounded-lg border border-gray-300 px-5 py-3 hover:bg-gray-50">아니요</button>
            <button @click="answerHistoryConfirm(true)" class="rounded-lg bg-primary px-5 py-3 font-medium text-white hover:opacity-90">예</button>
          </div>
        </div>
      </div>

      <CrewSettlementCalendarModal
        :show="crewCalendarModal.show"
        :crew="crewCalendarModal.crew"
        :month="crewCalendarModal.month"
        @close="closeCrewSettlementCalendar"
        @saved="handleCrewCalendarSaved"
      />
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, reactive, ref, watch } from 'vue'

import client from '@/api/client'
import {
  bulkSetYongchaPayGroup,
  convertToRegular,
  convertToYongcha,
  createYongchaPayGroup,
  deleteYongchaPayGroup,
  fetchYongchaPayGroups,
  fetchYongchaSummary,
  getCrewMonthlySettlement,
  getYongchaPayGroupSettlementSummary,
  setRegularFixedPay,
  setRoundYongcha,
  setYongchaPayGroup,
  updateYongchaPayGroup,
} from '@/api/crew'
import AppLayout from '@/components/common/AppLayout.vue'
import TeamFilter from '@/components/common/TeamFilter.vue'
import CrewSettlementCalendarModal from '@/components/settlement/CrewSettlementCalendarModal.vue'
import { useAuthStore } from '@/stores/auth'
import { useCrewStore } from '@/stores/crew'
import { formatCurrency } from '@/utils/format'

const hasYongchaPayGroupDetail = (detail) => {
  if (!detail || typeof detail !== 'object') return false
  return (
    Number(detail.base_pay || 0) > 0 ||
    Number(detail.base_households || 0) > 0 ||
    Number(detail.extra_household_pay || 0) > 0
  )
}

const renderYongchaPayGroupDetail = (detail) => {
  const basePay = Number(detail?.base_pay || 0)
  const baseHouseholds = Number(detail?.base_households || 0)
  const extraPay = Number(detail?.extra_household_pay || 0)
  const multiRoundPolicy = detail?.exclude_base_pay_on_multi_round ? ' / 다회차 기본급 미적용' : ''
  const title = `기본급 ${formatCurrency(basePay)}원 / 기준 ${baseHouseholds.toLocaleString()}가구 / 추가착당 ${formatCurrency(extraPay)}원${multiRoundPolicy}`
  return h('div', {
    class:
      'w-full max-w-[124px] rounded-md border border-fuchsia-100 bg-fuchsia-50 px-2 py-1 text-left text-[11px] font-semibold leading-4 text-fuchsia-800',
    title,
  }, [
    h('div', { class: 'whitespace-nowrap' }, `기본급 ${formatCurrency(basePay)}원`),
    h('div', { class: 'whitespace-nowrap' }, `기준 ${baseHouseholds.toLocaleString()}가구`),
    h('div', { class: 'whitespace-nowrap' }, `추가착당 ${formatCurrency(extraPay)}원`),
    detail?.exclude_base_pay_on_multi_round
      ? h('div', { class: 'whitespace-nowrap text-amber-700' }, '다회차 기본급 제외')
      : null,
  ])
}

const RoundPriceCell = defineComponent({
  props: {
    amount: { type: Number, required: true },
    active: { type: Boolean, required: true },
    groupName: { type: String, default: '' },
    groupDetail: { type: Object, default: null },
  },
  emits: ['toggle', 'edit', 'group'],
  setup(props, { emit }) {
    return () => {
      const groupName = String(props.groupName || '').trim()
      const hasGroupDetail = hasYongchaPayGroupDetail(props.groupDetail)
      const hasGroup = Boolean(groupName || hasGroupDetail)
      return h('div', { class: 'flex flex-col items-center gap-1 text-center min-w-[86px]' }, [
        hasGroupDetail
          ? renderYongchaPayGroupDetail(props.groupDetail)
          : groupName
            ? h('div', { class: 'max-w-[96px] truncate font-extrabold text-fuchsia-700 text-sm', title: groupName }, groupName)
            : h('div', { class: 'font-bold text-fuchsia-700 text-xs whitespace-nowrap' }, `${formatCurrency(Number(props.amount || 0))}원`),
        props.active
          ? h('div', { class: 'grid grid-cols-2 gap-1 w-full' }, [
              h(
                'button',
                {
                  class: 'rounded-md border border-red-200 bg-red-50 px-2 py-1 text-[11px] font-bold text-red-600 hover:bg-red-100',
                  onClick: () => emit('toggle'),
                },
                '용차해제',
              ),
              h(
                'button',
                {
                  class: 'rounded-md border border-gray-200 bg-white px-2 py-1 text-[11px] font-bold text-gray-700 hover:bg-gray-50',
                  onClick: () => emit(hasGroup ? 'group' : 'edit'),
                },
                hasGroup ? '상세' : '단가',
              ),
            ])
          : h(
              'button',
              {
                class: 'rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-[11px] font-bold text-gray-600 hover:bg-gray-100',
                onClick: () => emit('toggle'),
              },
              '용차전환',
            ),
      ])
    }
  },
})

const InlineRateEditor = defineComponent({
  props: {
    amount: { type: Number, required: true },
    groupName: { type: String, default: '' },
    groupDetail: { type: Object, default: null },
  },
  emits: ['edit', 'group'],
  setup(props, { emit }) {
    return () => {
      const groupName = String(props.groupName || '').trim()
      const hasGroupDetail = hasYongchaPayGroupDetail(props.groupDetail)
      const hasGroup = Boolean(groupName || hasGroupDetail)
      return h('div', { class: 'flex flex-col items-center gap-1 text-center min-w-[82px]' }, [
        hasGroupDetail
          ? renderYongchaPayGroupDetail(props.groupDetail)
          : groupName
            ? h('div', { class: 'max-w-[96px] truncate font-extrabold text-fuchsia-700 text-sm', title: groupName }, groupName)
            : h('div', { class: 'font-bold text-fuchsia-700 text-xs whitespace-nowrap' }, `${formatCurrency(Number(props.amount || 0))}원`),
        h(
          'button',
          {
            class: 'rounded-md border border-gray-200 bg-white px-2 py-1 text-[11px] font-bold text-gray-700 hover:bg-gray-50',
            onClick: (event) => {
              event.stopPropagation()
              emit(hasGroup ? 'group' : 'edit')
            },
          },
          hasGroup ? '상세' : '수정',
        ),
      ])
    }
  },
})

const PaginationButtons = defineComponent({
  props: {
    page: { type: Number, required: true },
    pages: { type: Array, required: true },
    totalPages: { type: Number, required: true },
  },
  emits: ['change'],
  setup(props, { emit }) {
    return () =>
      h('div', { class: 'flex gap-2' }, [
        h(
          'button',
          {
            class: 'px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-30',
            disabled: props.page === 1,
            onClick: () => emit('change', Math.max(1, props.page - 1)),
          },
          '이전',
        ),
        ...props.pages.map((p) =>
          h(
            'button',
            {
              class: `px-4 py-2 rounded-lg font-medium ${
                p === props.page ? 'bg-primary text-white' : 'border border-gray-300 hover:bg-gray-50'
              }`,
              onClick: () => emit('change', p),
            },
            String(p),
          ),
        ),
        h(
          'button',
          {
            class: 'px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-30',
            disabled: props.page === props.totalPages,
            onClick: () => emit('change', Math.min(props.totalPages, props.page + 1)),
          },
          '다음',
        ),
      ])
  },
})

const CREW_SYNC_EVENT = 'cheonha:crew-updated'

const authStore = useAuthStore()
const crewStore = useCrewStore()

const activeTab = ref('regular')
const searchQuery = ref('')
const selectedTeamName = ref('')

const regularPage = ref(1)
const yongchaPage = ref(1)
const regularMonth = ref(new Date().toISOString().slice(0, 7))
const yongchaMonth = ref(new Date().toISOString().slice(0, 7))
const pageSize = 20

const regularCount = ref(0)
const regularTotalPages = ref(1)
const yongchaCount = ref(0)
const yongchaTotalPages = ref(1)
const yongchaList = ref([])
const selectedYongcha = ref(null)
const yongchaDaily = ref([])
const yongchaLoading = ref(false)
const selectedCrewSettlement = ref(null)
const crewSettlementRows = ref([])
const crewSettlementTotals = ref({ households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 })
const crewSettlementLoading = ref(false)
const expandedSettlementDates = ref({})
const yongchaBulkMode = ref(false)
const yongchaBulkSelections = reactive({})

const selectedYongchaGroup = ref(null)
const yongchaGroupSettlementLoading = ref(false)
const yongchaGroupSettlementPage = ref(1)
const yongchaGroupSettlement = ref({
  totals: { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 },
  daily: { count: 0, page: 1, page_size: 10, total_pages: 1, results: [] },
  members: [],
})
const groupMemberModal = reactive({
  show: false,
  member: null,
  loading: false,
  rows: [],
  totals: { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 },
})

const showEditModal = ref(false)
const editingId = ref(null)
const originalPayPrice = ref(0)
const crewForm = reactive({
  name: '',
  phone: '',
  vehicle_number: '',
  bank_name: '',
  bank_account_number: '',
  bank_account_holder: '',
  vehicle_inspection_date: '',
  pay_price: 0,
})

const showRoundModal = ref(false)
const roundModalForm = reactive({
  memberId: null,
  roundNo: 1,
  amount: 0,
  mode: 'regular-edit',
  memberName: '',
})

const showConvertModal = ref(false)
const convertingMember = ref(null)
const convertForm = reactive({
  round1: 3000,
  round2: 3000,
  round3: 3000,
})
const showFixedPayModal = ref(false)
const fixedPayForm = reactive({
  memberId: null,
  memberName: '',
  round1: 0,
  round2: 0,
  round3: 0,
})
const showYongchaPayGroupModal = ref(false)
const showYongchaGroupEditorModal = ref(false)
const yongchaPayGroups = ref([])
const yongchaGroupLoading = ref(false)
const yongchaGroupSaving = ref(false)
const yongchaGroupTargetMember = ref(null)
const yongchaGroupSelectedId = ref('')
const yongchaGroupRoundSelection = reactive({
  1: false,
  2: false,
  3: false,
})
const yongchaGroupEditingId = ref(null)
const yongchaGroupForm = reactive({
  name: '',
  round_1_base_pay: 0,
  round_1_base_households: 0,
  round_1_extra_household_pay: 0,
  round_2_base_pay: 0,
  round_2_base_households: 0,
  round_2_extra_household_pay: 0,
  round_3_base_pay: 0,
  round_3_base_households: 0,
  round_3_extra_household_pay: 0,
  exclude_base_pay_on_multi_round: false,
})
const historyConfirm = reactive({
  show: false,
  resolve: null,
})
const crewCalendarModal = reactive({
  show: false,
  crew: null,
  month: '',
})

const regularRows = computed(() => crewStore.crewMembers)
const yongchaRows = computed(() => yongchaList.value)
const yongchaBulkSelectedRows = computed(() => Object.values(yongchaBulkSelections))
const yongchaGroupDailyRows = computed(() => yongchaGroupSettlement.value?.daily?.results || [])
const yongchaGroupDailyTotalPages = computed(() => Number(yongchaGroupSettlement.value?.daily?.total_pages || 1))
const yongchaGroupDailyVisiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, yongchaGroupSettlementPage.value - 2)
  for (let i = start; i <= Math.min(yongchaGroupDailyTotalPages.value, start + 4); i += 1) pages.push(i)
  return pages
})

const regularVisiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, regularPage.value - 2)
  for (let i = start; i <= Math.min(regularTotalPages.value, start + 4); i += 1) pages.push(i)
  return pages
})

const yongchaVisiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, yongchaPage.value - 2)
  for (let i = start; i <= Math.min(yongchaTotalPages.value, start + 4); i += 1) pages.push(i)
  return pages
})

const roundModalTitle = computed(() => {
  if (roundModalForm.mode === 'yongcha-edit') {
    return `${roundModalForm.memberName} ${roundModalForm.roundNo}회차 용차 단가 수정`
  }
  return `${roundModalForm.memberName} ${roundModalForm.roundNo}회차 용차 전환`
})

const roundModalDescription = computed(() => {
  if (roundModalForm.mode === 'yongcha-edit') {
    return '조 관리 기본값을 기반으로 배송원별 단가를 따로 적용합니다.'
  }
  return '조 관리 기본값을 불러왔습니다. 필요하면 이 배송원만 따로 수정할 수 있습니다.'
})

const isRegularYongchaGroupTarget = computed(() =>
  yongchaGroupTargetMember.value?.is_yongcha === false,
)

const selectedYongchaPayGroup = computed(() =>
  yongchaPayGroups.value.find((group) => String(group.id) === String(yongchaGroupSelectedId.value)) || null,
)

const selectedYongchaGroupRoundSummary = (roundNo) => {
  const group = selectedYongchaPayGroup.value
  if (!group) {
    return '개인/조별 가구당 단가를 사용합니다.'
  }
  const basePay = Number(group[`round_${roundNo}_base_pay`] || 0)
  const baseHouseholds = Number(group[`round_${roundNo}_base_households`] || 0)
  const extraPay = Number(group[`round_${roundNo}_extra_household_pay`] || 0)
  if (basePay <= 0 && baseHouseholds <= 0 && extraPay <= 0) {
    return '이 회차의 용차팀 조건이 없어 개인/조별 단가를 사용합니다.'
  }
  return `기본급 ${formatCurrency(basePay)}원 · 기준 ${baseHouseholds.toLocaleString()}가구 · 추가착당 ${formatCurrency(extraPay)}원`
}

const yongchaStatusMark = (row = {}) => {
  if (row.is_yongcha_label === '혼합') return 'O/X'
  return row.is_yongcha ? 'O' : 'X'
}

const settlementDateKey = (row = {}) => `${selectedCrewSettlement.value?.id || 'crew'}:${row.date || ''}`

const isSettlementDateExpanded = (row = {}) => Boolean(expandedSettlementDates.value[settlementDateKey(row)])

const toggleSettlementDate = (row = {}) => {
  if (!row.date) return
  const key = settlementDateKey(row)
  expandedSettlementDates.value = {
    ...expandedSettlementDates.value,
    [key]: !expandedSettlementDates.value[key],
  }
}

const clearYongchaGroupRoundSelection = () => {
  for (const roundNo of [1, 2, 3]) {
    yongchaGroupRoundSelection[roundNo] = false
  }
}

const currentSettlementMonth = () => (activeTab.value === 'regular' ? regularMonth.value : yongchaMonth.value)

const openCrewSettlementCalendar = (member, month = currentSettlementMonth()) => {
  crewCalendarModal.crew = member
  crewCalendarModal.month = month || currentSettlementMonth()
  crewCalendarModal.show = true
  if (member?.is_yongcha) selectedYongcha.value = member
}

const closeCrewSettlementCalendar = () => {
  crewCalendarModal.show = false
}

const handleCrewCalendarSaved = async () => {
  await refreshAll({ silent: true })
}

const selectCrewSettlement = async (member, tab = activeTab.value) => {
  selectedCrewSettlement.value = member
  expandedSettlementDates.value = {}
  if (tab === 'yongcha') {
    selectedYongcha.value = member
  }
  crewSettlementLoading.value = true
  try {
    const response = await getCrewMonthlySettlement(member.id, {
      month: tab === 'regular' ? regularMonth.value : yongchaMonth.value,
    })
    crewSettlementRows.value = response.data?.results || []
    crewSettlementTotals.value = response.data?.totals || { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 }
  } catch {
    crewSettlementRows.value = []
    crewSettlementTotals.value = { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 }
  } finally {
    crewSettlementLoading.value = false
  }
}

const clearBulkSelections = () => {
  for (const key of Object.keys(yongchaBulkSelections)) {
    delete yongchaBulkSelections[key]
  }
}

const toggleYongchaBulkMode = async () => {
  yongchaBulkMode.value = !yongchaBulkMode.value
  if (yongchaBulkMode.value) {
    selectedCrewSettlement.value = null
    crewSettlementRows.value = []
    await loadYongchaPayGroups()
  } else {
    clearBulkSelections()
  }
}

const toggleBulkSelection = (member, checked) => {
  if (!checked) {
    delete yongchaBulkSelections[member.id]
    return
  }
  yongchaBulkSelections[member.id] = {
    member,
    groupId: member.yongcha_pay_group || '',
  }
}

const setBulkSelectionGroup = (member, groupId) => {
  if (!yongchaBulkSelections[member.id]) {
    toggleBulkSelection(member, true)
  }
  yongchaBulkSelections[member.id].groupId = groupId || ''
}

const bulkSelectionGroupId = (member) => (
  yongchaBulkSelections[member.id]?.groupId ?? member.yongcha_pay_group ?? ''
)

const bulkGroupName = (groupId) => {
  if (!groupId) return '개인/조별 단가'
  const group = yongchaPayGroups.value.find((item) => String(item.id) === String(groupId))
  return group?.name || '선택한 용차팀'
}

const removeBulkSelection = (memberId) => {
  delete yongchaBulkSelections[memberId]
}

const submitBulkYongchaPayGroups = async () => {
  const rows = yongchaBulkSelectedRows.value
  if (rows.length === 0) return
  try {
    const applyHistory = await confirmApplyHistory()
    await bulkSetYongchaPayGroup({
      apply_history: applyHistory,
      assignments: rows.map((item) => ({
        crew_member_id: item.member.id,
        yongcha_pay_group: item.groupId || null,
      })),
    })
    clearBulkSelections()
    yongchaBulkMode.value = false
    notifyCrewChanged()
    await loadYongcha({ silent: false })
  } catch (error) {
    alert(error?.response?.data?.detail || '용차팀 일괄 변경에 실패했습니다.')
  }
}

const loadYongchaGroupSettlement = async () => {
  if (!selectedYongchaGroup.value) return
  yongchaGroupSettlementLoading.value = true
  try {
    const response = await getYongchaPayGroupSettlementSummary(selectedYongchaGroup.value.id, {
      month: yongchaMonth.value || undefined,
      page: yongchaGroupSettlementPage.value,
      page_size: 10,
    })
    yongchaGroupSettlement.value = response.data || {
      totals: { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 },
      daily: { count: 0, page: 1, page_size: 10, total_pages: 1, results: [] },
      members: [],
    }
  } catch {
    yongchaGroupSettlement.value = {
      totals: { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 },
      daily: { count: 0, page: 1, page_size: 10, total_pages: 1, results: [] },
      members: [],
    }
  } finally {
    yongchaGroupSettlementLoading.value = false
  }
}

const selectYongchaGroup = async (group) => {
  selectedYongchaGroup.value = group
  yongchaGroupSettlementPage.value = 1
  await loadYongchaGroupSettlement()
}

const changeYongchaGroupSettlementPage = async (page) => {
  yongchaGroupSettlementPage.value = page
  await loadYongchaGroupSettlement()
}

const openGroupMemberSettlement = async (member) => {
  groupMemberModal.show = true
  groupMemberModal.member = member
  groupMemberModal.loading = true
  groupMemberModal.rows = []
  groupMemberModal.totals = { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 }
  try {
    const response = await getCrewMonthlySettlement(member.id, { month: yongchaMonth.value || undefined })
    groupMemberModal.rows = response.data?.results || []
    groupMemberModal.totals = response.data?.totals || groupMemberModal.totals
  } catch {
    groupMemberModal.rows = []
  } finally {
    groupMemberModal.loading = false
  }
}

const notifyCrewChanged = () => {
  const value = String(Date.now())
  try {
    window.localStorage.setItem(CREW_SYNC_EVENT, value)
  } catch {}
  window.dispatchEvent(new CustomEvent(CREW_SYNC_EVENT, { detail: value }))
}

const resetPages = () => {
  regularPage.value = 1
  yongchaPage.value = 1
}

const refreshCrew = async (options = {}) => {
  if (
    showEditModal.value ||
    showRoundModal.value ||
    showConvertModal.value ||
    showFixedPayModal.value ||
    showYongchaPayGroupModal.value ||
    showYongchaGroupEditorModal.value
  ) return
  if (document.visibilityState === 'hidden') return
  const response = await crewStore.fetchCrew(
    {
      is_yongcha: false,
      team_name: selectedTeamName.value || undefined,
      search: searchQuery.value || undefined,
      page: regularPage.value,
      page_size: pageSize,
    },
    { silent: options.silent ?? crewStore.crewMembers.length > 0 },
  )
  const payload = response?.data || {}
  regularCount.value = Number(payload.count || regularRows.value.length || 0)
  regularTotalPages.value = Number(payload.total_pages || 1)
}

const loadYongcha = async (options = {}) => {
  try {
    const response = await fetchYongchaSummary({
      page: yongchaPage.value,
      page_size: pageSize,
      search: searchQuery.value || undefined,
      team_name: selectedTeamName.value || undefined,
      month: yongchaMonth.value || undefined,
    })
    const payload = response.data || {}
    yongchaList.value = payload.results || payload || []
    yongchaCount.value = Number(payload.count || yongchaList.value.length || 0)
    yongchaTotalPages.value = Number(payload.total_pages || 1)
    if (selectedYongcha.value) {
      const updated = yongchaList.value.find((item) => item.id === selectedYongcha.value.id)
      selectedYongcha.value = updated || null
      if (updated) {
        selectedCrewSettlement.value = updated
        await selectYongcha(updated, false, options)
      }
    }
  } catch (error) {
    if (!options.silent) {
      yongchaList.value = []
      yongchaCount.value = 0
      yongchaTotalPages.value = 1
    }
  }
}

const refreshAll = async (options = {}) => {
  await refreshCrew(options)
  if (activeTab.value === 'yongcha') {
    await loadYongcha(options)
  }
}

const selectYongcha = async (member, setSelected = true, options = {}) => {
  if (setSelected) selectedYongcha.value = member
  if (!options.silent) {
    await selectCrewSettlement(member, 'yongcha')
    return
  }
  try {
    const response = await getCrewMonthlySettlement(member.id, {
      month: yongchaMonth.value || undefined,
    })
    crewSettlementRows.value = response.data?.results || []
    crewSettlementTotals.value = response.data?.totals || { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 }
  } catch {
    if (!options.silent) crewSettlementRows.value = []
  }
}

const editCrew = (member) => {
  editingId.value = member.id
  crewForm.name = member.name || ''
  crewForm.phone = member.phone || ''
  crewForm.vehicle_number = member.vehicle_number || ''
  crewForm.bank_name = member.bank_name || ''
  crewForm.bank_account_number = member.bank_account_number || ''
  crewForm.bank_account_holder = member.bank_account_holder || ''
  crewForm.vehicle_inspection_date = member.vehicle_inspection_date || ''
  crewForm.pay_price = Number(member.pay_price || 0)
  originalPayPrice.value = Number(member.pay_price || 0)
  showEditModal.value = true
}

const confirmApplyHistory = () =>
  new Promise((resolve) => {
    historyConfirm.resolve = resolve
    historyConfirm.show = true
  })

const answerHistoryConfirm = (applyHistory) => {
  const resolve = historyConfirm.resolve
  historyConfirm.show = false
  historyConfirm.resolve = null
  if (resolve) resolve(applyHistory)
}

const submitEditCrew = async () => {
  try {
    await crewStore.updateCrew(editingId.value, {
      name: crewForm.name,
      phone: crewForm.phone,
      vehicle_number: crewForm.vehicle_number,
      bank_name: crewForm.bank_name,
      bank_account_number: crewForm.bank_account_number,
      bank_account_holder: crewForm.bank_account_holder,
      vehicle_inspection_date: crewForm.vehicle_inspection_date || null,
      pay_price: crewForm.pay_price || 0,
    })
    if (Number(crewForm.pay_price) !== Number(originalPayPrice.value)) {
      if (await confirmApplyHistory()) {
        await client.post(`/crew/members/${editingId.value}/recalc_settlements/`)
      }
    }
    showEditModal.value = false
    notifyCrewChanged()
    await refreshCrew({ silent: true })
  } catch (error) {
    alert(error?.response?.data?.detail || '배송원 수정에 실패했습니다.')
  }
}

const deleteCrew = async (member) => {
  if (!window.confirm(`${member.name} 배송원을 삭제할까요?`)) return
  try {
    await crewStore.removeCrew(member.id)
    notifyCrewChanged()
  } catch {
    alert('배송원 삭제에 실패했습니다.')
  }
}

const deleteYongcha = async (member) => {
  if (!window.confirm(`${member.name} 용차 인원을 삭제할까요?`)) return
  try {
    await crewStore.removeCrew(member.id)
    notifyCrewChanged()
    await loadYongcha({ silent: true })
  } catch {
    alert('용차 인원 삭제에 실패했습니다.')
  }
}

const openRegularRoundEdit = (member, roundNo) => {
  roundModalForm.memberId = member.id
  roundModalForm.memberName = member.name
  roundModalForm.roundNo = roundNo
  roundModalForm.mode = 'regular-edit'
  roundModalForm.amount = Number(member[`regular_round_${roundNo}_display_pay_price`] || 3000)
  showRoundModal.value = true
}

const openYongchaRoundEdit = (member, roundNo) => {
  roundModalForm.memberId = member.id
  roundModalForm.memberName = member.name
  roundModalForm.roundNo = roundNo
  roundModalForm.mode = 'yongcha-edit'
  roundModalForm.amount = Number(member[`yongcha_round_${roundNo}_display_pay_price`] || 3000)
  showRoundModal.value = true
}

const handleRegularRoundToggle = async (member, roundNo) => {
  const fieldName = `round_${roundNo}_is_yongcha`
  if (member[fieldName]) {
    if (!window.confirm(`${member.name} ${roundNo}회차 용차 전환을 해제할까요?`)) return
    const applyHistory = await confirmApplyHistory()
    try {
      await setRoundYongcha(member.id, {
        round_no: roundNo,
        is_yongcha: false,
        apply_history: applyHistory,
      })
      notifyCrewChanged()
      await refreshCrew({ silent: true })
      if (activeTab.value === 'yongcha') await loadYongcha({ silent: true })
    } catch (error) {
      alert(error?.response?.data?.detail || `${roundNo}회차 용차 해제에 실패했습니다.`)
    }
    return
  }
  roundModalForm.memberId = member.id
  roundModalForm.memberName = member.name
  roundModalForm.roundNo = roundNo
  roundModalForm.mode = 'regular-toggle'
  roundModalForm.amount = Number(member[`regular_round_${roundNo}_display_pay_price`] || 3000)
  showRoundModal.value = true
}

const submitRoundModal = async () => {
  const amount = Number(roundModalForm.amount || 0)
  if (Number.isNaN(amount) || amount < 0) {
    alert('단가는 0 이상의 숫자여야 합니다.')
    return
  }
  try {
    const applyHistory = await confirmApplyHistory()
    if (roundModalForm.mode === 'yongcha-edit') {
      await crewStore.updateCrew(roundModalForm.memberId, {
        [`personal_round_${roundModalForm.roundNo}_yongcha_pay_price`]: amount,
      })
      if (applyHistory) {
        await client.post(`/crew/members/${roundModalForm.memberId}/recalc_settlements/`)
      }
    } else {
      await setRoundYongcha(roundModalForm.memberId, {
        round_no: roundModalForm.roundNo,
        is_yongcha: true,
        round_pay_price: amount,
        apply_history: applyHistory,
      })
    }
    showRoundModal.value = false
    notifyCrewChanged()
    await refreshCrew({ silent: true })
    await loadYongcha({ silent: true })
  } catch (error) {
    alert(error?.response?.data?.detail || '용차 단가 반영에 실패했습니다.')
  }
}

const openConvertYongchaModal = (member) => {
  convertingMember.value = member
  convertForm.round1 = Number(member.yongcha_round_1_display_pay_price || 3000)
  convertForm.round2 = Number(member.yongcha_round_2_display_pay_price || 3000)
  convertForm.round3 = Number(member.yongcha_round_3_display_pay_price || 3000)
  showConvertModal.value = true
}

const submitConvertYongcha = async () => {
  if (!convertingMember.value) return
  try {
    const applyHistory = await confirmApplyHistory()
    await convertToYongcha(convertingMember.value.id, {
      apply_history: applyHistory,
      personal_round_1_yongcha_pay_price: Number(convertForm.round1 || 0),
      personal_round_2_yongcha_pay_price: Number(convertForm.round2 || 0),
      personal_round_3_yongcha_pay_price: Number(convertForm.round3 || 0),
    })
    showConvertModal.value = false
    activeTab.value = 'yongcha'
    selectedYongcha.value = null
    yongchaDaily.value = []
    notifyCrewChanged()
    await refreshCrew({ silent: true })
    await loadYongcha({ silent: false })
  } catch (error) {
    alert(error?.response?.data?.detail || '용차 전환에 실패했습니다.')
  }
}

const openFixedPayModal = (member) => {
  fixedPayForm.memberId = member.id
  fixedPayForm.memberName = member.name || ''
  fixedPayForm.round1 = Number(member.regular_round_1_base_pay || 0)
  fixedPayForm.round2 = Number(member.regular_round_2_base_pay || 0)
  fixedPayForm.round3 = Number(member.regular_round_3_base_pay || 0)
  showFixedPayModal.value = true
}

const submitFixedPay = async () => {
  const values = [fixedPayForm.round1, fixedPayForm.round2, fixedPayForm.round3].map((value) => Number(value || 0))
  if (values.some((value) => Number.isNaN(value) || value < 0)) {
    alert('기본급은 0 이상의 숫자여야 합니다.')
    return
  }
  try {
    const applyHistory = await confirmApplyHistory()
    await setRegularFixedPay(fixedPayForm.memberId, {
      round_1_base_pay: values[0],
      round_2_base_pay: values[1],
      round_3_base_pay: values[2],
      apply_history: applyHistory,
    })
    showFixedPayModal.value = false
    notifyCrewChanged()
    await refreshCrew({ silent: true })
  } catch (error) {
    alert(error?.response?.data?.detail || '기본급 설정에 실패했습니다.')
  }
}

const normalizeNonNegativeInteger = (value) => {
  if (value === '' || value === null || value === undefined) return 0
  const number = Number(value)
  if (!Number.isFinite(number)) return Number.NaN
  return Math.max(0, Math.round(number))
}

const resetYongchaGroupForm = () => {
  yongchaGroupEditingId.value = null
  yongchaGroupForm.name = ''
  yongchaGroupForm.exclude_base_pay_on_multi_round = false
  for (const roundNo of [1, 2, 3]) {
    yongchaGroupForm[`round_${roundNo}_base_pay`] = 0
    yongchaGroupForm[`round_${roundNo}_base_households`] = 0
    yongchaGroupForm[`round_${roundNo}_extra_household_pay`] = 0
  }
}

const buildYongchaGroupPayload = () => {
  const payload = {
    name: String(yongchaGroupForm.name || '').trim(),
    exclude_base_pay_on_multi_round: Boolean(yongchaGroupForm.exclude_base_pay_on_multi_round),
  }
  for (const roundNo of [1, 2, 3]) {
    payload[`round_${roundNo}_base_pay`] = normalizeNonNegativeInteger(yongchaGroupForm[`round_${roundNo}_base_pay`])
    payload[`round_${roundNo}_base_households`] = normalizeNonNegativeInteger(yongchaGroupForm[`round_${roundNo}_base_households`])
    payload[`round_${roundNo}_extra_household_pay`] = normalizeNonNegativeInteger(yongchaGroupForm[`round_${roundNo}_extra_household_pay`])
  }
  return payload
}

const getApiErrorMessage = (error, fallback) => {
  const data = error?.response?.data
  if (!data) return fallback
  if (typeof data.detail === 'string') return data.detail
  const values = Object.values(data)
  const firstFieldError = typeof values.flat === 'function' ? values.flat()[0] : values[0]
  return typeof firstFieldError === 'string' ? firstFieldError : fallback
}

const loadYongchaPayGroups = async () => {
  yongchaGroupLoading.value = true
  try {
    const response = await fetchYongchaPayGroups({ is_active: true })
    yongchaPayGroups.value = response.data.results || response.data || []
  } catch {
    yongchaPayGroups.value = []
  } finally {
    yongchaGroupLoading.value = false
  }
}

const openYongchaPayGroupModal = async (member) => {
  yongchaGroupTargetMember.value = member
  yongchaGroupSelectedId.value = member.yongcha_pay_group || ''
  yongchaGroupRoundSelection[1] = Boolean(member.round_1_is_yongcha)
  yongchaGroupRoundSelection[2] = Boolean(member.round_2_is_yongcha)
  yongchaGroupRoundSelection[3] = Boolean(member.round_3_is_yongcha)
  resetYongchaGroupForm()
  showYongchaPayGroupModal.value = true
  await loadYongchaPayGroups()
}

const openYongchaGroupManagement = async () => {
  showYongchaPayGroupModal.value = false
  yongchaGroupTargetMember.value = null
  yongchaGroupSelectedId.value = ''
  showYongchaGroupEditorModal.value = false
  activeTab.value = 'yongchaGroups'
  await loadYongchaPayGroups()
}

const openNewYongchaPayGroup = () => {
  resetYongchaGroupForm()
  showYongchaGroupEditorModal.value = true
}

const startEditYongchaPayGroup = (group) => {
  yongchaGroupEditingId.value = group.id
  yongchaGroupForm.name = group.name || ''
  yongchaGroupForm.exclude_base_pay_on_multi_round = Boolean(group.exclude_base_pay_on_multi_round)
  for (const roundNo of [1, 2, 3]) {
    yongchaGroupForm[`round_${roundNo}_base_pay`] = normalizeNonNegativeInteger(group[`round_${roundNo}_base_pay`])
    yongchaGroupForm[`round_${roundNo}_base_households`] = normalizeNonNegativeInteger(group[`round_${roundNo}_base_households`])
    yongchaGroupForm[`round_${roundNo}_extra_household_pay`] = normalizeNonNegativeInteger(group[`round_${roundNo}_extra_household_pay`])
  }
  showYongchaGroupEditorModal.value = true
}

const cancelYongchaGroupEdit = () => {
  showYongchaGroupEditorModal.value = false
  resetYongchaGroupForm()
}

const submitSaveYongchaPayGroup = async () => {
  const payload = buildYongchaGroupPayload()
  if (!payload.name) {
    alert('용차 팀 이름을 입력하세요.')
    return
  }
  if (Object.keys(payload).some((key) => !['name', 'exclude_base_pay_on_multi_round'].includes(key) && (!Number.isFinite(payload[key]) || payload[key] < 0))) {
    alert('단가와 기준 가구수는 0 이상의 숫자여야 합니다.')
    return
  }
  yongchaGroupSaving.value = true
  try {
    const editingId = yongchaGroupEditingId.value
    const response = editingId
      ? await updateYongchaPayGroup(editingId, payload)
      : await createYongchaPayGroup(payload)
    resetYongchaGroupForm()
    await loadYongchaPayGroups()
    if (selectedYongchaGroup.value?.id === editingId) {
      const updated = yongchaPayGroups.value.find((group) => group.id === editingId)
      if (updated) {
        selectedYongchaGroup.value = updated
        await loadYongchaGroupSettlement()
      }
    }
    yongchaGroupSelectedId.value = response.data?.id || editingId || ''
    showYongchaGroupEditorModal.value = false
  } catch (error) {
    alert(getApiErrorMessage(error, yongchaGroupEditingId.value ? '용차 팀 수정에 실패했습니다.' : '용차 팀 추가에 실패했습니다.'))
  } finally {
    yongchaGroupSaving.value = false
  }
}

const removeYongchaPayGroup = async (group) => {
  if (!window.confirm(`${group.name} 용차팀을 삭제할까요?\n이미 적용된 배송원은 개인/조별 가구당 단가로 돌아갑니다.`)) return
  yongchaGroupSaving.value = true
  try {
    await deleteYongchaPayGroup(group.id)
    if (selectedYongchaGroup.value?.id === group.id) {
      selectedYongchaGroup.value = null
      yongchaGroupSettlement.value = {
        totals: { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 },
        daily: { count: 0, page: 1, page_size: 10, total_pages: 1, results: [] },
        members: [],
      }
    }
    if (String(yongchaGroupSelectedId.value) === String(group.id)) {
      yongchaGroupSelectedId.value = ''
    }
    if (String(yongchaGroupEditingId.value) === String(group.id)) {
      resetYongchaGroupForm()
    }
    await loadYongchaPayGroups()
    notifyCrewChanged()
  } catch (error) {
    alert(getApiErrorMessage(error, '용차 팀 삭제에 실패했습니다.'))
  } finally {
    yongchaGroupSaving.value = false
  }
}

const submitYongchaPayGroup = async () => {
  if (!yongchaGroupTargetMember.value) return
  try {
    const selectedRounds = [1, 2, 3].filter((roundNo) => yongchaGroupRoundSelection[roundNo])
    if (isRegularYongchaGroupTarget.value && yongchaGroupSelectedId.value && selectedRounds.length === 0) {
      alert('용차팀을 적용할 회차를 1개 이상 선택하세요.')
      return
    }
    const applyHistory = await confirmApplyHistory()
    const payload = {
      yongcha_pay_group: yongchaGroupSelectedId.value || null,
      apply_history: applyHistory,
    }
    if (isRegularYongchaGroupTarget.value) {
      payload.round_yongcha_numbers = selectedRounds
    }
    await setYongchaPayGroup(yongchaGroupTargetMember.value.id, payload)
    showYongchaPayGroupModal.value = false
    notifyCrewChanged()
    await refreshCrew({ silent: true })
    await loadYongcha({ silent: true })
  } catch (error) {
    alert(error?.response?.data?.detail || '용차팀 적용에 실패했습니다.')
  }
}

const convertYongcha = async (member) => {
  const input = window.prompt(`${member.name} 배송원을 정규로 전환합니다.\n박스당 지급단가를 입력하세요.`, member.pay_price || '')
  if (input === null) return
  const payPrice = Number(input || 0)
  if (Number.isNaN(payPrice) || payPrice < 0) {
    alert('지급단가는 0 이상의 숫자여야 합니다.')
    return
  }
  try {
    const applyHistory = await confirmApplyHistory()
    await convertToRegular(member.id, {
      pay_price: payPrice,
      apply_history: applyHistory,
    })
    selectedYongcha.value = null
    yongchaDaily.value = []
    notifyCrewChanged()
    await refreshCrew({ silent: true })
    await loadYongcha({ silent: false })
    if (yongchaList.value.length === 0 && yongchaPage.value > 1) {
      yongchaPage.value -= 1
      await loadYongcha({ silent: false })
    }
  } catch (error) {
    alert(error?.response?.data?.detail || '정규 전환에 실패했습니다.')
  }
}

watch([searchQuery, selectedTeamName, activeTab], async () => {
  resetPages()
  if (activeTab.value === 'yongcha') {
    await loadYongcha({ silent: false })
  } else if (activeTab.value === 'yongchaGroups') {
    await loadYongchaPayGroups()
  } else {
    await refreshCrew({ silent: false })
  }
})

watch(regularPage, async () => {
  if (activeTab.value === 'regular') await refreshCrew({ silent: true })
})

watch(yongchaPage, async () => {
  if (activeTab.value === 'yongcha') await loadYongcha({ silent: true })
})

watch(yongchaMonth, async () => {
  yongchaPage.value = 1
  if (activeTab.value === 'yongcha') {
    await loadYongcha({ silent: false })
    if (selectedCrewSettlement.value?.id) {
      await selectCrewSettlement(selectedCrewSettlement.value, 'yongcha')
    }
  }
  if (activeTab.value === 'yongchaGroups' && selectedYongchaGroup.value) {
    yongchaGroupSettlementPage.value = 1
    await loadYongchaGroupSettlement()
  }
})

watch(regularMonth, async () => {
  if (activeTab.value === 'regular' && selectedCrewSettlement.value?.id) {
    await selectCrewSettlement(selectedCrewSettlement.value, 'regular')
  }
})

onMounted(async () => {
  await refreshAll({ silent: false })
})
</script>
