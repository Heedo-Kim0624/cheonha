<template>
  <div class="fleet-page">
    <aside class="fleet-sidebar">
      <RouterLink to="/portal/operations" class="back-link">운영 통합관리로 돌아가기</RouterLink>
      <div class="quick-links" aria-label="운영 바로가기">
        <RouterLink to="/portal/companies">회사 목록</RouterLink>
        <RouterLink to="/company/new/settlement?one_tab=upload">새회사 오네 정산</RouterLink>
      </div>

      <div class="brand">
        <span class="brand-mark">CL</span>
        <div>
          <p>CLEVER</p>
          <h1>차량관리</h1>
        </div>
      </div>

      <label class="company-select">
        <span>차량 회사</span>
        <select v-model="selectedCompany" @change="reload">
          <option v-for="company in companies" :key="company.code" :value="company.code">
            {{ company.name }}
          </option>
        </select>
      </label>

      <nav class="fleet-nav" aria-label="차량관리 메뉴">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeTab === tab.key }"
          @click="goTab(tab.key)"
        >
          <span>{{ tab.label }}</span>
          <small>{{ tab.caption }}</small>
        </button>
      </nav>

      <a class="legacy-link" :href="legacyUrl">기존 전체 기능 화면 열기</a>
    </aside>

    <main class="fleet-main">
      <header class="topbar">
        <div>
          <p class="eyebrow">FLEET MANAGEMENT</p>
          <h2>{{ currentTab?.label || '차량관리' }}</h2>
          <p>{{ currentTab?.caption || '차량 운영 데이터를 관리합니다.' }}</p>
        </div>
        <div class="top-actions">
          <input v-model="search" type="search" placeholder="차량번호, 차대번호, 고객명 검색" />
          <select v-model="statusFilter" aria-label="상태 필터">
            <option value="">전체 상태</option>
            <option v-for="status in statusChoices" :key="status" :value="status">{{ status }}</option>
          </select>
          <button type="button" class="btn" :disabled="loading" @click="reload">
            {{ loading ? '불러오는 중' : '새로고침' }}
          </button>
        </div>
      </header>

      <div v-if="error" class="alert">{{ error }}</div>

      <section v-if="activeTab === 'dashboard'" class="content-stack">
        <div class="metric-grid">
          <button
            v-for="metric in dashboardMetrics"
            :key="metric.key"
            type="button"
            class="metric-card"
            @click="focusMetric(metric.key)"
          >
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
            <small>{{ metric.caption }}</small>
          </button>
        </div>

        <section class="panel">
          <div class="panel-head">
            <div>
              <h3>차량 운영 현황</h3>
              <p>차량번호 기준으로 계약, 반납, 보험, 사고 이력을 묶어서 봅니다.</p>
            </div>
          </div>
          <FleetVehicleTable
            :groups="filteredGroups"
            :selected-plate="selectedPlate"
            :status-choices="statusChoices"
            @select="selectGroup"
            @status="saveStatus"
          />
        </section>
      </section>

      <section v-else-if="activeTab === 'vehicles'" class="content-stack">
        <section v-if="!selectedGroup" class="panel">
          <div class="panel-head">
            <div>
              <h3>차량 목록</h3>
              <p>차량번호 옆 상태값을 바로 바꾸고, 차량별 통합 이력을 확인합니다.</p>
            </div>
            <button class="btn primary" type="button" @click="openCreateVehicle">차량 추가</button>
          </div>
          <FleetVehicleTable
            :groups="filteredGroups"
            :selected-plate="selectedPlate"
            :status-choices="statusChoices"
            @select="selectGroup"
            @status="saveStatus"
          />
        </section>

        <section v-else class="vehicle-detail-page">
          <button type="button" class="btn back-button" @click="selectedPlate = ''">← 차량목록</button>

          <div class="vehicle-hero">
            <div>
              <small>차량번호 기준 통합 상세</small>
              <h2>{{ selectedGroup.plate }}</h2>
              <p>현재 차대번호 {{ currentRecord(selectedGroup)?.vin || '-' }} · {{ currentRecord(selectedGroup)?.model || '-' }}</p>
            </div>

            <div class="hero-status">
              <span>운영 상태</span>
              <select :value="fleetState(selectedGroup)" @change="saveStatus(selectedGroup, $event.target.value)">
                <option v-for="status in statusChoices" :key="status" :value="status">{{ status }}</option>
              </select>
            </div>

            <div class="hero-actions">
              <button class="btn" type="button" @click="openVehicleEdit(selectedGroup)">차량 정보 변경</button>
              <button class="btn danger" type="button" @click="openVehicleDelete(selectedGroup)">차량 삭제</button>
              <button class="btn" type="button" @click="openDocuments(selectedGroup)">자동차등록증</button>
              <button class="btn" type="button" @click="openSubscription(selectedGroup)">구독 계약</button>
              <button class="btn" type="button" @click="openReturn(selectedGroup)">반납 접수</button>
              <button class="btn" type="button" @click="openInsurance(selectedGroup)">보험 등록</button>
              <button class="btn primary" type="button" @click="openReplacement(selectedGroup)">대폐차</button>
            </div>
          </div>

          <div class="detail-tabs">
            <button
              v-for="mode in detailModes"
              :key="mode.key"
              type="button"
              :class="{ active: detailMode === mode.key }"
              @click="detailMode = mode.key"
            >
              {{ mode.label }}
            </button>
          </div>

          <div class="summary-grid">
            <div class="mini-card">
              <span>{{ detailModeLabel }} 사고건수</span>
              <strong>{{ selectedAccidentStats.count }}건</strong>
            </div>
            <div class="mini-card">
              <span>최종 사고일</span>
              <strong>{{ date(selectedAccidentStats.last) }}</strong>
            </div>
            <div class="mini-card">
              <span>보상금액</span>
              <strong>{{ money(selectedAccidentStats.comp) }}</strong>
            </div>
            <div class="mini-card">
              <span>지급금액</span>
              <strong>{{ money(selectedAccidentStats.paid) }}</strong>
            </div>
            <div class="mini-card">
              <span>미수채권</span>
              <strong>{{ money(selectedRepairStats.unpaid) }}</strong>
            </div>
          </div>

          <div class="detail-grid-two">
            <section class="panel">
              <div class="panel-head">
                <div>
                  <h3>현재 차량 정보</h3>
                  <p>실제 차량 ID·차대번호 기준</p>
                </div>
                <span class="badge green">{{ fleetState(selectedGroup) }}</span>
              </div>
              <div class="info-grid">
                <div><span>차량 내부 ID</span><strong>{{ currentRecord(selectedGroup)?.id || '-' }}</strong></div>
                <div><span>차대번호</span><strong>{{ currentRecord(selectedGroup)?.vin || '-' }}</strong></div>
                <div><span>차종</span><strong>{{ currentRecord(selectedGroup)?.model || '-' }}</strong></div>
                <div><span>호기번호</span><strong>{{ currentRecord(selectedGroup)?.unitNumber || currentRecord(selectedGroup)?.hgi || '-' }}</strong></div>
                <div><span>운행 시작일</span><strong>{{ date(currentRecord(selectedGroup)?.start) }}</strong></div>
                <div><span>현재 구독자</span><strong>{{ activeSubscription(selectedGroup)?.customer || '미구독' }}</strong></div>
                <div><span>소유자</span><strong>{{ selectedGroup.owner || '-' }}</strong></div>
              </div>
              <div class="doc-row">
                <div>
                  <strong>{{ registrationDocument(selectedGroup)?.name || '자동차등록증 미등록' }}</strong>
                  <small>{{ registrationDocument(selectedGroup)?.uploaded ? `업로드 ${date(registrationDocument(selectedGroup)?.uploaded)}` : '서류 업로드가 필요합니다.' }}</small>
                </div>
                <button class="btn soft" type="button" @click="openDocuments(selectedGroup)">보기/업로드</button>
              </div>
            </section>

            <section class="panel">
              <div class="panel-head">
                <div>
                  <h3>차량번호 사용 이력</h3>
                  <p>대폐차 전·후 차대번호와 등록증을 분리합니다.</p>
                </div>
              </div>
              <div class="timeline">
                <div v-for="record in vehicleTimeline" :key="record.id" class="timeline-row" :class="{ current: !record.end }">
                  <div class="line-dot"></div>
                  <div>
                    <strong>{{ !record.end ? '현재 차량' : '이전 차량' }} · {{ record.model || '-' }}</strong>
                    <p>{{ record.vin || '-' }}<br>{{ date(record.start) }} ~ {{ record.end ? date(record.end) : '현재' }}</p>
                  </div>
                  <button class="btn soft" type="button" @click="openDocuments(selectedGroup, record)">등록증</button>
                </div>
              </div>
            </section>
          </div>

          <div class="detail-grid-two">
            <section class="panel">
              <div class="panel-head">
                <div>
                  <h3>구독·전자계약 이력</h3>
                  <p>실제 차량별 전자계약서를 보관합니다.</p>
                </div>
                <button class="btn primary" type="button" @click="openSubscription(selectedGroup)">＋ 계약</button>
              </div>
              <div v-if="selectedGroup.subscriptions?.length" class="stack-list">
                <div v-for="item in selectedGroup.subscriptions" :key="item.id" class="doc-row">
                  <div>
                    <strong>{{ item.id }} · {{ item.customer || '-' }}</strong>
                    <small>{{ date(item.start) }} ~ {{ date(item.end) }} · {{ item.signStatus || '-' }}</small>
                  </div>
                  <button class="btn soft" type="button" @click="openSubscriptionDetail(item)">상세</button>
                </div>
              </div>
              <div v-else class="empty-box">계약 없음</div>
            </section>

            <section class="panel">
              <div class="panel-head">
                <div>
                  <h3>반납·수리비 이력</h3>
                  <p>사진·검수·청구를 통합합니다.</p>
                </div>
                <button class="btn primary" type="button" @click="openReturn(selectedGroup)">＋ 반납</button>
              </div>
              <div v-if="selectedGroup.returns?.length" class="stack-list">
                <div v-for="item in selectedGroup.returns" :key="item.id" class="doc-row">
                  <div>
                    <strong>{{ item.id }} · {{ item.status || '-' }}</strong>
                    <small>{{ datetime(item.scheduled) }} · 사진 {{ item.photos?.length || 0 }}장 · 청구 {{ money(returnTotals(item).claim) }}</small>
                  </div>
                  <button class="btn soft" type="button" @click="openReturnDetail(item)">상세</button>
                </div>
              </div>
              <div v-else class="empty-box">반납 이력 없음</div>
            </section>
          </div>

          <section class="panel">
            <div class="panel-head">
              <div>
                <h3>보험료 납부 현황</h3>
                <p>현재 차량 보험의 다음 납부일과 적용 요율을 관리합니다.</p>
              </div>
              <button class="btn primary" type="button" @click="openInsurance(selectedGroup)">＋ 보험 등록</button>
            </div>
            <div v-if="selectedGroup.insurances?.length" class="stack-list">
              <div v-for="item in selectedGroup.insurances" :key="item.id" class="doc-row">
                <div>
                  <strong>{{ item.insurer || '-' }} · {{ item.policyNo || '-' }}</strong>
                  <small>{{ date(item.start) }} ~ {{ date(item.end) }} · 요율 {{ item.currentRate ?? 0 }}%</small>
                </div>
                <button class="btn soft" type="button" @click="openInsuranceDetail(item)">상세</button>
              </div>
            </div>
            <div v-else class="empty-box">보험 계약이 없습니다.</div>
          </section>

          <section class="panel">
            <div class="panel-head">
              <div>
                <h3>{{ detailModeLabel }}</h3>
                <p>사고번호 클릭 시 보상/담보 상세를 수정할 수 있습니다.</p>
              </div>
            </div>
            <div class="table-wrap">
              <table class="detail-table">
                <thead>
                  <tr>
                    <th>사고번호</th>
                    <th>실제 차대번호</th>
                    <th>사고일시</th>
                    <th>운전자</th>
                    <th>사고장소</th>
                    <th class="money-cell">보상금액</th>
                    <th class="money-cell">지급금액</th>
                    <th>상태</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!selectedAccidentStats.list.length">
                    <td colspan="8" class="empty-cell">해당 조건의 사고가 없습니다.</td>
                  </tr>
                  <tr v-for="item in selectedAccidentStats.list" :key="item.id" @click="openAccidentDetail(item)">
                    <td class="strong">{{ item.id }}</td>
                    <td>{{ shortVin(item.vin) }}</td>
                    <td>{{ datetime(item.date) }}</td>
                    <td>{{ item.driver || '-' }}</td>
                    <td>{{ item.location || '-' }}</td>
                    <td class="money-cell">{{ money(item.compensation) }}</td>
                    <td class="money-cell">{{ money(item.paid) }}</td>
                    <td>{{ item.status || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </section>
      </section>

      <section v-else-if="activeTab === 'subscriptions'" class="panel">
        <div class="panel-head">
          <div>
            <h3>구독 전자계약</h3>
            <p>계약 기간, 구독료, 서명 상태를 차량번호 기준으로 확인합니다.</p>
          </div>
        </div>
        <SimpleTable :columns="subscriptionColumns" :rows="filteredSubscriptions" empty-text="구독 계약 이력이 없습니다." />
      </section>

      <section v-else-if="activeTab === 'returns'" class="panel">
        <div class="panel-head">
          <div>
            <h3>반납/수리비</h3>
            <p>반납 일정, 실제 반납일, 수리비 청구 이력을 확인합니다.</p>
          </div>
        </div>
        <SimpleTable :columns="returnColumns" :rows="filteredReturns" empty-text="반납/수리비 이력이 없습니다." />
      </section>

      <section v-else-if="activeTab === 'insurance'" class="panel">
        <div class="panel-head">
          <div>
            <h3>보험료 납부 현황</h3>
            <p>보험사, 증권번호, 가입 기간, 납부 상태를 관리합니다.</p>
          </div>
        </div>
        <SimpleTable :columns="insuranceColumns" :rows="filteredInsurances" empty-text="보험 이력이 없습니다." />
      </section>

      <section v-else-if="activeTab === 'accidents'" class="panel">
        <div class="panel-head">
          <div>
            <h3>사고 관리</h3>
            <p>사고관리대장과 보상상세내역을 하나의 사고 이력으로 봅니다.</p>
          </div>
          <button class="btn" type="button" @click="downloadAccidentTemplate">통합 양식 다운로드</button>
        </div>
        <SimpleTable :columns="accidentColumns" :rows="filteredAccidents" empty-text="사고 이력이 없습니다." />
      </section>

      <section v-else class="panel">
        <div class="panel-head">
          <div>
            <h3>엑셀 업로드</h3>
            <p>사고관리 통합 양식은 Vue에서 바로 다운로드하고, 대량 업로드는 기존 화면을 임시 연결합니다.</p>
          </div>
        </div>
        <div class="upload-bridge">
          <button class="btn" type="button" @click="downloadAccidentTemplate">사고 이력 통합 양식 다운로드</button>
          <a class="btn primary" :href="legacyUrl">기존 업로드 화면 열기</a>
        </div>
      </section>

      <div v-if="modal.open" class="modal-backdrop" @click.self="closeModal">
        <div class="modal-card" :class="{ wide: modal.wide }">
          <div class="modal-head">
            <div>
              <h3>{{ modal.title }}</h3>
              <p v-if="modal.caption">{{ modal.caption }}</p>
            </div>
            <button type="button" class="modal-close" @click="closeModal">×</button>
          </div>

          <form class="modal-body" @submit.prevent="submitModal">
            <template v-if="modal.type === 'vehicle-create' || modal.type === 'vehicle-edit'">
              <div class="form-grid">
                <label><span>차량번호</span><input v-model="form.vehicleNumber" required></label>
                <label><span>차대번호</span><input v-model="form.vin" required></label>
                <label><span>차종</span><input v-model="form.model"></label>
                <label><span>호기번호</span><input v-model="form.unitNumber"></label>
                <label><span>운영 상태</span><select v-model="form.status"><option v-for="status in statusChoices" :key="status">{{ status }}</option></select></label>
                <label><span>운행 시작일</span><input v-model="form.start" type="date"></label>
                <label class="full"><span>비고</span><textarea v-model="form.note"></textarea></label>
              </div>
            </template>

            <template v-else-if="modal.type === 'vehicle-delete'">
              <p class="danger-text">{{ form.vehicleNumber }} 차량을 삭제합니다. 이 작업은 되돌릴 수 없습니다.</p>
            </template>

            <template v-else-if="modal.type === 'documents'">
              <div class="document-list">
                <div v-for="docType in documentTypes" :key="docType.key" class="document-card">
                  <div>
                    <strong>{{ docType.label }}</strong>
                    <small>{{ documentByType(form.group, docType.key)?.name || '미등록' }}</small>
                  </div>
                  <div class="inline-actions">
                    <button type="button" class="btn soft" @click="previewFile(documentByType(form.group, docType.key))">미리보기</button>
                    <button type="button" class="btn" @click="downloadFile(documentByType(form.group, docType.key))">다운로드</button>
                    <label class="btn primary file-btn">
                      업로드·교체
                      <input type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" hidden @change="uploadDocument(docType.key, $event)">
                    </label>
                    <button type="button" class="btn danger" @click="removeDocument(docType.key)">삭제</button>
                  </div>
                </div>
              </div>
            </template>

            <template v-else-if="modal.type === 'subscription' || modal.type === 'subscription-detail'">
              <div class="form-grid">
                <label><span>차량번호</span><select v-model="form.plate" @change="syncFormRecord"><option v-for="group in groups" :key="group.plate">{{ group.plate }}</option></select></label>
                <label><span>실제 차량</span><select v-model="form.vehicleRecordId"><option v-for="record in recordsForPlate(form.plate)" :key="record.id" :value="record.id">{{ record.vin }} · {{ record.model }}</option></select></label>
                <label><span>구독자명/법인명</span><input v-model="form.customer" required></label>
                <label><span>연락처</span><input v-model="form.contact" placeholder="010-0000-0000"></label>
                <label><span>계약 시작일</span><input v-model="form.start" type="date" required></label>
                <label><span>계약 종료일</span><input v-model="form.end" type="date" required></label>
                <label><span>월 구독료</span><input v-model.number="form.monthlyFee" type="number" min="0"></label>
                <label><span>보증금</span><input v-model.number="form.deposit" type="number" min="0"></label>
                <label><span>계약상태</span><select v-model="form.status"><option>계약예정</option><option>구독중</option><option>종료</option><option>취소</option></select></label>
                <label><span>전자서명 상태</span><select v-model="form.signStatus"><option>미발송</option><option>서명대기</option><option>서명완료</option><option>문서없음</option></select></label>
                <label><span>전자계약서</span><input type="file" accept=".pdf,.doc,.docx,.jpg,.png" @change="form.file = $event.target.files?.[0] || null"></label>
                <label class="full"><span>특약·비고</span><textarea v-model="form.note"></textarea></label>
              </div>
              <div v-if="form.fileUrl || form.fileName" class="doc-row compact">
                <div><strong>{{ form.fileName || '계약서 파일' }}</strong><small>기존 계약 파일</small></div>
                <button type="button" class="btn soft" @click="previewFile({ url: form.fileUrl, name: form.fileName })">미리보기</button>
                <button type="button" class="btn" @click="downloadFile({ url: form.fileUrl, name: form.fileName })">다운로드</button>
              </div>
            </template>

            <template v-else-if="modal.type === 'return' || modal.type === 'return-detail'">
              <div class="form-grid">
                <label class="full"><span>구독 계약</span><select v-model="form.subscriptionId" @change="syncReturnContract"><option v-for="item in subscriptionCandidates" :key="item.id" :value="item.id">{{ item.id }} · {{ item.plate }} · {{ item.customer }}</option></select></label>
                <label><span>차량번호</span><input v-model="form.plate" readonly></label>
                <label><span>구독자</span><input v-model="form.customer" readonly></label>
                <label><span>반납 예정일</span><input v-model="form.scheduled" type="datetime-local" required></label>
                <label><span>실제 반납일</span><input v-model="form.actual" type="datetime-local"></label>
                <label class="full"><span>반납 장소</span><input v-model="form.location"></label>
                <label><span>진행 상태</span><select v-model="form.status"><option>반납예정</option><option>검수중</option><option>수리비청구</option><option>완료</option><option>취소</option></select></label>
                <label class="full"><span>검수 특이사항</span><textarea v-model="form.note"></textarea></label>
              </div>
              <div class="photo-grid">
                <div v-for="(photo, index) in form.photos" :key="photo.label" class="photo-card" :class="{ uploaded: photo.name }">
                  <strong>{{ photo.label }}</strong>
                  <small>{{ photo.name || '파일 없음' }}</small>
                  <div class="inline-actions compact-actions">
                    <button type="button" class="btn soft" @click="previewFile(photo)">미리보기</button>
                    <button type="button" class="btn" @click="downloadFile(photo)">다운로드</button>
                    <label class="btn primary file-btn">교체<input type="file" accept="image/*" hidden @change="setReturnPhoto(index, $event)"></label>
                    <button type="button" class="btn danger" @click="clearReturnPhoto(index)">삭제</button>
                  </div>
                </div>
              </div>
              <div class="repair-section">
                <div class="panel-head no-margin">
                  <h3>수리비 항목</h3>
                  <button type="button" class="btn primary" @click="addRepairRow">＋ 수리 항목 추가</button>
                </div>
                <div class="table-wrap">
                  <table class="detail-table">
                    <thead><tr><th>수리 항목</th><th>업체</th><th>실제 수리비</th><th>고객 청구액</th><th>입금상태</th><th>관리</th></tr></thead>
                    <tbody>
                      <tr v-for="(repair, index) in form.repairs" :key="index">
                        <td><input v-model="repair.item"></td>
                        <td><input v-model="repair.vendor"></td>
                        <td><input v-model.number="repair.cost" type="number" min="0"></td>
                        <td><input v-model.number="repair.claim" type="number" min="0"></td>
                        <td><select v-model="repair.payment"><option>미청구</option><option>청구</option><option>입금완료</option><option>취소</option></select></td>
                        <td><button type="button" class="btn danger" @click="form.repairs.splice(index, 1)">삭제</button></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </template>

            <template v-else-if="modal.type === 'insurance' || modal.type === 'insurance-detail'">
              <div class="form-grid">
                <label><span>차량번호</span><select v-model="form.plate" @change="syncFormRecord"><option v-for="group in groups" :key="group.plate">{{ group.plate }}</option></select></label>
                <label><span>실제 차량</span><select v-model="form.vehicleRecordId"><option v-for="record in recordsForPlate(form.plate)" :key="record.id" :value="record.id">{{ record.vin }} · {{ record.model }}</option></select></label>
                <label><span>보험사</span><input v-model="form.insurer" required></label>
                <label><span>증권번호</span><input v-model="form.policyNo"></label>
                <label><span>보험 시작일</span><input v-model="form.start" type="date"></label>
                <label><span>보험 종료일</span><input v-model="form.end" type="date"></label>
                <label><span>이전 요율</span><input v-model.number="form.previousRate" type="number" step="0.1"></label>
                <label><span>적용 요율</span><input v-model.number="form.currentRate" type="number" step="0.1"></label>
                <label><span>보험 상태</span><select v-model="form.status"><option>가입중</option><option>종료</option><option>해지</option><option>대기</option></select></label>
                <label class="full"><span>비고</span><textarea v-model="form.note"></textarea></label>
              </div>
              <div v-if="modal.type === 'insurance-detail'" class="modal-extra-actions">
                <button type="button" class="btn danger" @click="removeInsurance">보험 삭제</button>
              </div>
            </template>

            <template v-else-if="modal.type === 'replacement'">
              <div class="form-grid">
                <label class="full"><span>기존 차량번호</span><input v-model="form.vehicleNumber" readonly></label>
                <label><span>기존 차량 종료일</span><input v-model="form.oldEnd" type="date" required></label>
                <label><span>신규 차량 시작일</span><input v-model="form.newStart" type="date" required></label>
                <label class="full"><span>신규 차량번호</span><input v-model="form.newVehicleNumber" required placeholder="예: 전북91사4816"></label>
                <label><span>차대번호(동일)</span><input v-model="form.vin" readonly></label>
                <label><span>차종</span><input v-model="form.model"></label>
                <label><span>자동차등록증</span><input type="file" accept=".pdf,.jpg,.jpeg,.png" @change="form.file = $event.target.files?.[0] || null"></label>
              </div>
            </template>

            <template v-else-if="modal.type === 'accident-detail'">
              <div class="form-grid">
                <label><span>사고번호</span><input v-model="form.id" readonly></label>
                <label><span>운전자</span><input v-model="form.driver"></label>
                <label><span>사고일시</span><input v-model="form.date" type="datetime-local"></label>
                <label><span>사고장소</span><input v-model="form.location"></label>
                <label><span>담보</span><input v-model="form.coverage"></label>
                <label><span>상태</span><input v-model="form.status"></label>
                <label><span>대인 보상</span><input v-model.number="form.personalCompensation" type="number" min="0"></label>
                <label><span>대물 보상</span><input v-model.number="form.propertyCompensation" type="number" min="0"></label>
                <label><span>총 보상금액</span><input v-model.number="form.compensation" type="number" min="0"></label>
                <label><span>지급금액</span><input v-model.number="form.paid" type="number" min="0"></label>
                <label class="full"><span>사고내용</span><textarea v-model="form.description"></textarea></label>
                <label class="full"><span>보상 메모</span><textarea v-model="form.compensationNote"></textarea></label>
              </div>
            </template>

            <div v-if="modal.type !== 'documents'" class="modal-foot">
              <button type="button" class="btn" @click="closeModal">취소</button>
              <button type="submit" class="btn primary" :disabled="saving">{{ saving ? '저장 중' : modal.submitLabel || '저장' }}</button>
            </div>
          </form>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import SimpleTable from '@/components/fleet/FleetSimpleTable.vue'
import FleetVehicleTable from '@/components/fleet/FleetVehicleTable.vue'
import { useFleetSite } from '@/composables/useFleetSite'
import {
  createFleetDocument,
  createFleetInsurance,
  createFleetReplacement,
  createFleetReturn,
  createFleetSubscription,
  createFleetVehicle,
  deleteFleetDocument,
  deleteFleetInsurance,
  deleteFleetVehicle,
  downloadFleetAccidentTemplate,
  updateFleetAccident,
  updateFleetDocument,
  updateFleetInsurance,
  updateFleetRecordStatus,
  updateFleetReturn,
  updateFleetSubscription,
  updateFleetVehicleInfo,
  updateFleetVehicleStatus,
  uploadFleetReturnPhoto,
} from '@/api/fleetManagement'

const tabs = [
  { key: 'dashboard', label: '대시보드', caption: '차량 운영 요약' },
  { key: 'vehicles', label: '차량 목록', caption: '차량번호별 통합 상세' },
  { key: 'subscriptions', label: '구독 전자계약', caption: '계약과 월 구독료' },
  { key: 'returns', label: '반납/수리비', caption: '반납과 청구 이력' },
  { key: 'insurance', label: '보험', caption: '보험료 납부 현황' },
  { key: 'accidents', label: '사고 관리', caption: '사고와 보상 이력' },
  { key: 'upload', label: '엑셀 업로드', caption: '양식 다운로드와 업로드' },
]

const routeNames = {
  dashboard: 'CleverPortalVehicleDashboard',
  vehicles: 'CleverPortalVehicleVehicles',
  subscriptions: 'CleverPortalVehicleSubscriptions',
  returns: 'CleverPortalVehicleReturns',
  insurance: 'CleverPortalVehicleInsurance',
  accidents: 'CleverPortalVehicleAccidents',
  upload: 'CleverPortalVehicleUpload',
}

const statusChoices = ['유휴', 'A/S', '판매', '구독', '직영']

const route = useRoute()
const router = useRouter()
const {
  companies,
  selectedCompany,
  fleetPayload,
  groups,
  loading,
  error,
  loadCompanies,
  reload,
} = useFleetSite('CHEONHA')
const search = ref('')
const statusFilter = ref('')
const selectedPlate = ref('')

const activeTab = computed(() => route.meta.fleetTab || 'dashboard')
const currentTab = computed(() => tabs.find((tab) => tab.key === activeTab.value))
const legacyUrl = computed(() => `/fleet-management/?company=${encodeURIComponent(selectedCompany.value)}`)
const selectedGroup = computed(() => groups.value.find((group) => group.plate === selectedPlate.value))
const companyId = computed(() => fleetPayload.value?.company?.id || '')

const detailModes = [
  { key: 'all', label: '차량번호 전체 이력' },
  { key: 'current', label: '현재 차량 이력' },
  { key: 'previous', label: '이전 차량 이력' },
]

const documentTypes = [
  { key: 'registration_certificate', label: '차량 등록증' },
  { key: 'insurance_application', label: '보험 청약서' },
]

const returnPhotoLabels = ['전면', '후면', '좌측', '우측', '계기판', '실내', '냉동탑 내부', '파손 부위']
const detailMode = ref('all')
const saving = ref(false)
const modal = ref({ open: false, type: '', title: '', caption: '', submitLabel: '', wide: false })
const form = ref({})

const detailModeLabel = computed(() =>
  detailModes.find((item) => item.key === detailMode.value)?.label || '차량번호 전체 이력',
)
const vehicleTimeline = computed(() => [...(selectedGroup.value?.records || [])].reverse())
const selectedAccidentStats = computed(() => accidentStats(selectedGroup.value, detailMode.value))
const selectedRepairStats = computed(() => repairStats(selectedGroup.value))
const subscriptionCandidates = computed(() => {
  const scoped = selectedGroup.value?.subscriptions || []
  const active = scoped.filter((item) => ['구독중', '계약예정'].includes(item.status))
  return active.length ? active : scoped
})

const filteredGroups = computed(() => {
  const q = search.value.trim().toLowerCase()
  return groups.value.filter((group) => {
    const record = currentRecord(group)
    const statusMatched = !statusFilter.value || fleetState(group) === statusFilter.value
    if (!statusMatched) return false
    if (!q) return true
    const haystack = [
      group.plate,
      group.owner,
      record?.vin,
      record?.model,
      record?.unitNumber,
      ...(group.subscriptions || []).map((item) => item.customer),
      ...(group.accidents || []).map((item) => item.driver),
    ].join(' ').toLowerCase()
    return haystack.includes(q)
  })
})

const allSubscriptions = computed(() => groups.value.flatMap((group) =>
  (group.subscriptions || []).map((item) => ({
    plate: group.plate,
    customer: item.customer,
    period: `${item.start || '-'} ~ ${item.end || '-'}`,
    monthlyFee: money(item.monthlyFee),
    deposit: money(item.deposit),
    status: item.status || '-',
    signStatus: item.signStatus || '-',
  })),
))

const allReturns = computed(() => groups.value.flatMap((group) =>
  (group.returns || []).map((item) => ({
    plate: group.plate,
    customer: item.customer || '-',
    scheduled: item.scheduled || '-',
    actual: item.actual || '-',
    location: item.location || '-',
    status: item.status || '-',
    repairCount: Array.isArray(item.repairs) ? `${item.repairs.length}건` : '0건',
  })),
))

const allInsurances = computed(() => groups.value.flatMap((group) =>
  (group.insurances || []).map((item) => ({
    plate: group.plate,
    insurer: item.insurer || '-',
    policyNo: item.policyNo || '-',
    period: `${item.start || '-'} ~ ${item.end || '-'}`,
    status: item.status || '-',
    rate: `${item.previousRate ?? 0}% → ${item.currentRate ?? 0}%`,
  })),
))

const allAccidents = computed(() => groups.value.flatMap((group) =>
  (group.accidents || []).map((item) => ({
    plate: group.plate,
    driver: item.driver || '-',
    date: item.date || '-',
    location: item.location || '-',
    coverage: item.coverage || '-',
    compensation: money(item.compensation),
    status: item.status || '-',
  })),
))

const filteredSubscriptions = computed(() => filterRows(allSubscriptions.value))
const filteredReturns = computed(() => filterRows(allReturns.value))
const filteredInsurances = computed(() => filterRows(allInsurances.value))
const filteredAccidents = computed(() => filterRows(allAccidents.value))

const dashboardMetrics = computed(() => {
  const activeContracts = allSubscriptions.value.filter((item) => item.status.includes('구독') || item.status.toLowerCase().includes('active')).length
  const dueReturns = groups.value.filter((group) => {
    return (group.returns || []).some((item) => withinDays(item.scheduled, 7))
  }).length
  const missingDocs = groups.value.filter((group) => !hasRequiredDocuments(group)).length
  const repairClaims = groups.value.reduce((sum, group) => sum + (group.returns || []).reduce((inner, item) => inner + (Array.isArray(item.repairs) ? item.repairs.length : 0), 0), 0)
  return [
    { key: 'all', label: '전체 차량', value: `${groups.value.length}대`, caption: '등록된 차량번호 기준' },
    { key: 'subscribed', label: '구독 중', value: `${activeContracts}건`, caption: '진행 계약 기준' },
    { key: 'returns_due', label: '7일 내 반납 예정', value: `${dueReturns}대`, caption: '예정일 기준' },
    { key: 'missing_docs', label: '필수 서류 미비', value: `${missingDocs}대`, caption: '등록증/보험 청약서' },
    { key: 'repair_claims', label: '수리비 청구', value: `${repairClaims}건`, caption: '반납·수리 이력 기준' },
  ]
})

const subscriptionColumns = [
  { key: 'plate', label: '차량번호' },
  { key: 'customer', label: '고객' },
  { key: 'period', label: '기간' },
  { key: 'monthlyFee', label: '월 구독료', align: 'right' },
  { key: 'deposit', label: '보증금', align: 'right' },
  { key: 'status', label: '상태' },
  { key: 'signStatus', label: '서명' },
]

const returnColumns = [
  { key: 'plate', label: '차량번호' },
  { key: 'customer', label: '고객' },
  { key: 'scheduled', label: '반납 예정' },
  { key: 'actual', label: '실제 반납' },
  { key: 'location', label: '반납 장소' },
  { key: 'status', label: '상태' },
  { key: 'repairCount', label: '수리비' },
]

const insuranceColumns = [
  { key: 'plate', label: '차량번호' },
  { key: 'insurer', label: '보험사' },
  { key: 'policyNo', label: '증권번호' },
  { key: 'period', label: '기간' },
  { key: 'rate', label: '보험요율' },
  { key: 'status', label: '상태' },
]

const accidentColumns = [
  { key: 'plate', label: '차량번호' },
  { key: 'driver', label: '운전자' },
  { key: 'date', label: '사고일' },
  { key: 'location', label: '장소' },
  { key: 'coverage', label: '담보' },
  { key: 'compensation', label: '보상금액', align: 'right' },
  { key: 'status', label: '상태' },
]

function apiId(value, prefix = '') {
  if (!value) return null
  if (typeof value === 'number') return value
  const text = String(value)
  return Number(text.startsWith(prefix) ? text.slice(prefix.length) : text.replace(/^[A-Z]+-/, '')) || null
}

function vehicleApiId(record) {
  return record?.vehicleApiId || (String(record?.id || '').startsWith('VEH-') ? (record.apiId || apiId(record.id, 'VEH-')) : null)
}

function recordApiId(record) {
  return String(record?.id || '').startsWith('FVR-') ? (record.apiId || apiId(record.id, 'FVR-')) : null
}

function findGroupByPlate(plate) {
  return groups.value.find((group) => group.plate === plate)
}

function recordsForPlate(plate) {
  return findGroupByPlate(plate)?.records || []
}

function findRecordById(recordId) {
  for (const group of groups.value) {
    const record = (group.records || []).find((item) => item.id === recordId)
    if (record) return { group, record }
  }
  return { group: null, record: null }
}

function activeSubscription(group) {
  return (group?.subscriptions || []).find((item) => item.status === '구독중') || null
}

function scopedRecords(group, mode = detailMode.value) {
  const records = group?.records || []
  if (mode === 'all') return records
  const current = currentRecord(group)
  if (mode === 'current') return current ? [current] : []
  return records.filter((record) => record.id !== current?.id)
}

function accidentStats(group, mode = 'all') {
  const recordIds = new Set(scopedRecords(group, mode).map((record) => record.id))
  const list = (group?.accidents || []).filter((item) => {
    if (mode === 'all') return true
    return !item.vehicleId || recordIds.has(item.vehicleId)
  })
  return {
    count: list.length,
    last: list.map((item) => item.date).filter(Boolean).sort().at(-1) || '',
    comp: list.reduce((sum, item) => sum + Number(item.compensation || 0), 0),
    paid: list.reduce((sum, item) => sum + Number(item.paid || 0), 0),
    list,
  }
}

function repairStats(group) {
  const repairs = (group?.returns || []).flatMap((item) => item.repairs || [])
  return {
    claim: repairs.reduce((sum, item) => sum + Number(item.claim || 0), 0),
    unpaid: repairs
      .filter((item) => item.payment !== '입금완료')
      .reduce((sum, item) => sum + Number(item.claim || 0), 0),
  }
}

function returnTotals(item) {
  const repairs = item?.repairs || []
  return {
    cost: repairs.reduce((sum, repair) => sum + Number(repair.cost || 0), 0),
    claim: repairs.reduce((sum, repair) => sum + Number(repair.claim || 0), 0),
    unpaid: repairs
      .filter((repair) => repair.payment !== '입금완료')
      .reduce((sum, repair) => sum + Number(repair.claim || 0), 0),
  }
}

function documentByType(group, type) {
  if (!group) return null
  const docs = (group.documents || [])
    .filter((doc) => doc.type === type || doc.documentType === type || doc.document_type === type)
    .sort((a, b) => String(b.uploaded || '').localeCompare(String(a.uploaded || '')))
  if (docs[0]) return docs[0]
  if (type === 'registration_certificate') return registrationDocument(group)
  return null
}

function registrationDocument(group, record = currentRecord(group)) {
  if (record?.cert?.url || record?.cert?.name) return { ...record.cert, source: 'vehicle', record }
  return (group?.documents || []).find((doc) => doc.type === 'registration_certificate') || null
}

function previewFile(file) {
  if (!file?.url) {
    error.value = '미리보기 가능한 파일이 없습니다.'
    return
  }
  window.open(file.url, '_blank', 'noopener')
}

function downloadFile(file) {
  if (!file?.url) {
    error.value = '다운로드 가능한 파일이 없습니다.'
    return
  }
  const link = document.createElement('a')
  link.href = file.url
  link.download = file.name || ''
  document.body.appendChild(link)
  link.click()
  link.remove()
}

function closeModal() {
  modal.value = { open: false, type: '', title: '', caption: '', submitLabel: '', wide: false }
  form.value = {}
}

function openModal(type, title, nextForm = {}, options = {}) {
  form.value = nextForm
  modal.value = {
    open: true,
    type,
    title,
    caption: options.caption || '',
    submitLabel: options.submitLabel || '',
    wide: Boolean(options.wide),
  }
}

function openCreateVehicle() {
  openModal('vehicle-create', '차량 추가', {
    vehicleNumber: '',
    vin: '',
    model: '',
    unitNumber: '',
    status: '유휴',
    start: today(),
    note: '',
  }, { submitLabel: '차량 추가' })
}

function openVehicleEdit(group) {
  const record = currentRecord(group)
  openModal('vehicle-edit', '차량 정보 변경', {
    group,
    record,
    vehicleNumber: group.plate,
    vin: record?.vin || '',
    model: record?.model || '',
    unitNumber: record?.unitNumber || record?.hgi || '',
    status: fleetState(group),
    start: record?.start || '',
    note: record?.note || '',
  }, { submitLabel: '저장' })
}

function openVehicleDelete(group) {
  const record = currentRecord(group)
  openModal('vehicle-delete', '차량 삭제', {
    group,
    record,
    vehicleNumber: group.plate,
  }, { submitLabel: '삭제' })
}

function openDocuments(group, record = currentRecord(group)) {
  openModal('documents', '차량 관련 서류', { group, record }, {
    caption: '차량 등록증과 보험 청약서를 종류별로 업로드, 미리보기, 다운로드, 교체합니다.',
    wide: true,
  })
}

function openSubscription(group) {
  const record = currentRecord(group)
  const end = new Date()
  end.setFullYear(end.getFullYear() + 1)
  openModal('subscription', '구독 계약 등록', {
    plate: group.plate,
    vehicleRecordId: record?.id || '',
    customer: '',
    contact: '',
    start: today(),
    end: toDateInput(end),
    monthlyFee: 1000000,
    deposit: 0,
    status: '구독중',
    signStatus: '서명완료',
    note: '',
    file: null,
  }, { submitLabel: '계약 등록', wide: true })
}

function openSubscriptionDetail(item) {
  openModal('subscription-detail', '구독계약 상세 수정', {
    apiId: item.apiId,
    plate: item.plate,
    vehicleRecordId: item.vehicleId,
    customer: item.customer || '',
    contact: item.contact || '',
    start: item.start || '',
    end: item.end || '',
    monthlyFee: Number(item.monthlyFee || 0),
    deposit: Number(item.deposit || 0),
    status: item.status || '구독중',
    signStatus: item.signStatus || '서명완료',
    note: item.note || '',
    fileName: item.file?.name || '',
    fileUrl: item.file?.url || '',
    file: null,
  }, { submitLabel: '저장', wide: true })
}

function openReturn(group) {
  const candidates = group.subscriptions || []
  const contract = candidates.find((item) => ['구독중', '계약예정'].includes(item.status)) || candidates[0]
  if (!contract) {
    error.value = '반납 접수할 구독 계약이 없습니다.'
    return
  }
  const scheduled = new Date(Date.now() + 3 * 86400000)
  openModal('return', '반납 접수·검수 등록', returnFormFromContract(contract, scheduled), {
    submitLabel: '반납 내역 저장',
    wide: true,
  })
}

function openReturnDetail(item) {
  openModal('return-detail', '반납 상세 수정', {
    apiId: item.apiId,
    subscriptionId: item.subscriptionId,
    vehicleId: item.vehicleId,
    plate: item.plate,
    customer: item.customer || '',
    scheduled: toDateTimeInput(item.scheduled),
    actual: toDateTimeInput(item.actual),
    location: item.location || '경기도 김포시 김포공장',
    status: item.status || '반납예정',
    note: item.note || '',
    photos: normalizedReturnPhotos(item.photos),
    repairs: (item.repairs || []).map((repair) => ({ ...repair })),
  }, { submitLabel: '저장', wide: true })
}

function openInsurance(group) {
  const record = currentRecord(group)
  const end = new Date()
  end.setFullYear(end.getFullYear() + 1)
  openModal('insurance', '보험 계약 등록', {
    plate: group.plate,
    vehicleRecordId: record?.id || '',
    insurer: '',
    policyNo: '',
    start: today(),
    end: toDateInput(end),
    previousRate: 0,
    currentRate: 0,
    status: '가입중',
    note: '',
  }, { submitLabel: '보험 등록', wide: true })
}

function openInsuranceDetail(item) {
  openModal('insurance-detail', '보험 상세 수정', {
    apiId: item.apiId,
    plate: item.plate,
    vehicleRecordId: item.vehicleId,
    insurer: item.insurer || '',
    policyNo: item.policyNo || '',
    start: item.start || '',
    end: item.end || '',
    previousRate: Number(item.previousRate || 0),
    currentRate: Number(item.currentRate || 0),
    status: item.status || '가입중',
    payments: item.payments || [],
    note: item.note || '',
  }, { submitLabel: '저장', wide: true })
}

function openReplacement(group) {
  const record = currentRecord(group)
  const tomorrow = new Date(Date.now() + 86400000)
  openModal('replacement', '대폐차 등록', {
    group,
    record,
    vehicleNumber: group.plate,
    oldEnd: today(),
    newStart: toDateInput(tomorrow),
    newVehicleNumber: '',
    vin: record?.vin || '',
    model: record?.model || '',
    file: null,
  }, { submitLabel: '대폐차 반영', wide: true })
}

function openAccidentDetail(item) {
  openModal('accident-detail', '사고 상세 수정', {
    apiId: item.apiId,
    id: item.id,
    driver: item.driver || '',
    date: toDateTimeInput(item.date),
    location: item.location || '',
    coverage: item.coverage || '',
    status: item.status || '',
    description: item.description || '',
    personalCompensation: Number(item.personalCompensation || 0),
    propertyCompensation: Number(item.propertyCompensation || 0),
    compensation: Number(item.compensation || 0),
    paid: Number(item.paid || 0),
    compensationNote: item.compensationNote || '',
  }, { submitLabel: '저장', wide: true })
}

function syncFormRecord() {
  const record = currentRecord(findGroupByPlate(form.value.plate))
  form.value.vehicleRecordId = record?.id || ''
}

function returnFormFromContract(contract, scheduledDate = new Date()) {
  return {
    subscriptionId: contract.id,
    vehicleId: contract.vehicleId,
    plate: contract.plate,
    customer: contract.customer || '',
    scheduled: toDateTimeInput(scheduledDate),
    actual: '',
    location: '경기도 김포시 김포공장',
    status: '반납예정',
    note: '',
    photos: normalizedReturnPhotos([]),
    repairs: [],
  }
}

function syncReturnContract() {
  const contract = (selectedGroup.value?.subscriptions || []).find((item) => item.id === form.value.subscriptionId)
  if (!contract) return
  Object.assign(form.value, returnFormFromContract(contract, form.value.scheduled || new Date()))
}

function normalizedReturnPhotos(photos = []) {
  const byLabel = new Map(photos.map((photo) => [photo.label, photo]))
  return returnPhotoLabels.map((label) => ({ label, name: '', url: '', mime: '', ...(byLabel.get(label) || {}) }))
}

function addRepairRow() {
  form.value.repairs ||= []
  form.value.repairs.push({ item: '', vendor: '', cost: 0, claim: 0, payment: '청구' })
}

function clearReturnPhoto(index) {
  Object.assign(form.value.photos[index], { name: '', url: '', mime: '' })
}

async function setReturnPhoto(index, event) {
  const file = event.target.files?.[0]
  if (!file) return
  const url = await readDataUrl(file)
  Object.assign(form.value.photos[index], {
    name: file.name,
    url,
    mime: file.type,
    file,
  })
}

function readDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

async function uploadDocument(type, event) {
  const file = event.target.files?.[0]
  if (!file || !form.value.group) return
  const record = form.value.record || currentRecord(form.value.group)
  const existing = documentByType(form.value.group, type)
  const body = new FormData()
  body.append('company', companyId.value)
  body.append('vehicle_number', form.value.group.plate)
  body.append('document_type', type)
  body.append('file', file)
  const vApi = vehicleApiId(record)
  const rApi = recordApiId(record)
  if (vApi) body.append('vehicle', vApi)
  if (rApi) body.append('vehicle_record', rApi)
  try {
    if (existing?.apiId) await updateFleetDocument(existing.apiId, body)
    else await createFleetDocument(body)
    await reload()
    if (selectedPlate.value) {
      form.value.group = findGroupByPlate(selectedPlate.value)
      form.value.record = currentRecord(form.value.group)
    }
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || '서류 저장에 실패했습니다.'
  } finally {
    event.target.value = ''
  }
}

async function removeDocument(type) {
  const doc = documentByType(form.value.group, type)
  if (!doc?.apiId) {
    error.value = '삭제할 파일이 없습니다.'
    return
  }
  try {
    await deleteFleetDocument(doc.apiId)
    await reload()
    form.value.group = findGroupByPlate(selectedPlate.value)
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || '서류 삭제에 실패했습니다.'
  }
}

async function removeInsurance() {
  if (!form.value.apiId) return
  try {
    await deleteFleetInsurance(form.value.apiId)
    closeModal()
    await reload()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || '보험 삭제에 실패했습니다.'
  }
}

async function submitModal() {
  saving.value = true
  try {
    if (modal.value.type === 'vehicle-create') await submitVehicleCreate()
    else if (modal.value.type === 'vehicle-edit') await submitVehicleEdit()
    else if (modal.value.type === 'vehicle-delete') await submitVehicleDelete()
    else if (modal.value.type === 'subscription') await submitSubscription(false)
    else if (modal.value.type === 'subscription-detail') await submitSubscription(true)
    else if (modal.value.type === 'return') await submitReturn(false)
    else if (modal.value.type === 'return-detail') await submitReturn(true)
    else if (modal.value.type === 'insurance') await submitInsurance(false)
    else if (modal.value.type === 'insurance-detail') await submitInsurance(true)
    else if (modal.value.type === 'replacement') await submitReplacement()
    else if (modal.value.type === 'accident-detail') await submitAccident()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || '저장에 실패했습니다.'
  } finally {
    saving.value = false
  }
}

async function submitVehicleCreate() {
  const vehicleNumber = form.value.vehicleNumber
  const response = await createFleetVehicle({
    company: companyId.value,
    vehicle_number: vehicleNumber,
    vin_tid: form.value.vin,
    model: form.value.model,
    hgi: form.value.unitNumber,
    status: form.value.status,
    shipped_at: form.value.start,
    notes: form.value.note,
  })
  closeModal()
  await reload()
  if (response.data?.open_subscription) {
    const group = findGroupByPlate(vehicleNumber)
    if (group) openSubscription(group)
  }
}

async function submitVehicleEdit() {
  const record = form.value.record
  const vApi = vehicleApiId(record)
  if (!vApi) throw new Error('차량 마스터 ID가 없어 차량 정보를 변경할 수 없습니다.')
  const oldPlate = form.value.group?.plate
  const newPlate = form.value.vehicleNumber
  const response = await updateFleetVehicleInfo(vApi, {
    vehicle_number: newPlate,
    vin_tid: form.value.vin,
    model: form.value.model,
    hgi: form.value.unitNumber,
    status: form.value.status,
    shipped_at: form.value.start,
    notes: form.value.note,
  })
  selectedPlate.value = newPlate
  closeModal()
  await reload()
  if (oldPlate !== newPlate) selectedPlate.value = newPlate
  if (response.data?.open_subscription && selectedGroup.value) openSubscription(selectedGroup.value)
}

async function submitVehicleDelete() {
  const vApi = vehicleApiId(form.value.record)
  if (!vApi) throw new Error('차량 마스터 ID가 없어 차량을 삭제할 수 없습니다.')
  await deleteFleetVehicle(vApi)
  selectedPlate.value = ''
  closeModal()
  await reload()
}

function payloadVehicleRefs() {
  const { record } = findRecordById(form.value.vehicleRecordId)
  return {
    record,
    vehicle: vehicleApiId(record),
    vehicle_record: recordApiId(record),
  }
}

async function submitSubscription(isUpdate) {
  const refs = payloadVehicleRefs()
  const body = form.value.file ? new FormData() : {}
  const set = (key, value) => {
    if (body instanceof FormData) {
      if (value !== undefined && value !== null) body.append(key, value)
    } else {
      body[key] = value
    }
  }
  set('company', companyId.value)
  set('vehicle', refs.vehicle)
  set('vehicle_record', refs.vehicle_record)
  set('vehicle_number', form.value.plate)
  set('customer', form.value.customer)
  set('contact', form.value.contact)
  set('start_date', form.value.start)
  set('end_date', form.value.end)
  set('monthly_fee', form.value.monthlyFee || 0)
  set('deposit', form.value.deposit || 0)
  set('status', form.value.status)
  set('sign_status', form.value.signStatus)
  set('note', form.value.note || '')
  if (form.value.file) set('contract_file', form.value.file)
  if (isUpdate) await updateFleetSubscription(form.value.apiId, body)
  else await createFleetSubscription(body)
  closeModal()
  await reload()
}

async function submitReturn(isUpdate) {
  const contract = (selectedGroup.value?.subscriptions || groups.value.flatMap((group) => group.subscriptions || []))
    .find((item) => item.id === form.value.subscriptionId)
  const { record } = findRecordById(form.value.vehicleId)
  const photos = (form.value.photos || [])
    .filter((photo) => photo.name)
    .map(({ label, name, url, mime }) => ({ label, name, url, mime }))
  const payload = {
    company: companyId.value,
    subscription: contract?.apiId || apiId(form.value.subscriptionId, 'SUB-'),
    vehicle: vehicleApiId(record),
    vehicle_record: recordApiId(record),
    vehicle_number: form.value.plate,
    customer: form.value.customer,
    scheduled_at: toApiDateTime(form.value.scheduled),
    actual_at: toApiDateTime(form.value.actual),
    location: form.value.location,
    status: form.value.status,
    note: form.value.note || '',
    photos,
    checks: [],
    repairs: (form.value.repairs || []).filter((repair) => repair.item || repair.vendor || repair.cost || repair.claim),
  }
  let response
  if (isUpdate) response = await updateFleetReturn(form.value.apiId, payload)
  else response = await createFleetReturn(payload)

  const returnId = response?.data?.id || form.value.apiId
  for (const photo of form.value.photos || []) {
    if (photo.file && returnId) {
      const data = new FormData()
      data.append('label', photo.label)
      data.append('file', photo.file)
      await uploadFleetReturnPhoto(returnId, data)
    }
  }
  closeModal()
  await reload()
}

async function submitInsurance(isUpdate) {
  const refs = payloadVehicleRefs()
  const payload = {
    company: companyId.value,
    vehicle: refs.vehicle,
    vehicle_record: refs.vehicle_record,
    vehicle_number: form.value.plate,
    insurer: form.value.insurer,
    policy_no: form.value.policyNo,
    start_date: form.value.start,
    end_date: form.value.end,
    previous_rate: form.value.previousRate || 0,
    current_rate: form.value.currentRate || 0,
    status: form.value.status,
    payments: form.value.payments || [],
    note: form.value.note || '',
  }
  if (isUpdate) await updateFleetInsurance(form.value.apiId, payload)
  else await createFleetInsurance(payload)
  closeModal()
  await reload()
}

async function submitReplacement() {
  await createFleetReplacement({
    company: companyId.value,
    vehicle_number: form.value.vehicleNumber,
    new_vehicle_number: form.value.newVehicleNumber,
    old_end: form.value.oldEnd,
    new_start: form.value.newStart,
    vin: form.value.vin,
    model: form.value.model,
    certificate_name: form.value.file?.name || '',
  })
  selectedPlate.value = form.value.newVehicleNumber
  closeModal()
  await reload()
}

async function submitAccident() {
  await updateFleetAccident(form.value.apiId, {
    driver: form.value.driver,
    accident_at: toApiDateTime(form.value.date),
    location: form.value.location,
    description: form.value.description,
    coverage: form.value.coverage,
    status: form.value.status,
    personal_compensation: form.value.personalCompensation || 0,
    property_compensation: form.value.propertyCompensation || 0,
    compensation: form.value.compensation || 0,
    paid: form.value.paid || 0,
    compensation_note: form.value.compensationNote || '',
  })
  closeModal()
  await reload()
}

function filterRows(rows) {
  const q = search.value.trim().toLowerCase()
  return rows.filter((row) => {
    if (statusFilter.value && row.status !== statusFilter.value) return false
    if (!q) return true
    return Object.values(row).join(' ').toLowerCase().includes(q)
  })
}

function goTab(tabKey) {
  router.push({ name: routeNames[tabKey] || routeNames.dashboard })
}

function selectGroup(group) {
  selectedPlate.value = group.plate
  detailMode.value = 'all'
  if (activeTab.value !== 'vehicles') goTab('vehicles')
}

function currentRecord(group) {
  const records = group?.records || []
  return records.find((record) => !record.end) || records[records.length - 1] || null
}

function fleetState(group) {
  const record = currentRecord(group)
  if (record?.status) return record.status
  if ((group?.subscriptions || []).some((item) => item.status?.includes('구독'))) return '구독'
  return '유휴'
}

async function saveStatus(group, statusValue) {
  const record = currentRecord(group)
  const previous = record?.status
  if (record) record.status = statusValue
  try {
    if (record?.id?.startsWith('FVR-') && record.apiId) {
      await updateFleetRecordStatus(record.apiId, { status: statusValue })
    } else if (record?.vehicleApiId) {
      await updateFleetVehicleStatus(record.vehicleApiId, { status: statusValue })
    } else {
      throw new Error('차량 마스터 ID가 없어 상태를 변경할 수 없습니다.')
    }
    await reload()
  } catch (err) {
    if (record) record.status = previous
    error.value = err?.response?.data?.detail || err?.message || '상태 변경에 실패했습니다.'
  }
}

function focusMetric(metricKey) {
  if (metricKey === 'all') {
    statusFilter.value = ''
    selectedPlate.value = ''
    return
  }
  if (metricKey === 'subscribed') {
    statusFilter.value = '구독'
  } else if (metricKey === 'repair_claims') {
    statusFilter.value = 'A/S'
  } else {
    statusFilter.value = ''
  }
}

function hasRequiredDocuments(group) {
  const types = new Set((group.documents || []).map((doc) => doc.type || doc.documentType || doc.document_type))
  return types.has('registration_certificate') && types.has('insurance_application')
}

function withinDays(value, days) {
  if (!value) return false
  const date = new Date(String(value).slice(0, 10))
  if (Number.isNaN(date.getTime())) return false
  const now = new Date()
  const diffDays = (date.getTime() - now.getTime()) / 86400000
  return diffDays >= 0 && diffDays <= days
}

function money(value) {
  const number = Number(value || 0)
  return `${number.toLocaleString('ko-KR')}원`
}

function date(value) {
  if (!value) return '-'
  const parsed = new Date(String(value).slice(0, 10))
  if (Number.isNaN(parsed.getTime())) return String(value)
  return parsed.toLocaleDateString('ko-KR')
}

function datetime(value) {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return parsed.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function shortVin(value) {
  if (!value) return '-'
  const text = String(value)
  return text.length > 7 ? `···${text.slice(-7)}` : text
}

function today() {
  return toDateInput(new Date())
}

function toDateInput(value) {
  const dateValue = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(dateValue.getTime())) return ''
  return new Date(dateValue.getTime() - dateValue.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

function toDateTimeInput(value) {
  if (!value) return ''
  const dateValue = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(dateValue.getTime())) return String(value).slice(0, 16)
  return new Date(dateValue.getTime() - dateValue.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

function toApiDateTime(value) {
  if (!value) return null
  const dateValue = new Date(value)
  return Number.isNaN(dateValue.getTime()) ? null : dateValue.toISOString()
}

async function downloadAccidentTemplate() {
  try {
    const response = await downloadFleetAccidentTemplate({ company: selectedCompany.value })
    const blobUrl = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = '차량_사고관리_통합업로드_양식.xlsx'
    link.click()
    URL.revokeObjectURL(blobUrl)
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || '양식 다운로드에 실패했습니다.'
  }
}

watch(selectedCompany, () => {
  selectedPlate.value = ''
})

onMounted(async () => {
  await loadCompanies()
  await reload()
})
</script>

<style scoped>
.fleet-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  background: #f3f6fa;
  color: #101827;
}

.fleet-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 18px;
  border-right: 1px solid #e4e8f0;
  background: #fff;
  padding: 22px 18px;
}

.back-link,
.legacy-link,
.btn {
  border: 1px solid #d7deea;
  border-radius: 10px;
  background: #fff;
  color: #1f2a44;
  font-weight: 800;
  text-decoration: none;
  padding: 10px 12px;
  text-align: center;
  cursor: pointer;
}

.quick-links {
  display: grid;
  gap: 8px;
  margin-top: -8px;
}

.quick-links a {
  display: block;
  border: 1px solid #e4e8f0;
  border-radius: 10px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  font-weight: 800;
  padding: 9px 11px;
  text-align: center;
  text-decoration: none;
}

.quick-links a:hover {
  border-color: #c5d941;
  color: #101827;
}

.btn.primary,
.brand-mark {
  border-color: #c5d941;
  background: #c5d941;
  color: #101827;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  font-weight: 900;
}

.brand p {
  margin: 0;
  font-weight: 900;
  letter-spacing: .04em;
}

.brand h1 {
  margin: 2px 0 0;
  font-size: 18px;
}

.company-select span,
.company-select select {
  display: block;
  width: 100%;
}

.company-select span {
  margin-bottom: 7px;
  font-size: 13px;
  font-weight: 900;
  color: #64748b;
}

select,
input {
  border: 1px solid #d7deea;
  border-radius: 10px;
  background: #fff;
  color: #101827;
  font: inherit;
  padding: 10px 12px;
}

.fleet-nav {
  display: grid;
  gap: 8px;
}

.fleet-nav button {
  border: 0;
  border-radius: 13px;
  background: #f6f8fb;
  color: #334155;
  padding: 14px;
  text-align: left;
  cursor: pointer;
}

.fleet-nav button span,
.fleet-nav button small {
  display: block;
}

.fleet-nav button span {
  font-weight: 900;
}

.fleet-nav button small {
  margin-top: 4px;
  color: #7b8794;
}

.fleet-nav button.active {
  background: #101827;
  color: #fff;
}

.fleet-nav button.active small {
  color: #cbd5e1;
}

.legacy-link {
  margin-top: auto;
}

.fleet-main {
  min-width: 0;
  padding: 28px 32px 48px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: .08em;
  color: #718096;
}

.topbar h2 {
  margin: 0;
  font-size: 28px;
}

.topbar p {
  margin: 6px 0 0;
  color: #667085;
}

.top-actions {
  width: min(720px, 55vw);
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 150px auto;
  gap: 10px;
}

.content-stack {
  display: grid;
  gap: 18px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  border: 1px solid #e4e8f0;
  border-radius: 14px;
  background: #fff;
  padding: 18px;
  text-align: left;
  cursor: pointer;
}

.metric-card span,
.metric-card small {
  display: block;
  color: #718096;
  font-weight: 800;
}

.metric-card strong {
  display: block;
  margin: 8px 0 6px;
  font-size: 26px;
}

.panel,
.detail-panel {
  border: 1px solid #e4e8f0;
  border-radius: 16px;
  background: #fff;
  padding: 18px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.panel-head h3,
.detail-panel h3 {
  margin: 0;
  font-size: 20px;
}

.panel-head p,
.detail-panel p {
  margin: 6px 0 0;
  color: #667085;
}

.alert {
  margin-bottom: 16px;
  border: 1px solid #fecaca;
  border-radius: 12px;
  background: #fef2f2;
  color: #b91c1c;
  padding: 12px 14px;
  font-weight: 800;
}

.detail-panel {
  position: fixed;
  right: 28px;
  bottom: 28px;
  width: min(520px, calc(100vw - 320px));
  box-shadow: 0 18px 50px rgba(15, 23, 42, .18);
}

.detail-close {
  position: absolute;
  top: 10px;
  right: 12px;
  border: 0;
  background: transparent;
  font-size: 24px;
  cursor: pointer;
}

.detail-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.detail-grid div {
  border-radius: 12px;
  background: #f7f9fc;
  padding: 12px;
}

.detail-grid span {
  display: block;
  font-size: 12px;
  font-weight: 800;
  color: #7b8794;
}

.detail-grid strong {
  display: block;
  margin-top: 6px;
}

.upload-bridge {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.vehicle-detail-page {
  display: grid;
  gap: 16px;
}

.back-button {
  width: fit-content;
}

.vehicle-hero {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(180px, auto) minmax(480px, auto);
  align-items: center;
  gap: 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, #263d86 0%, #4965e4 100%);
  color: #fff;
  padding: 28px;
  box-shadow: 0 18px 40px rgba(37, 65, 150, .22);
}

.vehicle-hero small {
  display: block;
  margin-bottom: 12px;
  color: rgba(255, 255, 255, .78);
  font-weight: 900;
}

.vehicle-hero h2 {
  margin: 0;
  font-size: 34px;
  letter-spacing: 0;
}

.vehicle-hero p {
  margin: 8px 0 0;
  color: rgba(255, 255, 255, .78);
  font-weight: 700;
}

.hero-status {
  display: grid;
  gap: 8px;
  border-radius: 14px;
  background: rgba(255, 255, 255, .14);
  padding: 14px;
}

.hero-status span {
  color: rgba(255, 255, 255, .8);
  font-size: 12px;
  font-weight: 900;
}

.hero-actions,
.inline-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 9px;
}

.hero-actions .btn {
  color: #fff;
  border-color: rgba(255, 255, 255, .22);
  background: rgba(255, 255, 255, .14);
}

.hero-actions .btn.primary {
  color: #101827;
  border-color: #c5d941;
  background: #c5d941;
}

.btn.danger {
  border-color: #fecaca;
  color: #b91c1c;
  background: #fff8f8;
}

.detail-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.detail-tabs button {
  border: 1px solid #e4e8f0;
  border-radius: 10px;
  background: #fff;
  color: #334155;
  padding: 11px 16px;
  font-weight: 900;
  cursor: pointer;
}

.detail-tabs button.active {
  border-color: #4965e4;
  background: #4965e4;
  color: #fff;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.mini-card {
  border: 1px solid #e4e8f0;
  border-radius: 14px;
  background: #fff;
  padding: 16px;
}

.mini-card span,
.info-grid span,
.doc-row small {
  display: block;
  color: #718096;
  font-size: 12px;
  font-weight: 900;
}

.mini-card strong {
  display: block;
  margin-top: 7px;
  font-size: 23px;
}

.detail-grid-two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 900;
}

.badge.green {
  color: #166534;
  background: #dcfce7;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.info-grid div {
  border-radius: 12px;
  background: #f7f9fc;
  padding: 12px;
  min-width: 0;
}

.info-grid strong {
  display: block;
  margin-top: 6px;
  overflow-wrap: anywhere;
}

.doc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border: 1px solid #e8edf5;
  border-radius: 12px;
  background: #fff;
  padding: 12px;
}

.doc-row.compact {
  margin-top: 14px;
}

.doc-row strong {
  display: block;
  color: #101827;
}

.stack-list {
  display: grid;
  gap: 9px;
}

.empty-box {
  border-radius: 12px;
  background: #f7f9fc;
  color: #8792a2;
  padding: 22px;
  text-align: center;
  font-weight: 800;
}

.timeline {
  display: grid;
  gap: 10px;
}

.timeline-row {
  position: relative;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: start;
  border-radius: 12px;
  background: #f7f9fc;
  padding: 12px;
}

.line-dot {
  width: 10px;
  height: 10px;
  margin-top: 5px;
  border-radius: 999px;
  background: #94a3b8;
}

.timeline-row.current .line-dot {
  background: #c5d941;
}

.timeline-row p {
  margin: 5px 0 0;
  color: #667085;
}

.detail-table {
  width: 100%;
  min-width: 920px;
  border-collapse: collapse;
}

.detail-table th {
  background: #101827;
  color: #fff;
  padding: 11px 12px;
  text-align: left;
}

.detail-table td {
  border-bottom: 1px solid #edf1f7;
  border-right: 1px solid #edf1f7;
  padding: 10px 12px;
}

.detail-table tbody tr:hover td {
  background: #f6f8ec;
}

.money-cell {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.strong {
  font-weight: 900;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, .55);
  padding: 24px;
}

.modal-card {
  width: min(720px, 100%);
  max-height: min(86vh, 900px);
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  background: #fff;
  overflow: hidden;
  box-shadow: 0 24px 70px rgba(15, 23, 42, .32);
}

.modal-card.wide {
  width: min(1120px, 100%);
}

.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid #e8edf5;
  padding: 18px 20px;
}

.modal-head h3 {
  margin: 0;
  font-size: 21px;
}

.modal-head p {
  margin: 5px 0 0;
  color: #667085;
}

.modal-close {
  border: 0;
  background: transparent;
  color: #334155;
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
}

.modal-body {
  overflow: auto;
  padding: 20px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.form-grid label {
  display: grid;
  gap: 7px;
  font-weight: 900;
  color: #334155;
}

.form-grid label.full {
  grid-column: 1 / -1;
}

.form-grid label span {
  font-size: 12px;
  color: #64748b;
}

textarea {
  min-height: 96px;
  resize: vertical;
}

textarea,
.form-grid input,
.form-grid select,
.detail-table input,
.detail-table select {
  width: 100%;
  border: 1px solid #d7deea;
  border-radius: 10px;
  background: #fff;
  color: #101827;
  font: inherit;
  padding: 10px 12px;
}

.document-list {
  display: grid;
  gap: 12px;
}

.document-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid #e8edf5;
  border-radius: 14px;
  padding: 14px;
}

.file-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 16px 0;
}

.photo-card {
  display: grid;
  gap: 6px;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  background: #f8fafc;
  padding: 12px;
}

.photo-card.uploaded {
  border-style: solid;
  border-color: #c5d941;
  background: #fbfdf0;
}

.compact-actions {
  justify-content: flex-start;
}

.repair-section {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.no-margin {
  margin-bottom: 0;
}

.modal-foot,
.modal-extra-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.danger-text {
  border-radius: 12px;
  background: #fef2f2;
  color: #991b1b;
  padding: 14px;
  font-weight: 900;
}

@media (max-width: 1100px) {
  .fleet-page {
    grid-template-columns: 1fr;
  }

  .fleet-sidebar {
    position: static;
    height: auto;
  }

  .fleet-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .topbar {
    align-items: stretch;
    flex-direction: column;
  }

  .top-actions {
    width: 100%;
    grid-template-columns: 1fr;
  }

  .detail-panel {
    position: static;
    width: auto;
    margin-top: 16px;
  }

  .vehicle-hero,
  .detail-grid-two,
  .summary-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .photo-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
