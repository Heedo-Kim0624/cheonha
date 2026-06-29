<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- 스텝 진행바 -->
      <div v-if="!isOneShipper" class="bg-white rounded-xl p-5 border border-gray-200">
        <div class="flex items-center justify-between">
          <div v-for="(step, idx) in stepLabels" :key="idx"
            class="flex items-center" :class="idx < stepLabels.length - 1 ? 'flex-1' : ''">
            <div class="flex items-center gap-3 cursor-pointer" @click="goToStep(idx)">
              <div class="w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all"
                :class="idx < currentStep ? 'bg-success text-white'
                  : idx === currentStep ? 'bg-primary text-white'
                  : 'bg-gray-200 text-gray-500'">
                <span v-if="idx < currentStep">&#10003;</span>
                <span v-else>{{ idx + 1 }}</span>
              </div>
              <span class="font-medium whitespace-nowrap"
                :class="idx <= currentStep ? 'text-text' : 'text-gray-400'">
                {{ step }}
              </span>
            </div>
            <div v-if="idx < stepLabels.length - 1"
              class="flex-1 h-0.5 mx-4 rounded"
              :class="idx < currentStep ? 'bg-success' : 'bg-gray-200'"></div>
          </div>
        </div>
      </div>

      <!-- ============ STEP 0: 파일 업로드 ============ -->
      <div v-if="currentStep === 0" class="bg-white rounded-xl p-8 border border-gray-200">
        <h3 class="text-xl font-bold text-text mb-2">배차 파일 업로드</h3>
        <p class="text-gray-500 mb-6">배차현황 엑셀 파일을 업로드하면 자동으로 팀과 배송원 정보를 분석합니다.</p>

        <div class="mb-5 grid gap-3 md:grid-cols-[220px,1fr]">
          <label class="block">
            <span class="mb-1 block text-sm font-semibold text-gray-600">화주사</span>
            <select v-model="selectedShipper" class="w-full rounded-lg border border-gray-300 px-3 py-2 font-semibold text-text">
              <option v-for="shipper in shipperOptions" :key="shipper.code" :value="shipper.code">
                {{ shipper.name }}
              </option>
            </select>
          </label>
          <div class="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
            <span v-if="isTextUploadMode">텍스트를 붙여넣으면 아래 미리보기에서 건수와 가구수를 확인한 뒤 저장합니다.</span>
            <span v-else-if="isFileUploadMode">기존 컬리 Excel 업로드 방식 그대로 사용합니다.</span>
            <span v-else>이 화주사의 배차표 업로드 로직은 아직 연결되지 않았습니다.</span>
          </div>
        </div>

        <div v-if="isOneShipper" class="rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-900">
          <p class="text-lg font-extrabold">오네 정산은 정산 페이지에서 관리합니다.</p>
          <p class="mt-1 text-sm font-semibold">
            오네는 컬리/쿠팡 배차표 업로드 흐름과 다른 지급명세서 기준을 사용하므로, 좌측 메뉴의 오네 정산 화면에서 업로드와 검증을 진행합니다.
          </p>
          <RouterLink
            :to="`${getCompanyAppFromRoute(route).routeBase}/settlement`"
            class="mt-4 inline-flex rounded-lg bg-amber-700 px-4 py-2 font-bold text-white hover:bg-amber-600"
          >
            오네 정산으로 이동
          </RouterLink>
        </div>

        <div v-else-if="isTextUploadMode" class="space-y-4 rounded-xl border border-gray-200 p-5">
          <div class="grid gap-3 md:grid-cols-4">
            <label class="block">
              <span class="mb-1 block text-sm font-semibold text-gray-600">날짜 기준</span>
              <select v-model="textDateBasis" class="w-full rounded-lg border border-gray-300 px-3 py-2">
                <option value="delivery">배송일 기준</option>
                <option value="work">출근일 기준(+1일)</option>
              </select>
            </label>
            <label class="block">
              <span class="mb-1 block text-sm font-semibold text-gray-600">{{ textDateInputLabel }}</span>
              <input v-model="textDispatchDate" type="date" class="w-full rounded-lg border border-gray-300 px-3 py-2" />
              <span v-if="textDateBasis === 'work' && effectiveTextDispatchDate" class="mt-1 block text-xs font-semibold text-blue-600">
                배송일 {{ effectiveTextDispatchDate }}
              </span>
            </label>
            <label class="block">
              <span class="mb-1 block text-sm font-semibold text-gray-600">회차</span>
              <select v-model="textRoundCode" class="w-full rounded-lg border border-gray-300 px-3 py-2">
                <option v-for="round in coupangRoundOptions" :key="round.code" :value="round.code">
                  {{ round.label }}
                </option>
              </select>
            </label>
            <label class="block">
              <span class="mb-1 block text-sm font-semibold text-gray-600">조</span>
              <select v-model="textTeamId" class="w-full rounded-lg border border-gray-300 px-3 py-2">
                <option value="">조 선택</option>
                <option v-for="team in textTeams" :key="team.id" :value="String(team.id)">
                  {{ team.name }}
                </option>
              </select>
            </label>
          </div>

          <div class="flex flex-col gap-2 md:flex-row">
            <input v-model.trim="textNewTeamName" type="text" placeholder="쿠팡/송파1 같은 조 이름 입력"
              class="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2" />
            <button type="button" class="rounded-lg bg-gray-900 px-4 py-2 font-bold text-white" @click="createTextTeam">
              조 추가
            </button>
          </div>

          <textarea v-model="textRaw" rows="9" placeholder="쿠팡 공유 텍스트를 붙여넣으세요."
            class="w-full rounded-xl border border-gray-300 p-4 font-mono text-sm outline-none focus:border-primary"></textarea>

          <div v-if="textPreviewLoading" class="text-sm font-semibold text-primary">미리보기 생성 중...</div>
          <div v-if="textError" class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-danger">{{ textError }}</div>

          <div v-if="textPreview" class="rounded-xl border border-gray-200 overflow-hidden">
            <div class="flex flex-wrap items-center justify-between gap-3 bg-gray-50 px-4 py-3">
              <div class="font-bold text-text">미리보기 {{ textPreviewRows.length.toLocaleString() }}행</div>
              <div class="flex gap-2 text-sm font-semibold text-gray-700">
                <span>건수 {{ Number(textPreview.total_boxes || 0).toLocaleString() }}</span>
                <span>가구수 {{ Number(textPreview.total_households || 0).toLocaleString() }}</span>
              </div>
            </div>
            <div class="max-h-80 overflow-auto">
              <table class="w-full text-sm">
                <thead class="sticky top-0 bg-white border-b border-gray-200">
                  <tr>
                    <th class="px-3 py-2 text-left">권역</th>
                    <th class="px-3 py-2 text-left">이름</th>
                    <th class="px-3 py-2 text-right">건수</th>
                    <th class="px-3 py-2 text-right">가구수</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in textPreviewRows" :key="row.row_num" class="border-b border-gray-100">
                    <td class="px-3 py-2 font-semibold">{{ row.sub_region }}</td>
                    <td class="px-3 py-2">{{ row.manager_name }}</td>
                    <td class="px-3 py-2 text-right">{{ Number(row.boxes || 0).toLocaleString() }}</td>
                    <td class="px-3 py-2 text-right">{{ Number(row.households || 0).toLocaleString() }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <button type="button" class="w-full rounded-xl bg-primary px-5 py-3 font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="!canPreviewTextUpload || textUploadLoading || textPreviewLoading || (textPreview?.errors?.length || 0) > 0"
            @click="submitTextUpload">
            {{ textUploadLoading ? '저장 중...' : '확인 후 저장' }}
          </button>
        </div>

        <div v-else-if="isFileUploadMode" @dragover.prevent="isDragging = true" @dragleave="isDragging = false" @drop.prevent="handleDrop"
          class="border-2 border-dashed rounded-xl p-16 text-center transition-all cursor-pointer"
          :class="isDragging ? 'border-primary bg-primary-light' : 'border-gray-300 hover:border-primary'"
          @click="$refs.fileInput.click()">
          <input ref="fileInput" type="file" accept=".xlsx,.xls" multiple class="hidden" @change="handleFileSelect" />
          <div class="text-5xl mb-4 text-gray-400">&#128194;</div>
          <p class="text-lg font-medium text-text mb-1">파일을 여기에 끌어다 놓거나 클릭하세요</p>
          <p class="text-gray-400">여러 개의 .xlsx 파일을 한 번에 선택하거나 드래그할 수 있습니다.</p>
        </div>
        <div v-else class="rounded-xl border border-amber-200 bg-amber-50 p-8 text-sm text-amber-800">
          <p class="text-lg font-bold text-amber-900">업로드 로직 개발 필요</p>
          <p class="mt-2">
            {{ selectedShipperProfile?.name || selectedShipper }} 화주사는 컬리/쿠팡과 다른 배차표 형식을 사용하므로,
            별도 파싱 로직을 개발하고 배포한 뒤 업로드할 수 있습니다.
          </p>
        </div>

        <div v-if="!isOneShipper && isUploading" class="mt-6 flex items-center gap-3 text-primary">
          <div class="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full"></div>
          <span class="font-medium">{{ uploadProgressText || '파일 분석 중...' }}</span>
        </div>
        <div v-if="!isOneShipper && uploadError" class="mt-4 p-4 bg-red-50 border border-red-200 text-danger rounded-lg">{{ uploadError }}</div>
        <div v-if="!isOneShipper && batchUploadResults.length > 0" class="mt-4 border border-gray-200 rounded-lg overflow-hidden">
          <div class="px-4 py-3 bg-gray-50 font-bold text-text">일괄 업로드 결과</div>
          <div class="divide-y divide-gray-100">
            <div v-for="result in batchUploadResults" :key="result.key" class="px-4 py-3 flex items-center justify-between gap-4">
              <span class="font-medium text-text truncate">{{ result.name }}</span>
              <span
                class="shrink-0 px-2 py-1 rounded-full text-xs font-semibold"
                :class="result.ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
              >
                {{ result.ok ? '완료' : result.message }}
              </span>
            </div>
          </div>
        </div>

        <!-- 업로드 이력 -->
        <div v-if="!isOneShipper" class="mt-8 rounded-xl border border-gray-200 bg-white">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3">
            <div>
              <h4 class="font-bold text-text">기존 업로드 이력</h4>
              <p class="text-xs text-gray-500">
                {{ uploadHistoryLoaded ? `${uploadHistoryCount.toLocaleString()}건` : '업로드 화면 표시 후 별도로 불러옵니다.' }}
              </p>
            </div>
            <button type="button" class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              :disabled="uploadHistoryLoading"
              @click="refreshHistory">
              {{ uploadHistoryLoading ? '로딩 중' : '새로고침' }}
            </button>
          </div>

          <div v-if="uploadHistoryLoading && !uploadHistoryLoaded" class="px-4 py-8 text-center text-sm font-semibold text-primary">
            업로드 이력을 불러오는 중입니다.
          </div>
          <div v-else-if="uploadHistoryError" class="m-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-danger">
            {{ uploadHistoryError }}
          </div>
          <div v-else-if="uploadHistoryLoaded && uploadHistory.length === 0" class="px-4 py-8 text-center text-sm text-gray-400">
            업로드 이력이 없습니다.
          </div>
          <div v-else class="max-h-[520px] overflow-y-auto p-3">
            <div class="space-y-2">
              <div v-for="upload in uploadHistory" :key="upload.id"
                class="flex flex-col gap-3 rounded-lg bg-gray-50 p-3 md:flex-row md:items-center md:justify-between">
                <div class="min-w-0">
                  <div class="truncate font-medium text-text">{{ upload.original_filename || '배차파일' }}</div>
                  <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
                    <span v-if="upload.dispatch_date" class="font-semibold text-blue-600">{{ upload.dispatch_date }}</span>
                    <span>{{ upload.team_name || '-' }}</span>
                    <span>{{ Number(upload.total_rows || 0).toLocaleString() }}행</span>
                    <span v-if="upload.round_no">{{ upload.round_no }}회차</span>
                  </div>
                </div>
                <div class="flex shrink-0 flex-wrap items-center gap-2">
                  <span class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="upload.status === 'CONFIRMED' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'">
                    {{ upload.status === 'CONFIRMED' ? '정산완료' : '대기중' }}
                  </span>
                  <button v-if="upload.status !== 'CONFIRMED'" @click="resumeUpload(upload)"
                    class="rounded-lg bg-primary px-3 py-1 text-xs font-medium text-white hover:opacity-90">
                    정산생성
                  </button>
                  <button @click="downloadUploadFile(upload)"
                    class="rounded-lg bg-gray-900 px-3 py-1 text-xs font-medium text-white hover:bg-gray-800">
                    원본다운
                  </button>
                  <button @click="deleteUpload(upload)"
                    class="rounded-lg bg-red-500 px-3 py-1 text-xs font-medium text-white hover:opacity-90">
                    삭제
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ============ STEP 1: 일괄 정산 생성 ============ -->
      <div v-if="!isOneShipper && currentStep === 1 && batchMode" class="space-y-5">
        <div class="bg-white rounded-xl p-5 border border-gray-200">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-xl font-bold text-text">일괄 정산 생성</h3>
              <p class="text-gray-500">업로드된 배차표를 한 번에 정산 생성합니다.</p>
            </div>
            <div class="flex gap-3">
              <span class="px-3 py-1 bg-blue-50 text-blue-700 rounded-full font-medium">{{ batchUploads.length }}개 파일</span>
              <span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full">{{ batchTotalRows.toLocaleString() }}행</span>
            </div>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th class="text-left px-4 py-3 font-semibold text-gray-600">파일명</th>
                  <th class="text-left px-4 py-3 font-semibold text-gray-600">배송일</th>
                  <th class="text-left px-4 py-3 font-semibold text-gray-600">조</th>
                  <th class="text-right px-4 py-3 font-semibold text-gray-600">행</th>
                  <th class="text-center px-4 py-3 font-semibold text-gray-600">상태</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="upload in batchUploads" :key="upload.id" class="border-b border-gray-100">
                  <td class="px-4 py-3 font-medium text-text">{{ upload.original_filename || '배차파일' }}</td>
                  <td class="px-4 py-3 text-blue-700">{{ upload.dispatch_date || '-' }}</td>
                  <td class="px-4 py-3">{{ upload.team_name || '-' }}</td>
                  <td class="px-4 py-3 text-right font-bold">{{ Number(upload.total_rows || 0).toLocaleString() }}</td>
                  <td class="px-4 py-3 text-center">
                    <span class="px-2 py-1 rounded-full text-xs font-semibold"
                      :class="batchResultByUploadId[upload.id]?.ok ? 'bg-green-100 text-green-700' : batchResultByUploadId[upload.id]?.ok === false ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'">
                      {{ batchResultByUploadId[upload.id]?.label || '정산 대기' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="authStore.isAdmin" class="bg-white rounded-xl p-5 border border-gray-200">
          <h3 class="font-bold text-text mb-4">팀 단가 설정</h3>
          <div v-for="team in teamPricingList" :key="team.id || team.code"
            class="p-5 border border-gray-200 rounded-xl mb-3">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-10 h-10 bg-primary-light rounded-full flex items-center justify-center">
                <span class="text-primary-dark font-bold">{{ team.code }}</span>
              </div>
              <span class="text-lg font-bold text-text">{{ team.name }}</span>
              <span v-if="team.has_price" class="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">설정됨</span>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-500 mb-1">수신단가 (박스당)</label>
                <input v-model.number="team._receive_price" type="number" placeholder="0"
                  class="w-full px-4 py-3 border border-blue-200 rounded-lg text-right text-lg bg-blue-50 focus:border-blue-400 outline-none" />
              </div>
              <div>
                <label class="block text-sm text-gray-500 mb-1">특근비용 (1인당)</label>
                <input v-model.number="team._overtime_cost" type="number" placeholder="0"
                  class="w-full px-4 py-3 border border-amber-200 rounded-lg text-right text-lg bg-amber-50 focus:border-amber-400 outline-none" />
              </div>
            </div>
          </div>
        </div>

        <div v-if="newCrewList.length > 0" class="bg-white rounded-xl p-5 border border-gray-200">
          <h3 class="font-bold text-text mb-1">신규 배송원 확인</h3>
          <p class="text-gray-500 mb-4">
            지급단가를 0원으로 두면 용차로 처리되며, 용차 지급단가는 가구당으로 적용됩니다.
          </p>
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="text-left px-4 py-3 font-semibold text-gray-600">이름</th>
                <th class="text-left px-4 py-3 font-semibold text-gray-600">조</th>
                <th class="text-center px-4 py-3 font-semibold text-gray-600">구분</th>
                <th class="text-right px-4 py-3 font-semibold text-orange-600">지급단가 (박스당)</th>
                <th class="text-right px-4 py-3 font-semibold text-fuchsia-600">용차지급단가 (가구당)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="crew in newCrewList" :key="crew.batch_key || crew.code" class="border-b border-gray-100">
                <td class="px-4 py-3 font-bold text-text">{{ crew.code }}</td>
                <td class="px-4 py-3">{{ crew.team_name || '-' }}</td>
                <td class="px-4 py-3 text-center">
                  <span class="px-2 py-1 rounded-full text-xs font-semibold"
                    :class="isCrewYongchaCandidate(crew) ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700'">
                    {{ isCrewYongchaCandidate(crew) ? '용차' : '정규' }}
                  </span>
                </td>
                <td class="px-4 py-3 text-right">
                  <input v-if="!crew.is_yongcha" v-model.number="crew._pay_price" type="number" placeholder="0" min="0"
                    class="w-32 px-3 py-2 border border-orange-300 rounded-lg text-right bg-orange-50 focus:border-orange-400 outline-none" />
                  <span v-else class="text-gray-400">용차</span>
                </td>
                <td class="px-4 py-3 text-right">
                  <input v-model.number="crew._yongcha_pay_price" type="number" placeholder="3000" min="0"
                    class="w-36 px-3 py-2 border border-fuchsia-300 rounded-lg text-right bg-fuchsia-50 focus:border-fuchsia-400 outline-none" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="batchOvertimeGroups.length > 0" class="bg-white rounded-xl p-5 border border-gray-200">
          <h3 class="font-bold text-text mb-1">특근 설정</h3>
          <p class="text-gray-500 mb-4">파일별로 특근 대상 배송원을 선택하고 금액을 입력하세요.</p>

          <div v-for="group in batchOvertimeGroups" :key="group.upload_id" class="mb-5 last:mb-0 border border-gray-200 rounded-xl overflow-hidden">
            <div class="px-4 py-3 bg-gray-50 flex items-center justify-between">
              <div>
                <div class="font-bold text-text">{{ group.name }}</div>
                <div class="text-sm text-gray-500">{{ group.dispatch_date || '-' }} · {{ group.team_name || '-' }}</div>
              </div>
              <span class="text-sm text-gray-500">특근 {{ group.crew.filter(c => c.isOvertime).length }}명</span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-white border-b border-gray-200">
                  <tr>
                    <th class="text-left px-4 py-3 font-semibold text-gray-600">배송원</th>
                    <th class="text-left px-4 py-3 font-semibold text-gray-600">담당 권역</th>
                    <th class="text-right px-4 py-3 font-semibold text-gray-600">박스수</th>
                    <th class="text-center px-4 py-3 font-semibold text-gray-600">특근</th>
                    <th class="text-right px-4 py-3 font-semibold text-gray-600">특근 금액(원)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="person in group.crew" :key="person.key" class="border-b border-gray-100 last:border-b-0">
                    <td class="px-4 py-3 font-medium text-text">{{ person.name }}</td>
                    <td class="px-4 py-3">
                      <div class="flex flex-wrap gap-1">
                        <span v-for="region in person.regions" :key="region"
                          class="px-2 py-0.5 bg-primary-light text-primary-dark rounded text-xs font-medium">{{ region }}</span>
                      </div>
                    </td>
                    <td class="px-4 py-3 text-right font-bold">{{ Number(person.totalBoxes || 0).toLocaleString() }}</td>
                    <td class="px-4 py-3 text-center">
                      <input type="checkbox" v-model="person.isOvertime" class="w-5 h-5 rounded" />
                    </td>
                    <td class="px-4 py-3 text-right">
                      <input v-if="person.isOvertime" v-model.number="person.overtimeCost"
                        type="number" min="0" placeholder="0"
                        class="w-32 px-3 py-2 border border-orange-300 rounded-lg text-right bg-orange-50 focus:border-orange-400 outline-none" />
                      <span v-else class="text-gray-300">-</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div v-if="batchSettlementResults.length > 0" class="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-200 font-bold text-text">정산 생성 결과</div>
          <div class="divide-y divide-gray-100">
            <div v-for="result in batchSettlementResults" :key="result.upload_id" class="px-5 py-4 flex items-center justify-between gap-4">
              <div>
                <div class="font-medium text-text">{{ result.name }}</div>
                <div class="text-sm text-gray-500">{{ result.detail }}</div>
              </div>
              <span class="px-2 py-1 rounded-full text-xs font-semibold"
                :class="result.ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'">
                {{ result.ok ? '완료' : '실패' }}
              </span>
            </div>
          </div>
          <div class="px-5 py-4 border-t border-gray-200">
            <button @click="resetUpload" class="px-6 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">
              새로 업로드
            </button>
          </div>
        </div>
      </div>

      <!-- ============ STEP 1: 데이터 확인 + 팀 단가 + 배송원 등록 ============ -->
      <div v-if="!isOneShipper && currentStep === 1 && !batchMode" class="space-y-5">
        <!-- 업로드 요약 -->
        <div class="bg-white rounded-xl p-5 border border-gray-200">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-xl font-bold text-text">배차 데이터 확인</h3>
            <div class="flex gap-3">
              <span v-if="dispatchDate" class="px-3 py-1 bg-blue-50 text-blue-700 rounded-full font-medium">{{ dispatchDate }}</span>
              <span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full">{{ validRecordCount }}건</span>
            </div>
          </div>
          <div class="overflow-x-auto max-h-80 overflow-y-auto">
            <table class="w-full">
              <thead class="bg-gray-50 border-b border-gray-200 sticky top-0">
                <tr>
                  <th class="text-left px-4 py-3 font-semibold text-gray-600">담당자</th>
                  <th class="text-left px-4 py-3 font-semibold text-gray-600">권역</th>
                  <th class="text-right px-4 py-3 font-semibold text-gray-600">박스수</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rec in visibleRecords" :key="rec.id" class="border-b border-gray-100 hover:bg-gray-50">
                  <td class="px-4 py-3 font-medium text-text">{{ rec.manager_name }}</td>
                  <td class="px-4 py-3">
                    <div class="flex flex-wrap gap-1">
                      <span v-for="r in rec.sub_region.split(',').map(s => s.trim()).filter(s => s && s !== '-')" :key="r"
                        class="px-2 py-0.5 bg-primary-light text-primary-dark rounded text-xs font-medium">{{ r }}</span>
                    </div>
                  </td>
                  <td class="px-4 py-3 text-right font-bold">{{ rec.boxes }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 팀 단가 설정 (관리자만) -->
        <div v-if="authStore.isAdmin" class="bg-white rounded-xl p-5 border border-gray-200">
          <h3 class="font-bold text-text mb-4">팀 단가 설정</h3>
          <div v-for="team in teamPricingList" :key="team.id"
            class="p-5 border border-gray-200 rounded-xl mb-3">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-10 h-10 bg-primary-light rounded-full flex items-center justify-center">
                <span class="text-primary-dark font-bold">{{ team.code }}</span>
              </div>
              <span class="text-lg font-bold text-text">{{ team.name }}</span>
              <span v-if="team.has_price" class="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">설정됨</span>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-500 mb-1">수신단가 (박스당)</label>
                <input v-model.number="team._receive_price" type="number" placeholder="0"
                  class="w-full px-4 py-3 border border-blue-200 rounded-lg text-right text-lg bg-blue-50 focus:border-blue-400 outline-none" />
              </div>
              <div>
                <label class="block text-sm text-gray-500 mb-1">특근비용 (1인당)</label>
                <input v-model.number="team._overtime_cost" type="number" placeholder="0"
                  class="w-full px-4 py-3 border border-amber-200 rounded-lg text-right text-lg bg-amber-50 focus:border-amber-400 outline-none" />
              </div>
            </div>
          </div>
        </div>

        <!-- 배송원 확인 -->
        <div v-if="newCrewList.length > 0" class="bg-white rounded-xl p-5 border border-gray-200">
          <h3 class="font-bold text-text mb-1">신규 배송원 확인</h3>
          <p class="text-gray-500 mb-4">
            처음 보는 이름입니다. 이름 끝에 v가 붙었거나 지급단가를 0원으로 두고 진행하면 용차로 처리되며, 용차 지급단가는 가구당으로 적용됩니다.
          </p>

          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="text-left px-4 py-3 font-semibold text-gray-600">이름</th>
                <th class="text-center px-4 py-3 font-semibold text-gray-600">구분</th>
                <th class="text-right px-4 py-3 font-semibold text-orange-600">지급단가 (박스당)</th>
                <th class="text-right px-4 py-3 font-semibold text-fuchsia-600">용차지급단가 (가구당)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="crew in newCrewList" :key="crew.code" class="border-b border-gray-100">
                <td class="px-4 py-3 font-bold text-text">{{ crew.code }}</td>
                <td class="px-4 py-3 text-center">
                  <span class="px-2 py-1 rounded-full text-xs font-semibold"
                    :class="isCrewYongchaCandidate(crew) ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700'">
                    {{ isCrewYongchaCandidate(crew) ? '용차' : '정규' }}
                  </span>
                </td>
                <td class="px-4 py-3 text-right">
                  <input v-if="!crew.is_yongcha" v-model.number="crew._pay_price" type="number" placeholder="0" min="0"
                    class="w-32 px-3 py-2 border border-orange-300 rounded-lg text-right bg-orange-50 focus:border-orange-400 outline-none" />
                  <span v-else class="text-gray-400">이름 v 감지</span>
                </td>
                <td class="px-4 py-3 text-right">
                  <input v-model.number="crew._yongcha_pay_price" type="number" placeholder="3000" min="0"
                    class="w-36 px-3 py-2 border border-fuchsia-300 rounded-lg text-right bg-fuchsia-50 focus:border-fuchsia-400 outline-none" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="existingCrewMembers.length > 0" class="bg-white rounded-xl p-5 border border-green-200">
          <h4 class="font-semibold text-success mb-2">기존 배송원 ({{ existingCrewMembers.length }}명)</h4>
          <div class="flex flex-wrap gap-2">
            <span v-for="c in existingCrewMembers" :key="c.code"
              class="px-3 py-1 bg-green-50 text-green-700 rounded-full font-medium">{{ c.code }}</span>
          </div>
        </div>
      </div>

      <!-- ============ STEP 2: 특근 설정 ============ -->
      <div v-if="!isOneShipper && currentStep === 2 && !batchMode" class="space-y-5">
        <div class="bg-white rounded-xl p-5 border border-gray-200">
          <h3 class="text-xl font-bold text-text mb-1">특근 설정</h3>
          <p class="text-gray-500 mb-4">특근 대상 배송원을 선택하고 금액을 입력하세요.</p>

          <div v-if="dispatchDate" class="mb-4 px-4 py-2 bg-blue-50 rounded-lg text-blue-700 font-medium">
            배차일: {{ dispatchDate }}
          </div>

          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="text-left px-4 py-3 font-semibold text-gray-600">배송원</th>
                <th class="text-left px-4 py-3 font-semibold text-gray-600">담당 권역</th>
                <th class="text-right px-4 py-3 font-semibold text-gray-600">박스수</th>
                <th class="text-center px-4 py-3 font-semibold text-gray-600">특근</th>
                <th class="text-right px-4 py-3 font-semibold text-gray-600">특근 금액(원)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="person in crewOvertimeList" :key="person.name"
                class="border-b border-gray-100 hover:bg-gray-50">
                <td class="px-4 py-3 font-medium text-text">{{ person.name }}</td>
                <td class="px-4 py-3">
                  <div class="flex flex-wrap gap-1">
                    <span v-for="r in person.regions" :key="r"
                      class="px-2 py-0.5 bg-primary-light text-primary-dark rounded text-xs font-medium">{{ r }}</span>
                  </div>
                </td>
                <td class="px-4 py-3 text-right font-bold">{{ person.totalBoxes }}</td>
                <td class="px-4 py-3 text-center">
                  <input type="checkbox" v-model="person.isOvertime" class="w-5 h-5 rounded" />
                </td>
                <td class="px-4 py-3 text-right">
                  <input v-if="person.isOvertime" v-model.number="person.overtimeCost"
                    type="number" min="0" placeholder="0"
                    class="w-32 px-3 py-2 border border-orange-300 rounded-lg text-right bg-orange-50 focus:border-orange-400 outline-none" />
                  <span v-else class="text-gray-300">-</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="mt-3 flex justify-between text-gray-500">
            <span>{{ crewOvertimeList.length }}명</span>
            <span>특근 {{ crewOvertimeList.filter(c => c.isOvertime).length }}명</span>
          </div>
        </div>
      </div>

      <!-- ============ STEP 3: 정산 확정 ============ -->
      <div v-if="!isOneShipper && currentStep === 3 && !batchMode" class="space-y-5">
        <div v-if="!settlementResult" class="bg-white rounded-xl p-6 border border-gray-200">
          <h3 class="text-xl font-bold text-text mb-6">정산 확인</h3>
          <div class="grid grid-cols-4 gap-4 mb-6">
            <div class="p-5 bg-gray-50 rounded-xl text-center">
              <p class="text-sm text-gray-500 mb-1">등록 배송원</p>
              <p class="text-2xl font-bold text-text">{{ registeredCount }}명</p>
            </div>
            <div class="p-5 bg-gray-50 rounded-xl text-center">
              <p class="text-sm text-gray-500 mb-1">배차 건수</p>
              <p class="text-2xl font-bold text-text">{{ validRecordCount }}건</p>
            </div>
            <div class="p-5 bg-gray-50 rounded-xl text-center">
              <p class="text-sm text-gray-500 mb-1">특근</p>
              <p class="text-2xl font-bold text-warning">{{ crewOvertimeList.filter(c => c.isOvertime).length }}명</p>
            </div>
            <div class="p-5 bg-gray-50 rounded-xl text-center">
              <p class="text-sm text-gray-500 mb-1">배차일</p>
              <p class="text-2xl font-bold text-blue-700">{{ dispatchDate || '-' }}</p>
            </div>
          </div>
        </div>

        <!-- 정산 결과 -->
        <div v-if="settlementResult" class="space-y-5">
          <div class="bg-white rounded-xl p-8 border border-green-200 text-center">
            <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center text-success text-3xl mx-auto mb-4">&#10003;</div>
            <p class="font-bold text-2xl text-text mb-2">정산이 생성되었습니다</p>
            <p class="text-gray-500">
              {{ settlementResult.settlement.period_start }} | {{ settlementResult.settlement.team }} |
              {{ settlementResult.crew_details?.length || 0 }}명 배송원
            </p>
            <div v-if="settlementResult.skipped_crew?.length > 0"
              class="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-left">
              미등록 제외: {{ settlementResult.skipped_crew.join(', ') }}
            </div>
          </div>

          <button @click="resetUpload" class="px-6 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">
            새로 업로드
          </button>
        </div>
      </div>

      <!-- 하단 버튼 -->
      <div v-if="!isOneShipper && currentStep > 0 && !settlementResult && !batchSettlementComplete"
        class="flex justify-between bg-white rounded-xl p-5 border border-gray-200">
        <button @click="currentStep--"
          class="px-5 py-3 border border-gray-300 rounded-lg text-text hover:bg-gray-50 font-medium">이전</button>
        <div class="flex gap-3">
          <button v-if="batchMode" @click="handleBatchFinalize" :disabled="isProcessing || batchUploads.length === 0"
            class="px-8 py-3 bg-success text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50">
            {{ isProcessing ? '일괄 정산 생성 중...' : '일괄 정산 생성' }}
          </button>
          <button v-else-if="currentStep < 3" @click="handleNextStep" :disabled="isProcessing"
            class="px-8 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50">
            {{ isProcessing ? '처리 중...' : '다음' }}
          </button>
          <button v-else-if="currentStep === 3" @click="handleFinalize" :disabled="isProcessing"
            class="px-8 py-3 bg-success text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50">
            {{ isProcessing ? '정산 생성 중...' : '정산 생성' }}
          </button>
        </div>
      </div>

      <div v-if="processError" class="p-4 bg-red-50 border border-red-200 text-danger rounded-xl">{{ processError }}</div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { formatDateTime, formatCurrency } from '@/utils/format'
import AppLayout from '@/components/common/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import client from '@/api/client'
import { fetchPublicCompanyApp, fetchShippers } from '@/api/companyAdmin'
import { getCompanyAppFromRoute } from '@/utils/companyApp'
import {
  ensureSelectedShipperCode,
  setSelectedShipperCode,
  SHIPPER_CONTEXT_CHANGED_EVENT,
} from '@/utils/shipperContext'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
import {
  uploadDispatchFile, getDetectedInfo, configureAll,
  setOvertime, finalizeUpload, fetchUploads, getRecords, downloadDispatchFile,
  previewTextDispatch, uploadTextDispatch
} from '@/api/dispatch'

const currentStep = ref(0)
const stepLabels = computed(() => (
  batchMode.value
    ? ['배차표 업로드', '일괄 정산 생성']
    : ['배차표 업로드', '데이터 확인·단가 설정', '특근 설정', '정산 확정']
))

const isDragging = ref(false)
const isUploading = ref(false)
const isProcessing = ref(false)
const uploadError = ref('')
const uploadProgressText = ref('')
const processError = ref('')
const uploadId = ref(null)

const selectedShipper = ref('kurly')
const enabledShipperCodes = ref(['kurly'])
const shipperCatalog = ref([])
const fileUploadShipperCodes = new Set(['kurly'])
const textUploadShipperCodes = new Set(['coupang'])
const textTeams = ref([])
const textDateBasis = ref('delivery')
const textDispatchDate = ref('')
const textRoundCode = ref('W1')
const textTeamId = ref('')
const textNewTeamName = ref('')
const textRaw = ref('')
const textPreview = ref(null)
const textPreviewLoading = ref(false)
const textUploadLoading = ref(false)
const textError = ref('')
let textPreviewTimer = null

const coupangRoundOptions = [
  { code: 'W1', label: 'W1', roundNo: 1 },
  { code: 'W2', label: 'W2', roundNo: 2 },
  { code: 'D1', label: 'D1', roundNo: 1 },
  { code: 'D2', label: 'D2', roundNo: 2 },
  { code: 'D3', label: 'D3', roundNo: 3 },
]

const detectedInfo = ref(null)
const uploadRecords = ref([])
const uploadHistory = ref([])
const uploadHistoryLoading = ref(false)
const uploadHistoryLoaded = ref(false)
const uploadHistoryError = ref('')
const batchUploadResults = ref([])
const batchMode = ref(false)
const batchUploads = ref([])
const batchOvertimeGroups = ref([])
const batchSettlementResults = ref([])
const newCrewList = ref([])
const dispatchDate = ref(null)
const teamPricingList = ref([])
const crewOvertimeList = ref([])

const settlementResult = ref(null)
const expandedCrewCode = ref(null)

const batchTotalRows = computed(() => (
  batchUploads.value.reduce((sum, upload) => sum + Number(upload.total_rows || 0), 0)
))

const uploadHistoryCount = computed(() => uploadHistory.value.length)

const batchSettlementComplete = computed(() => (
  batchMode.value && batchSettlementResults.value.length > 0 && !isProcessing.value
))

const batchResultByUploadId = computed(() => {
  const resultMap = {}
  for (const result of batchSettlementResults.value) {
    resultMap[result.upload_id] = {
      ok: result.ok,
      label: result.ok ? '정산 완료' : '실패',
    }
  }
  return resultMap
})

const normalizeList = (payload) => payload?.results || payload || []

const shipperOptions = computed(() => {
  const enabled = new Set(enabledShipperCodes.value.length ? enabledShipperCodes.value : ['kurly'])
  const rows = normalizeList(shipperCatalog.value).filter(item => enabled.has(item.code))
  if (rows.length > 0) return rows
  return [{ code: 'kurly', name: '컬리', upload_type: 'FILE' }]
})

const selectedShipperProfile = computed(() => (
  shipperOptions.value.find(item => item.code === selectedShipper.value)
  || shipperOptions.value[0]
  || { code: 'kurly', name: '컬리', upload_type: 'FILE' }
))

const companyAppCode = computed(() => getCompanyAppFromRoute(route).code)
const isOneShipper = computed(() => String(selectedShipper.value || '').trim().toLowerCase() === 'one')
const isFileUploadMode = computed(() => fileUploadShipperCodes.has(String(selectedShipper.value || '').trim().toLowerCase()))
const isTextUploadMode = computed(() => textUploadShipperCodes.has(String(selectedShipper.value || '').trim().toLowerCase()))

const canPreviewTextUpload = computed(() => (
  isTextUploadMode.value
  && effectiveTextDispatchDate.value
  && textRoundNo.value
  && textTeamId.value
  && textRaw.value.trim()
))

const textPreviewRows = computed(() => textPreview.value?.rows || [])
const selectedCoupangRound = computed(() => (
  coupangRoundOptions.find((round) => round.code === textRoundCode.value) || coupangRoundOptions[0]
))
const textRoundNo = computed(() => selectedCoupangRound.value.roundNo)
const textDateInputLabel = computed(() => (textDateBasis.value === 'work' ? '출근일' : '배송일'))
const effectiveTextDispatchDate = computed(() => {
  if (!textDispatchDate.value) return ''
  if (textDateBasis.value !== 'work') return textDispatchDate.value
  const parsed = new Date(`${textDispatchDate.value}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return ''
  parsed.setDate(parsed.getDate() + 1)
  const year = parsed.getFullYear()
  const month = String(parsed.getMonth() + 1).padStart(2, '0')
  const day = String(parsed.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
})

const existingCrewMembers = computed(() => {
  if (!detectedInfo.value) return []
  return detectedInfo.value.crew_members.filter(c => !c.is_new)
})

const visibleRecords = computed(() => {
  return uploadRecords.value.filter(r => r.manager_name && r.boxes > 0)
})

const validRecordCount = computed(() => visibleRecords.value.length)

const registeredCount = computed(() => {
  if (crewOvertimeList.value.length > 0) return crewOvertimeList.value.length
  return existingCrewMembers.value.length + newCrewList.value.length
})

// Methods
const goToStep = (idx) => { if (idx < currentStep.value) currentStep.value = idx }

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
  } catch (e) {
    enabledShipperCodes.value = ['kurly']
    shipperCatalog.value = [{ code: 'kurly', name: '컬리', upload_type: 'FILE' }]
  }
  await loadTextTeams()
}

const handleShipperContextChanged = (event) => {
  const detail = event?.detail || {}
  if (detail.companyCode !== companyAppCode.value) return
  if (!detail.shipperCode || selectedShipper.value === detail.shipperCode) return
  selectedShipper.value = detail.shipperCode
}

const loadTextTeams = async () => {
  if (!isTextUploadMode.value) {
    textTeams.value = []
    textTeamId.value = ''
    return
  }
  try {
    const resp = await client.get('/accounts/teams/', {
      params: { shipper_code: selectedShipper.value },
    })
    textTeams.value = normalizeList(resp.data)
    if (textTeamId.value && !textTeams.value.some(team => String(team.id) === String(textTeamId.value))) {
      textTeamId.value = ''
    }
  } catch (e) {
    textTeams.value = []
  }
}

const createTextTeam = async () => {
  const name = textNewTeamName.value.trim()
  if (!name) {
    textError.value = '추가할 조 이름을 입력해주세요.'
    return
  }
  textError.value = ''
  try {
    const resp = await client.post('/accounts/teams/shipper-team/', {
      shipper_code: selectedShipper.value,
      name,
    })
    textNewTeamName.value = ''
    await loadTextTeams()
    textTeamId.value = String(resp.data?.id || '')
    scheduleTextPreview()
  } catch (e) {
    textError.value = e.response?.data?.detail || '조 추가에 실패했습니다.'
  }
}

const buildTextPayload = () => ({
  shipper_code: selectedShipper.value,
  team_id: textTeamId.value,
  input_date: textDispatchDate.value,
  date_basis: textDateBasis.value,
  dispatch_date: effectiveTextDispatchDate.value,
  round_no: textRoundNo.value,
  round_code: textRoundCode.value,
  raw_text: textRaw.value,
})

const runTextPreview = async () => {
  if (!canPreviewTextUpload.value) {
    textPreview.value = null
    return
  }
  textPreviewLoading.value = true
  textError.value = ''
  try {
    const resp = await previewTextDispatch(buildTextPayload())
    textPreview.value = resp.data
    if (resp.data?.errors?.length) {
      textError.value = resp.data.errors[0]?.message || '파싱 오류가 있습니다.'
    }
  } catch (e) {
    textPreview.value = null
    textError.value = e.response?.data?.detail || '텍스트 미리보기에 실패했습니다.'
  } finally {
    textPreviewLoading.value = false
  }
}

const scheduleTextPreview = () => {
  if (textPreviewTimer) window.clearTimeout(textPreviewTimer)
  textPreviewTimer = window.setTimeout(runTextPreview, 350)
}

const submitTextUpload = async () => {
  if (!isTextUploadMode.value) {
    textError.value = '이 화주사의 텍스트 업로드 로직은 아직 지원하지 않습니다.'
    return
  }
  if (!canPreviewTextUpload.value) {
    textError.value = '배송일, 회차, 조, 텍스트를 모두 입력해주세요.'
    return
  }
  textUploadLoading.value = true
  textError.value = ''
  try {
    const resp = await uploadTextDispatch(buildTextPayload())
    batchMode.value = false
    batchUploads.value = []
    batchOvertimeGroups.value = []
    batchSettlementResults.value = []
    batchUploadResults.value = []
    await applyUploadData(resp.data)
    currentStep.value = 1
    await loadHistory()
  } catch (e) {
    textError.value = e.response?.data?.detail || '텍스트 저장에 실패했습니다.'
  } finally {
    textUploadLoading.value = false
  }
}

const isCrewYongchaCandidate = (crew) => {
  return Boolean(crew.is_yongcha) || Number(crew._pay_price || 0) <= 0
}

const makeBatchCrewKey = (teamId, code) => `${teamId || 'none'}:${code}`

const buildBatchTeams = (uploads) => {
  const teamMap = new Map()
  for (const upload of uploads) {
    for (const team of upload.detected_info?.teams || []) {
      const key = team.id || team.code
      if (!key || teamMap.has(key)) continue
      teamMap.set(key, {
        ...team,
        _receive_price: team.receive_price || 0,
        _pay_price: team.pay_price || 0,
        _overtime_cost: team.default_overtime_cost || 0,
      })
    }
  }
  return Array.from(teamMap.values())
}

const buildBatchNewCrew = (uploads) => {
  const crewMap = new Map()
  for (const upload of uploads) {
    const teamId = upload.team || null
    const teamName = upload.team_name || ''
    for (const crew of upload.detected_info?.crew_members || []) {
      if (!crew.is_new) continue
      const key = makeBatchCrewKey(teamId, crew.code)
      const existing = crewMap.get(key)
      if (existing) {
        existing.upload_ids.push(upload.id)
        existing.file_names.push(upload.original_filename || '배차파일')
        existing.is_yongcha = existing.is_yongcha || crew.is_yongcha
        if (!existing._yongcha_pay_price) {
          existing._yongcha_pay_price = Number(crew.yongcha_pay_price || 3000)
        }
        continue
      }
      crewMap.set(key, {
        ...crew,
        batch_key: key,
        team: teamId,
        team_name: teamName,
        upload_ids: [upload.id],
        file_names: [upload.original_filename || '배차파일'],
        _pay_price: Number(crew.pay_price || 0),
        _yongcha_pay_price: Number(crew.yongcha_pay_price || 3000),
      })
    }
  }
  return Array.from(crewMap.values()).sort((a, b) => {
    const teamCompare = String(a.team_name || '').localeCompare(String(b.team_name || ''))
    if (teamCompare) return teamCompare
    return String(a.code || '').localeCompare(String(b.code || ''))
  })
}

const uploadDefaultOvertimeCost = (upload, teams) => {
  const team = teams.find(t => t.id === upload.team)
    || (upload.detected_info?.teams || []).find(t => t.id === upload.team)
    || (upload.detected_info?.teams || [])[0]
    || teams[0]
  return Number(team?._overtime_cost ?? team?.default_overtime_cost ?? 0)
}

const buildBatchOvertimeGroups = (uploads, teams) => {
  return uploads.map(upload => {
    const defaultOT = uploadDefaultOvertimeCost(upload, teams)
    const allowedCrew = new Set((upload.detected_info?.crew_members || []).map(crew => crew.code))
    const crewMap = {}

    for (const record of upload.records || []) {
      const name = String(record.manager_name || '').trim()
      if (!name || Number(record.boxes || 0) <= 0) continue
      if (allowedCrew.size > 0 && !allowedCrew.has(name)) continue

      if (!crewMap[name]) {
        crewMap[name] = {
          key: `${upload.id}:${name}`,
          name,
          regions: new Set(),
          totalBoxes: 0,
          isOvertime: false,
          overtimeCost: defaultOT,
        }
      }

      for (const region of String(record.sub_region || '').split(',').map(s => s.trim()).filter(Boolean)) {
        if (region !== '-') crewMap[name].regions.add(region)
      }
      crewMap[name].totalBoxes += Number(record.boxes || 0)
    }

    return {
      upload_id: upload.id,
      name: upload.original_filename || '배차파일',
      dispatch_date: upload.dispatch_date || '',
      team_name: upload.team_name || '',
      crew: Object.values(crewMap)
        .filter(person => person.totalBoxes > 0)
        .map(person => ({ ...person, regions: Array.from(person.regions) }))
        .sort((a, b) => a.name.localeCompare(b.name)),
    }
  }).filter(group => group.crew.length > 0)
}

const prepareBatchSettlement = (uploads) => {
  const teams = buildBatchTeams(uploads)
  batchMode.value = true
  batchUploads.value = uploads
  batchOvertimeGroups.value = buildBatchOvertimeGroups(uploads, teams)
  batchSettlementResults.value = []
  uploadId.value = null
  detectedInfo.value = null
  uploadRecords.value = []
  crewOvertimeList.value = []
  settlementResult.value = null
  teamPricingList.value = teams
  newCrewList.value = buildBatchNewCrew(uploads)
  dispatchDate.value = uploads.map(upload => upload.dispatch_date).filter(Boolean).join(', ')
  currentStep.value = 1
}

const handleDrop = (e) => {
  isDragging.value = false
  processFiles(e.dataTransfer.files)
}

const handleFileSelect = (e) => {
  processFiles(e.target.files)
  e.target.value = ''
}

const getExcelFiles = (fileList) => Array.from(fileList || [])
  .filter(file => file.name.match(/\.xlsx?$/i))

const getExistingUploadsForFileDate = async (file) => {
  const dateMatch = file.name.match(/(\d{4})-(\d{2})-(\d{2})/)
  if (!dateMatch) return { fileDate: null, existing: [] }

  const fileDate = `${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}`
  try {
    const checkResp = await client.get('/dispatch/uploads/check_date/', { params: { date: fileDate } })
    return { fileDate, existing: checkResp.data || [] }
  } catch (e) {
    return { fileDate, existing: [] }
  }
}

const confirmDuplicateUploads = async (files) => {
  const duplicates = []
  for (const file of files) {
    const { fileDate, existing } = await getExistingUploadsForFileDate(file)
    if (fileDate && existing.length > 0) {
      duplicates.push({ file, fileDate, existing })
    }
  }

  if (duplicates.length === 0) return true

  if (duplicates.length === 1) {
    const duplicate = duplicates[0]
    const times = duplicate.existing.map(e => {
      const d = new Date(e.upload_date)
      return `${d.getHours()}시 ${d.getMinutes()}분 ${d.getSeconds()}초`
    }).join(', ')
    return confirm(`${duplicate.fileDate}에 배차표를 올린 이력이 있습니다.\n(${times})\n\n추가로 올리시겠습니까? 정산이 합산됩니다.`)
  }

  const lines = duplicates.map(d => `- ${d.file.name} (${d.fileDate}, 기존 ${d.existing.length}건)`).join('\n')
  return confirm(`이미 배차표를 올린 날짜가 포함되어 있습니다.\n${lines}\n\n그래도 일괄 업로드하시겠습니까? 정산이 합산됩니다.`)
}

const applyUploadData = async (data) => {
  uploadId.value = data.id
  detectedInfo.value = data.detected_info
  dispatchDate.value = data.dispatch_date || null

  // 팀 단가 리스트
  teamPricingList.value = (data.detected_info.teams || []).map(t => ({
    ...t,
    _receive_price: t.receive_price || 0,
    _pay_price: t.pay_price || 0,
    _overtime_cost: t.default_overtime_cost || 0,
  }))

  newCrewList.value = (data.detected_info.crew_members || [])
    .filter(c => c.is_new)
    .map(c => ({
      ...c,
      _pay_price: Number(c.pay_price || 0),
      _yongcha_pay_price: Number(c.yongcha_pay_price || 3000),
    }))

  // create 응답에 records 포함, 없으면 별도 조회
  if (data.records && data.records.length > 0) {
    uploadRecords.value = data.records
  } else {
    const recResp = await getRecords(data.id)
    uploadRecords.value = recResp.data.results || recResp.data || []
  }
}

const uploadOneFile = async (file) => {
  const resp = await uploadDispatchFile(file, selectedShipper.value)
  const data = resp.data
  if (!data.records || data.records.length === 0) {
    const recResp = await getRecords(data.id)
    data.records = recResp.data.results || recResp.data || []
  }
  return data
}

const processFile = async (file) => {
  if (!file.name.match(/\.xlsx?$/i)) { uploadError.value = '.xlsx 파일만 업로드 가능합니다.'; return }
  if (!await confirmDuplicateUploads([file])) return

  batchMode.value = false
  batchUploads.value = []
  batchOvertimeGroups.value = []
  batchSettlementResults.value = []
  isUploading.value = true
  uploadError.value = ''
  uploadProgressText.value = '파일 분석 중...'
  batchUploadResults.value = []

  try {
    const data = await uploadOneFile(file)
    await applyUploadData(data)
    currentStep.value = 1
  } catch (e) {
    uploadError.value = e.response?.data?.detail || '업로드 실패'
  } finally {
    isUploading.value = false
    uploadProgressText.value = ''
  }
}

const processFiles = async (fileList) => {
  if (!isFileUploadMode.value) {
    uploadError.value = '이 화주사의 파일 업로드 로직은 아직 지원하지 않습니다.'
    return
  }
  const selectedFiles = Array.from(fileList || [])
  if (selectedFiles.length === 0) return

  batchMode.value = false
  batchUploads.value = []
  batchOvertimeGroups.value = []
  batchSettlementResults.value = []

  const files = getExcelFiles(selectedFiles)
  if (files.length === 0) {
    uploadError.value = '.xlsx 파일만 업로드 가능합니다.'
    return
  }

  if (files.length !== selectedFiles.length) {
    uploadError.value = '엑셀 파일이 아닌 항목은 제외하고 업로드합니다.'
  } else {
    uploadError.value = ''
  }

  if (files.length === 1) {
    await processFile(files[0])
    return
  }

  if (!await confirmDuplicateUploads(files)) return

  isUploading.value = true
  uploadProgressText.value = `0/${files.length}개 업로드 준비 중...`
  batchUploadResults.value = []
  const successfulUploads = []

  for (let index = 0; index < files.length; index += 1) {
    const file = files[index]
    uploadProgressText.value = `${index + 1}/${files.length}개 업로드 중: ${file.name}`
    try {
      const data = await uploadOneFile(file)
      successfulUploads.push(data)
      batchUploadResults.value.push({ key: `${index}-${file.name}`, name: file.name, ok: true, message: '완료', upload_id: data.id })
    } catch (e) {
      batchUploadResults.value.push({
        key: `${index}-${file.name}`,
        name: file.name,
        ok: false,
        message: e.response?.data?.detail || '실패',
      })
    }
  }

  const failedCount = batchUploadResults.value.filter(result => !result.ok).length
  uploadError.value = failedCount > 0 ? `${failedCount}개 파일 업로드에 실패했습니다.` : ''
  uploadProgressText.value = ''
  isUploading.value = false
  await loadHistory()

  if (successfulUploads.length > 0) {
    prepareBatchSettlement(successfulUploads)
  }
}

const buildCrewOvertimeList = () => {
  const registeredCodes = new Set()
  if (detectedInfo.value) {
    for (const c of detectedInfo.value.crew_members || []) {
      if (!c.is_new) registeredCodes.add(c.code)
    }
  }

  // 팀 기본 특근비
  const defaultOT = teamPricingList.value.length > 0 ? (teamPricingList.value[0]._overtime_cost || 0) : 0

  const crewMap = {}
  for (const rec of uploadRecords.value) {
    if (!rec.manager_name || !rec.sub_region) continue
    if (!registeredCodes.has(rec.manager_name)) continue
    if (!crewMap[rec.manager_name]) {
      crewMap[rec.manager_name] = { name: rec.manager_name, regions: new Set(), totalBoxes: 0, isOvertime: false, overtimeCost: defaultOT }
    }
    for (const r of rec.sub_region.split(',').map(s => s.trim()).filter(s => s && s !== '-')) {
      crewMap[rec.manager_name].regions.add(r)
    }
    crewMap[rec.manager_name].totalBoxes += rec.boxes || 0
  }

  crewOvertimeList.value = Object.values(crewMap)
    .filter(c => c.totalBoxes > 0)
    .map(c => ({ ...c, regions: Array.from(c.regions) }))
}

const handleNextStep = async () => {
  isProcessing.value = true
  processError.value = ''
  try {
    if (currentStep.value === 1) {
      // 팀 단가 + 배송원 등록
      const teams = teamPricingList.value.map(t => ({
        id: t.id, receive_price: t._receive_price || 0, pay_price: t._pay_price || 0, default_overtime_cost: t._overtime_cost || 0
      }))
      const crew = newCrewList.value.map(c => ({
        code: c.code, name: c.name || c.code, phone: '', vehicle_number: '',
        pay_price: c._pay_price || 0,
        yongcha_pay_price: c._yongcha_pay_price || 0,
        is_yongcha: isCrewYongchaCandidate(c)
      }))

      await client.post(`/dispatch/uploads/${uploadId.value}/configure/`, { teams, crew })

      const infoResp = await getDetectedInfo(uploadId.value)
      detectedInfo.value = infoResp.data
      buildCrewOvertimeList()
      currentStep.value = 2
    } else if (currentStep.value === 2) {
      const crewData = crewOvertimeList.value.map(c => ({
        name: c.name, is_overtime: c.isOvertime, overtime_cost: c.isOvertime ? (c.overtimeCost || 0) : 0
      }))
      await setOvertime(uploadId.value, crewData)
      currentStep.value = 3
    }
  } catch (e) {
    processError.value = e.response?.data?.detail || '처리 오류'
  } finally {
    isProcessing.value = false
  }
}

const buildBatchCrewPayload = (upload) => {
  return (upload.detected_info?.crew_members || [])
    .filter(crew => crew.is_new)
    .map(crew => {
      const batchCrew = newCrewList.value.find(item => item.batch_key === makeBatchCrewKey(upload.team, crew.code))
      const source = batchCrew || crew
      return {
        code: crew.code,
        name: crew.name || crew.code,
        phone: crew.phone || '',
        vehicle_number: crew.vehicle_number || '',
        pay_price: Number(source._pay_price || source.pay_price || 0),
        yongcha_pay_price: Number(source._yongcha_pay_price || source.yongcha_pay_price || 3000),
        is_yongcha: isCrewYongchaCandidate(source),
      }
    })
}

const buildBatchOvertimePayload = (upload) => {
  const group = batchOvertimeGroups.value.find(item => item.upload_id === upload.id)
  if (!group) return []
  return group.crew.map(person => ({
    name: person.name,
    is_overtime: person.isOvertime,
    overtime_cost: person.isOvertime ? (person.overtimeCost || 0) : 0,
  }))
}

const handleBatchFinalize = async () => {
  if (batchUploads.value.length === 0) return

  isProcessing.value = true
  processError.value = ''
  batchSettlementResults.value = []

  const teams = teamPricingList.value.map(t => ({
    id: t.id,
    receive_price: t._receive_price || 0,
    pay_price: t._pay_price || 0,
    default_overtime_cost: t._overtime_cost || 0,
  }))

  for (const upload of batchUploads.value) {
    try {
      await configureAll(upload.id, {
        teams,
        crew: buildBatchCrewPayload(upload),
      })
      await setOvertime(upload.id, buildBatchOvertimePayload(upload))
      const response = await finalizeUpload(upload.id, {})
      const settlement = response.data?.settlement
      batchSettlementResults.value.push({
        upload_id: upload.id,
        name: upload.original_filename || '배차파일',
        ok: true,
        detail: settlement
          ? `${settlement.period_start} / ${settlement.team} / ${formatCurrency(Number(settlement.total_receive || 0))}원`
          : '정산 생성 완료',
      })
    } catch (e) {
      batchSettlementResults.value.push({
        upload_id: upload.id,
        name: upload.original_filename || '배차파일',
        ok: false,
        detail: e.response?.data?.detail || '정산 생성 실패',
      })
    }
  }

  const failedCount = batchSettlementResults.value.filter(result => !result.ok).length
  if (failedCount > 0) {
    processError.value = `${failedCount}개 파일 정산 생성에 실패했습니다.`
  }

  isProcessing.value = false
  await loadHistory()
}

const handleFinalize = async () => {
  isProcessing.value = true
  processError.value = ''
  try {
    const resp = await finalizeUpload(uploadId.value, {})
    settlementResult.value = resp.data
  } catch (e) {
    processError.value = e.response?.data?.detail || '정산 생성 실패'
  } finally {
    isProcessing.value = false
  }
}

const resetUpload = () => {
  currentStep.value = 0; uploadId.value = null; detectedInfo.value = null
  uploadRecords.value = []; newCrewList.value = []; dispatchDate.value = null
  teamPricingList.value = []; crewOvertimeList.value = []
  settlementResult.value = null; uploadError.value = ''; processError.value = ''
  uploadProgressText.value = ''; batchUploadResults.value = []
  batchMode.value = false; batchUploads.value = []; batchOvertimeGroups.value = []; batchSettlementResults.value = []
  expandedCrewCode.value = null; loadHistory()
}

const resumeUpload = async (upload) => {
  batchMode.value = false
  batchUploads.value = []
  batchOvertimeGroups.value = []
  batchSettlementResults.value = []
  isUploading.value = true
  uploadError.value = ''
  try {
    uploadId.value = upload.id
    dispatchDate.value = upload.dispatch_date || null

    // detected_info 로드
    const infoResp = await getDetectedInfo(upload.id)
    detectedInfo.value = infoResp.data

    teamPricingList.value = (infoResp.data.teams || []).map(t => ({
      ...t,
      _receive_price: t.receive_price || 0,
      _pay_price: t.pay_price || 0,
      _overtime_cost: t.default_overtime_cost || 0,
    }))

    newCrewList.value = (infoResp.data.crew_members || [])
      .filter(c => c.is_new)
      .map(c => ({
        ...c,
        _pay_price: Number(c.pay_price || 0),
        _yongcha_pay_price: Number(c.yongcha_pay_price || 3000),
      }))

    // records 로드
    const recResp = await getRecords(upload.id)
    uploadRecords.value = recResp.data.results || recResp.data || []

    currentStep.value = 1
  } catch (e) {
    uploadError.value = e.response?.data?.detail || '데이터 로드 실패'
  } finally {
    isUploading.value = false
  }
}

const deleteUpload = async (upload) => {
  const name = upload.original_filename || '배차파일'
  if (!confirm(`"${name}" 업로드를 삭제하시겠습니까?\n연관된 정산 데이터도 함께 삭제됩니다.`)) return
  try {
    await client.delete(`/dispatch/uploads/${upload.id}`)
    loadHistory()
  } catch (e) {
    alert(e.response?.data?.detail || '삭제 실패')
  }
}

const downloadUploadFile = async (upload) => {
  try {
    const response = await downloadDispatchFile(upload.id)
    const blob = new Blob([response.data], {
      type: response.headers?.['content-type'] || 'application/octet-stream'
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = upload.original_filename || `dispatch_${upload.id}.xlsx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    alert(e.response?.data?.detail || '원본 배차표 다운로드 실패')
  }
}

const loadHistory = async () => {
  uploadHistoryLoading.value = true
  uploadHistoryError.value = ''
  try {
    const r = await fetchUploads({ summary: 1 })
    uploadHistory.value = r.data.results || r.data || []
    uploadHistoryLoaded.value = true
  } catch (e) {
    uploadHistoryError.value = e.response?.data?.detail || '업로드 이력을 불러오지 못했습니다.'
  } finally {
    uploadHistoryLoading.value = false
  }
}

const refreshHistory = async () => {
  await loadHistory()
}

watch(selectedShipper, async (shipper) => {
  if (shipper) {
    setSelectedShipperCode(companyAppCode.value, shipper)
  }
  if (isOneShipper.value) {
    await router.push(`${getCompanyAppFromRoute(route).routeBase}/settlement`)
    return
  }
  textPreview.value = null
  textError.value = ''
  textTeamId.value = ''
  await loadTextTeams()
})

watch([textDateBasis, textDispatchDate, textRoundCode, textTeamId, textRaw], () => {
  if (isTextUploadMode.value) scheduleTextPreview()
})

onMounted(async () => {
  window.addEventListener(SHIPPER_CONTEXT_CHANGED_EVENT, handleShipperContextChanged)
  loadShipperOptions()
  await nextTick()
  window.setTimeout(() => {
    loadHistory()
  }, 0)
})

onBeforeUnmount(() => {
  window.removeEventListener(SHIPPER_CONTEXT_CHANGED_EVENT, handleShipperContextChanged)
})
</script>
