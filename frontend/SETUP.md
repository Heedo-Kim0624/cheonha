# 천하운수 정산관리 시스템 - 프론트엔드 설정 가이드

## 프로젝트 개요

Vue 3, Vite, Pinia, Tailwind CSS를 사용하는 현대적인 배송 정산 관리 시스템입니다.

### 기술 스택

- **프레임워크**: Vue 3 (Composition API, `<script setup>`)
- **빌드 도구**: Vite 5
- **상태 관리**: Pinia 2
- **라우팅**: Vue Router 4
- **HTTP 클라이언트**: Axios
- **CSS 프레임워크**: Tailwind CSS 3
- **아이콘**: 커스텀 SVG (별도 라이브러리 없음)

## 시작하기

### 1. 사전 요구사항

- Node.js 16 이상
- npm 8 이상 (또는 yarn, pnpm)

### 2. 설치

```bash
# 프로젝트 디렉토리로 이동
cd frontend

# 의존성 설치
npm install
```

### 3. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env
```

``.env`` 파일 수정 (필요시):

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 4. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 `http://localhost:5173` 접속

## 프로젝트 구조 상세

```
frontend/
├── index.html                    # HTML 진입점
├── package.json                  # 프로젝트 의존성
├── vite.config.js               # Vite 설정
├── tailwind.config.js           # Tailwind 설정
├── postcss.config.js            # PostCSS 설정
├── .env.example                 # 환경 변수 예시
├── .gitignore
├── README.md
└── src/
    ├── main.js                  # 앱 진입점
    ├── App.vue                  # 루트 컴포넌트
    ├── router/
    │   └── index.js             # 라우팅 설정
    ├── stores/                  # Pinia 스토어
    │   ├── auth.js              # 인증
    │   ├── dashboard.js         # 대시보드
    │   ├── dispatch.js          # 배차
    │   ├── crew.js              # 배송원
    │   ├── settlement.js        # 정산
    │   ├── region.js            # 권역
    │   └── partner.js           # 파트너사
    ├── api/                     # API 모듈
    │   ├── client.js            # Axios 인스턴스
    │   ├── auth.js
    │   ├── dashboard.js
    │   ├── dispatch.js
    │   ├── crew.js
    │   ├── settlement.js
    │   ├── region.js
    │   └── partner.js
    ├── components/
    │   └── common/              # 공통 컴포넌트
    │       ├── AppLayout.vue        # 메인 레이아웃
    │       ├── KpiCard.vue          # KPI 카드
    │       ├── BadgeComponent.vue   # 배지
    │       ├── DataTable.vue        # 데이터 테이블
    │       ├── ModalDialog.vue      # 모달
    │       ├── StepperBar.vue       # 스테퍼
    │       ├── UploadZone.vue       # 드래그 업로드
    │       ├── InnerTabs.vue        # 탭
    │       ├── ToastNotification.vue # 토스트
    │       ├── FilterBar.vue        # 필터
    │       └── WorkflowGuide.vue    # 가이드
    ├── views/                   # 페이지 컴포넌트
    │   ├── LoginView.vue
    │   ├── HomeView.vue
    │   ├── DispatchView.vue
    │   ├── CrewView.vue
    │   ├── SettlementView.vue
    │   └── RegionView.vue
    ├── utils/
    │   ├── format.js            # 포맷팅 함수
    │   └── icons.js             # SVG 아이콘
    └── assets/
        └── main.css             # 글로벌 스타일
```

## 주요 기능 구현

### 1. 인증 (Authentication)

**LoginView.vue**
- 이메일/비밀번호 기반 로그인
- 자동 로그인 옵션
- JWT 토큰 기반 인증
- 데모 계정: demo@example.com / demo1234

**API**: `src/api/auth.js`

```javascript
import { login, logout, getProfile } from '@/api/auth'

await login(email, password)
```

### 2. 대시보드 (Dashboard)

**HomeView.vue**
- KPI 카드 (수신/지급/특근/수익)
- 권역별 수익 현황 표 및 차트
- 최근 활동 타임라인
- 4단계 업무 프로세스 가이드

**스토어**: `src/stores/dashboard.js`

```javascript
const dashboardStore = useDashboardStore()
dashboardStore.kpiData       // KPI 데이터
dashboardStore.regionRevenue // 권역별 수익
dashboardStore.recentActivity // 최근 활동
```

### 3. 배차 관리 (Dispatch)

**DispatchView.vue** - 3개 탭

#### 업로드 탭
- 5단계 진행 바
- 파일 선택 → 검증 → 미리보기 → 완료
- 드래그 앤 드롭 업로드
- 데이터 검증 및 오류 표시

#### 특근설정 탭
- 조별 특근 비용 입력
- 실시간 저장

#### 업로드이력 탭
- 업로드 히스토리 테이블
- 상태 필터링
- 내림차순 정렬

### 4. 배송원 관리 (Crew)

**CrewView.vue**
- 배송원 정보 테이블 (코드/이름/전화/차량/조/권역/상태)
- 신규 배송원 자동 감지 섹션
- 조별/권역별 필터
- 배송원 추가/수정/삭제 모달
- 검색 기능

**스토어**: `src/stores/crew.js`

```javascript
const crewStore = useCrewStore()
crewStore.crewMembers      // 배송원 목록
crewStore.newDetections    // 신규 감지
crewStore.addCrew(data)    // 추가
crewStore.updateCrewMember(id, data) // 수정
```

### 5. 정산 (Settlement)

**SettlementView.vue** - 2개 탭

#### 전체정산 탭
- 정산 데이터 테이블
- 수신/지급/특근/수익 금액 표시
- 상태 배지 (완료/진행중)
- 정산서 다운로드

#### 월별정산 탭
- 월별 정산 카드 뷰
- 기간별 KPI 표시
- 클릭하여 상세보기

**모달**: 정산 생성
- 기간 선택
- 수신/지급/특근/수익 입력
- 실시간 마진 계산

### 6. 권역 관리 (Region)

**RegionView.vue** - 2개 탭

#### 팀관리 탭
- 팀 카드 (A조/X조/R조)
- 팀리더 표시
- 기본 특근 비용 수정

#### 권역관리 탭
- 권역별 단가 테이블
- 수신단가 (파란색) / 지급단가 (주황색)
- 마진 자동 계산 (초록/빨강)
- 적자 권역 경고
- 단가 추가 모달
- 엑셀 일괄 업로드

## 컴포넌트 API

### AppLayout.vue

메인 레이아웃 (사이드바 + 탑바)

```vue
<AppLayout>
  <slot></slot>
</AppLayout>
```

### KpiCard.vue

```vue
<KpiCard
  label="수신"
  :value="2850000"
  :change="12.5"
  subText="전월 대비"
/>
```

Props:
- `label`: 레이블
- `value`: 수치 (숫자)
- `change`: 변화율 (%)
- `subText`: 부설명 (기본값: '전월 대비')

### DataTable.vue

```vue
<DataTable
  :columns="columns"
  :data="data"
>
  <template #cell-{colKey}="{ row, value }">
    <!-- 커스텀 셀 렌더링 -->
  </template>
</DataTable>
```

Props:
- `columns`: 컬럼 배열 `[{ key, label, width?, sortable? }]`
- `data`: 데이터 배열

Slots:
- `cell-{key}`: 특정 컬럼 커스텀 렌더링

Features:
- 정렬 가능 (sortable: true)
- 컬럼 너비 조절
- 행 호버 효과

### ModalDialog.vue

```vue
<ModalDialog
  :isOpen="isOpen"
  title="모달 제목"
  @close="isOpen = false"
>
  <p>모달 내용</p>
  <template #footer>
    <button>확인</button>
  </template>
</ModalDialog>
```

Props:
- `isOpen`: Boolean
- `title`: 모달 제목

Slots:
- default: 모달 본문
- `footer`: 하단 버튼

### UploadZone.vue

```vue
<UploadZone
  accept=".xlsx,.xls"
  :multiple="false"
  @files-selected="handleFiles"
/>
```

Props:
- `accept`: 허용 파일 확장자
- `multiple`: 여러 파일 선택 가능 여부

Emits:
- `files-selected`: 파일 선택 완료

### StepperBar.vue

```vue
<StepperBar
  :steps="['단계1', '단계2', '단계3']"
  :currentStep="1"
/>
```

Props:
- `steps`: 단계 배열
- `currentStep`: 현재 단계 (0-indexed)

### InnerTabs.vue

```vue
<InnerTabs
  :tabs="['탭1', '탭2']"
  :activeTab="activeTab"
  @change="activeTab = $event"
>
  <!-- 탭 내용 -->
</InnerTabs>
```

### FilterBar.vue

```vue
<FilterBar
  :filters="filterOptions"
  :showDateRange="true"
  :showSearch="true"
  @filter-change="handleChange"
/>
```

### BadgeComponent.vue

```vue
<BadgeComponent
  text="활성"
  variant="success"
/>
```

Variants: `primary`, `success`, `danger`, `warning`, `info`, `gray`

## 스토어 (Pinia) 사용법

### useAuthStore

```javascript
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// 상태
authStore.user          // 사용자 정보
authStore.token         // JWT 토큰
authStore.teamFilter    // 팀 필터
authStore.isAuthenticated // 인증 여부

// 액션
await authStore.login(email, password)
authStore.logout()
authStore.setTeamFilter(team)
```

### useDashboardStore

```javascript
import { useDashboardStore } from '@/stores/dashboard'

const dashboardStore = useDashboardStore()

dashboardStore.kpiData
dashboardStore.regionRevenue
dashboardStore.recentActivity
await dashboardStore.fetchData()
```

### useDispatchStore

```javascript
import { useDispatchStore } from '@/stores/dispatch'

const dispatchStore = useDispatchStore()

dispatchStore.uploadHistory
dispatchStore.overtimeSettings
await dispatchStore.uploadDispatch(file)
dispatchStore.setOvertimeCost(team, cost)
```

### useCrewStore

```javascript
import { useCrewStore } from '@/stores/crew'

const crewStore = useCrewStore()

crewStore.crewMembers
crewStore.newDetections
await crewStore.addCrew(data)
await crewStore.updateCrewMember(id, data)
crewStore.removeNewDetection(phone)
```

### useSettlementStore

```javascript
import { useSettlementStore } from '@/stores/settlement'

const settlementStore = useSettlementStore()

settlementStore.settlements
await settlementStore.createNewSettlement(data)
```

### useRegionStore

```javascript
import { useRegionStore } from '@/stores/region'

const regionStore = useRegionStore()

regionStore.teams
regionStore.regions
await regionStore.updateRegionPrice(id, data)
```

## API 통합

### API 클라이언트 설정

`src/api/client.js` - Axios 인스턴스

```javascript
import client from '@/api/client'

// 기본 설정
// - baseURL: http://localhost:8000/api/v1
// - JWT 토큰 자동 추가
// - 401 에러 시 자동 로그아웃
```

### API 모듈 사용

```javascript
import { login, logout, getProfile } from '@/api/auth'
import { fetchUploads, createUpload } from '@/api/dispatch'
import { fetchCrewMembers, createCrew } from '@/api/crew'
// ...etc
```

## 유틸리티 함수

### 포맷팅 (utils/format.js)

```javascript
import {
  formatCurrency,      // 1000000 → '1,000,000'
  formatDate,          // new Date() → '2024-04-08'
  formatDateTime,      // new Date() → '2024-04-08 14:30'
  formatTime,          // new Date() → '14:30'
  formatTimeAgo,       // new Date() → '방금' / '5분 전'
  parsePhoneNumber,    // '01012345678' → '010-1234-5678'
  validateEmail,       // 이메일 검증
  validatePhoneNumber, // 전화번호 검증
  calculatePercentageChange, // 변화율 계산
  getMonthYearString   // new Date() → '2024-04'
} from '@/utils/format'
```

### 아이콘 (utils/icons.js)

모든 SVG 아이콘은 문자열로 정의됨:

```javascript
import {
  IconHome,
  IconDispatch,
  IconCrew,
  IconSettlement,
  IconRegion,
  IconPlus,
  IconEdit,
  IconDelete,
  IconDownload,
  IconUpload,
  IconClose,
  IconCheck,
  IconWarning,
  IconError,
  IconSuccess,
  // ... etc
} from '@/utils/icons'

// 사용
<span v-html="IconHome" class="w-5 h-5"></span>
```

## 스타일 및 테마

### 설계 토큰 (Design Tokens)

CSS 변수로 정의됨 (`src/assets/main.css`):

```css
--primary: #C8D530;          /* 주색상 */
--primary-light: #F4F7D6;    /* 밝은 주색상 */
--primary-dark: #7A8A00;     /* 어두운 주색상 */
--text: #1A1A1A;             /* 기본 텍스트 */
--text2: #666;               /* 보조 텍스트 */
--text3: #999;               /* 약한 텍스트 */
--bg: #F5F5F5;               /* 배경 */
--card: #FFF;                /* 카드 배경 */
--border: #E5E5E5;           /* 테두리 */
--border-light: #F0F0F0;     /* 밝은 테두리 */
--danger: #E74C3C;           /* 위험 */
--success: #27AE60;          /* 성공 */
--warning: #F39C12;          /* 경고 */
--info: #2980B9;             /* 정보 */
```

### Tailwind 커스터마이징

`tailwind.config.js`에서 확장:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        DEFAULT: '#C8D530',
        light: '#F4F7D6',
        dark: '#7A8A00',
      },
      // ...
    }
  }
}
```

## 개발 워크플로우

### 로컬 개발

```bash
# 개발 서버 실행
npm run dev

# 새 컴포넌트 생성
# src/components/common/MyComponent.vue

# 새 페이지 추가
# src/views/MyView.vue
# src/router/index.js에 라우트 추가

# 새 스토어 생성
# src/stores/myStore.js

# 새 API 모듈 생성
# src/api/myApi.js
```

### 코드 구조

#### 컴포넌트 템플릿

```vue
<template>
  <div>
    <!-- 마크업 -->
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

defineProps({
  // props 정의
})

defineEmits(['event-name'])

const state = ref(null)

const computed = computed(() => {
  // 계산된 상태
})

const handler = () => {
  // 메서드
}
</script>

<style scoped>
/* 스타일 */
</style>
```

#### 스토어 템플릿

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchData } from '@/api/myApi'

export const useMyStore = defineStore('myStore', () => {
  const state = ref([])

  const computed = computed(() => {
    // 파생 상태
  })

  const action = async () => {
    try {
      const response = await fetchData()
      state.value = response.data
    } catch (error) {
      console.error('Error:', error)
    }
  }

  return { state, computed, action }
})
```

## 빌드 및 배포

### 개발 빌드

```bash
npm run build
```

### 빌드 결과

- `dist/index.html` - 진입점
- `dist/assets/` - JS, CSS, 기타 자산

### 프로덕션 배포

1. 빌드 생성: `npm run build`
2. `dist` 폴더를 웹 서버로 배포
3. 웹 서버 설정: SPA 라우팅을 위해 모든 요청을 `index.html`로 리다이렉트

#### Nginx 설정 예시

```nginx
server {
  listen 80;
  server_name example.com;
  root /var/www/dist;

  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

## 문제 해결

### 포트 충돌

포트 5173이 사용 중인 경우:

```bash
npm run dev -- --port 5174
```

### API 연결 실패

1. `.env` 파일에서 `VITE_API_BASE_URL` 확인
2. 백엔드 서버가 실행 중인지 확인
3. CORS 설정 확인

### 빌드 오류

```bash
# node_modules 재설치
rm -rf node_modules
npm install

# 캐시 초기화
npm cache clean --force
```

## 성능 최적화

- 이미지: WebP 형식 사용
- 코드 분할: 동적 import 사용
- 번들 분석: `npm run build -- --analyze`

## 보안 고려사항

- JWT 토큰은 localStorage에 저장 (XSS 공격에 취약)
- 프로덕션: secure, httpOnly 쿠키 사용 권장
- API 응답 검증
- 민감한 데이터는 클라이언트에 노출하지 않기

## 추가 리소스

- [Vue 3 문서](https://vuejs.org/)
- [Vite 문서](https://vitejs.dev/)
- [Pinia 문서](https://pinia.vuejs.org/)
- [Tailwind CSS 문서](https://tailwindcss.com/)
- [Vue Router 문서](https://router.vuejs.org/)

## 지원

개발 중 문제가 발생하면:

1. 브라우저 콘솔 확인
2. 네트워크 탭에서 API 요청 확인
3. Pinia DevTools 사용
4. Vue DevTools 설치

---

마지막 업데이트: 2024년 4월
