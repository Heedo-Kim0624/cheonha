# 빠른 시작 가이드 (Quick Start)

## 설치 및 실행 (5분)

```bash
# 1. 의존성 설치
npm install

# 2. 환경 설정 (선택)
cp .env.example .env

# 3. 개발 서버 시작
npm run dev
```

브라우저: `http://localhost:5173`

## 로그인

```
이메일: demo@example.com
비밀번호: demo1234
```

## 파일 구조 요약

```
frontend/
├── src/
│   ├── views/           ← 페이지 (6개)
│   │   ├── LoginView
│   │   ├── HomeView
│   │   ├── DispatchView
│   │   ├── CrewView
│   │   ├── SettlementView
│   │   └── RegionView
│   ├── components/      ← 재사용 컴포넌트 (11개)
│   ├── stores/          ← 상태 관리 (7개)
│   ├── api/             ← API 호출 (8개)
│   ├── router/          ← 라우팅
│   ├── utils/           ← 유틸리티
│   └── assets/          ← 스타일
├── package.json
├── vite.config.js
├── tailwind.config.js
└── index.html
```

## 주요 기능별 진입점

### 1. 홈/대시보드
`src/views/HomeView.vue`
- KPI 카드
- 권역별 수익
- 최근 활동

### 2. 배차 데이터
`src/views/DispatchView.vue`
- 파일 업로드 (5단계)
- 특근 비용 설정
- 업로드 이력

### 3. 배송원 관리
`src/views/CrewView.vue`
- 배송원 목록
- 신규 감지
- 추가/수정/삭제

### 4. 정산
`src/views/SettlementView.vue`
- 전체 정산
- 월별 정산
- 정산서 다운로드

### 5. 권역 관리
`src/views/RegionView.vue`
- 팀 관리
- 단가 관리
- 일괄 업로드

## 자주 사용하는 컴포넌트

### 데이터 표시

```vue
<KpiCard label="수신" :value="2850000" :change="12.5" />
<DataTable :columns="columns" :data="data" />
<BadgeComponent text="활성" variant="success" />
```

### 사용자 상호작용

```vue
<UploadZone @files-selected="handleFiles" />
<ModalDialog :isOpen="isOpen" @close="isOpen = false">...</ModalDialog>
<InnerTabs :tabs="tabs" :activeTab="active" @change="active = $event" />
```

### 진행 표시

```vue
<StepperBar :steps="steps" :currentStep="current" />
<ToastNotification message="저장되었습니다" type="success" />
```

## 자주 사용하는 유틸리티

```javascript
// 포맷팅
import { formatCurrency, formatDate, formatTimeAgo } from '@/utils/format'

formatCurrency(1000000)  // '1,000,000'
formatDate(new Date())   // '2024-04-08'
formatTimeAgo(new Date()) // '방금'

// 아이콘
import { IconHome, IconPlus, IconDelete } from '@/utils/icons'

<span v-html="IconHome" class="w-5 h-5"></span>
```

## 자주 사용하는 스토어

```javascript
// 인증
import { useAuthStore } from '@/stores/auth'
const authStore = useAuthStore()
authStore.user, authStore.isAuthenticated, authStore.logout()

// 대시보드
import { useDashboardStore } from '@/stores/dashboard'
const dashboardStore = useDashboardStore()
dashboardStore.kpiData, dashboardStore.regionRevenue

// 배송원
import { useCrewStore } from '@/stores/crew'
const crewStore = useCrewStore()
crewStore.crewMembers, crewStore.addCrew(), crewStore.updateCrewMember()

// 권역
import { useRegionStore } from '@/stores/region'
const regionStore = useRegionStore()
regionStore.regions, regionStore.teams, regionStore.updateRegionPrice()
```

## 색상 팔레트

```
주색상: #C8D530 (라임 그린)
위험: #E74C3C (빨강)
성공: #27AE60 (초록)
경고: #F39C12 (주황)
정보: #2980B9 (파랑)
```

## 자주 하는 작업

### 새 페이지 추가

1. `src/views/MyView.vue` 생성
2. `src/router/index.js`에 라우트 추가
3. `src/components/common/AppLayout.vue`에 네비게이션 추가

### 새 컴포넌트 생성

```vue
<!-- src/components/common/MyComponent.vue -->
<template>
  <div>
    <slot></slot>
  </div>
</template>

<script setup>
defineProps({
  // props
})

defineEmits(['event'])
</script>
```

### API 호출 추가

```javascript
// src/api/myApi.js
import client from './client'

export const fetchData = () => {
  return client.get('/endpoint')
}

// 컴포넌트에서 사용
import { fetchData } from '@/api/myApi'
const data = await fetchData()
```

### 상태 관리 추가

```javascript
// src/stores/myStore.js
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMyStore = defineStore('my', () => {
  const items = ref([])

  const addItem = (item) => {
    items.value.push(item)
  }

  return { items, addItem }
})

// 컴포넌트에서 사용
const store = useMyStore()
store.addItem(newItem)
```

## 명령어

```bash
npm run dev        # 개발 서버 시작
npm run build      # 프로덕션 빌드
npm run preview    # 빌드 결과 미리보기
npm install        # 의존성 설치
npm update         # 의존성 업데이트
```

## 브라우저 DevTools

### Vue DevTools
- Chrome, Firefox 확장프로그램 설치
- 컴포넌트 트리 확인
- 상태 디버깅

### Pinia DevTools
- 상태 변경 추적
- 액션 리플레이
- 시간 여행 디버깅

## 팁과 트릭

### 1. Mock 데이터

각 스토어에 기본 mock 데이터 포함. 백엔드 없이도 개발 가능.

### 2. 반응형

모든 컴포넌트는 `<script setup>` 사용 (간결함)

### 3. 포맷팅

모든 금액은 `formatCurrency()` 사용

```javascript
<span>{{ formatCurrency(value) }}</span>
```

### 4. 라우팅

인증 가드 자동 적용. `/login`으로 자동 리다이렉트.

### 5. API 에러 처리

API 클라이언트가 401 자동 처리 (로그아웃)

## 문제 해결

### 포트 충돌

```bash
npm run dev -- --port 3000
```

### 모듈 찾을 수 없음

```bash
npm install
rm -rf node_modules
npm cache clean --force
npm install
```

### 빌드 실패

```bash
npm run build -- --debug
```

## 다음 단계

1. **컴포넌트 학습**
   - `src/components/common/` 파일들 살펴보기
   - 각 컴포넌트의 Props와 Emits 확인

2. **페이지 개발**
   - `src/views/` 에서 기존 페이지 분석
   - 새로운 기능 추가

3. **API 연동**
   - `src/api/` 모듈 살펴보기
   - 백엔드 API 엔드포인트 연결

4. **상태 관리**
   - `src/stores/` 패턴 이해
   - 복잡한 상태를 위한 새 스토어 생성

## 더 많은 정보

- `README.md` - 전체 프로젝트 문서
- `SETUP.md` - 상세 설정 가이드
- `src/` 내 주석 참고

---

행운을 빕니다! 😊
