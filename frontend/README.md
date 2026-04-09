# 천하운수 정산관리 시스템 - 프론트엔드

Vue 3 + Vite + Pinia + Tailwind CSS로 구축된 천하운수 정산관리 시스템 프론트엔드입니다.

## 시스템 요구사항

- Node.js 16+
- npm 또는 yarn

## 설치

```bash
npm install
```

## 환경 설정

`.env.example` 파일을 `.env`로 복사하고 필요시 수정합니다:

```bash
cp .env.example .env
```

### 환경 변수

- `VITE_API_BASE_URL`: 백엔드 API 기본 URL (기본값: `http://localhost:8000/api/v1`)

## 개발 서버 실행

```bash
npm run dev
```

서버는 `http://localhost:5173`에서 실행됩니다.

## 프로덕션 빌드

```bash
npm run build
```

빌드 결과는 `dist` 디렉토리에 생성됩니다.

## 프로젝트 구조

```
src/
├── api/                 # API 통신 레이어
│   ├── client.js       # Axios 인스턴스
│   ├── auth.js         # 인증 API
│   ├── dispatch.js     # 배차 API
│   ├── crew.js         # 배송원 API
│   ├── settlement.js   # 정산 API
│   ├── region.js       # 권역 API
│   ├── partner.js      # 파트너사 API
│   └── dashboard.js    # 대시보드 API
├── assets/             # 정적 자원
│   └── main.css        # 글로벌 스타일
├── components/         # 재사용 가능한 컴포넌트
│   └── common/         # 공통 컴포넌트
│       ├── AppLayout.vue
│       ├── KpiCard.vue
│       ├── BadgeComponent.vue
│       ├── DataTable.vue
│       ├── ModalDialog.vue
│       ├── StepperBar.vue
│       ├── UploadZone.vue
│       ├── InnerTabs.vue
│       ├── ToastNotification.vue
│       ├── FilterBar.vue
│       └── WorkflowGuide.vue
├── stores/             # Pinia 상태 관리
│   ├── auth.js         # 인증 스토어
│   ├── dashboard.js    # 대시보드 스토어
│   ├── dispatch.js     # 배차 스토어
│   ├── crew.js         # 배송원 스토어
│   ├── settlement.js   # 정산 스토어
│   ├── region.js       # 권역 스토어
│   └── partner.js      # 파트너사 스토어
├── views/              # 페이지 컴포넌트
│   ├── LoginView.vue
│   ├── HomeView.vue
│   ├── DispatchView.vue
│   ├── CrewView.vue
│   ├── SettlementView.vue
│   └── RegionView.vue
├── router/             # Vue Router 설정
│   └── index.js
├── utils/              # 유틸리티 함수
│   ├── format.js       # 포맷팅 함수
│   └── icons.js        # SVG 아이콘
├── main.js             # 애플리케이션 진입점
└── App.vue             # 루트 컴포넌트
```

## 주요 기능

### 1. 로그인 (LoginView)
- 이메일/비밀번호 기반 인증
- 자동 로그인 옵션
- 데모 계정 제공

### 2. 대시보드 (HomeView)
- KPI 카드 (수신/지급/특근/수익)
- 권역별 수익 현황
- 최근 활동 타임라인
- 업무 프로세스 가이드

### 3. 배차 관리 (DispatchView)
- 5단계 배차 파일 업로드 프로세스
- 데이터 검증 및 미리보기
- 특근 비용 관리
- 업로드 이력 조회

### 4. 배송원 관리 (CrewView)
- 배송원 정보 관리
- 신규 배송원 자동 감지
- 조별/권역별 필터링
- 배송원 추가/수정/삭제

### 5. 정산 (SettlementView)
- 월별 정산 생성 및 조회
- 정산 세부내역 확인
- 정산서 다운로드
- 전체정산/월별정산 탭

### 6. 권역 관리 (RegionView)
- 팀별 설정 (팀리더, 기본 특근 비용)
- 권역별 수신/지급 단가 관리
- 마진 실시간 계산
- 적자 권역 경고
- 단가 일괄 업로드

## 디자인 시스템

### 색상 토큰

```css
--primary: #C8D530;          /* 주색상 (라임 그린) */
--primary-light: #F4F7D6;    /* 밝은 주색상 */
--primary-dark: #7A8A00;     /* 어두운 주색상 */
--text: #1A1A1A;             /* 기본 텍스트 */
--text2: #666;               /* 보조 텍스트 */
--text3: #999;               /* 약한 텍스트 */
--bg: #F5F5F5;               /* 배경 */
--card: #FFF;                /* 카드 배경 */
--border: #E5E5E5;           /* 테두리 */
--border-light: #F0F0F0;     /* 밝은 테두리 */
--danger: #E74C3C;           /* 위험 (빨강) */
--success: #27AE60;          /* 성공 (초록) */
--warning: #F39C12;          /* 경고 (주황) */
--info: #2980B9;             /* 정보 (파랑) */
```

## 상태 관리 (Pinia)

### useAuthStore
- 사용자 인증 정보
- 토큰 관리
- 팀 필터 설정

### useDashboardStore
- KPI 데이터
- 권역별 수익
- 최근 활동

### useDispatchStore
- 배차 파일 업로드 관리
- 특근 설정
- 업로드 이력

### useCrewStore
- 배송원 목록
- 신규 배송원 감지
- 배송원 추가/수정/삭제

### useSettlementStore
- 정산 목록
- 정산 상세정보
- 정산 생성

### useRegionStore
- 팀 정보
- 권역 정보
- 단가 관리

### usePartnerStore
- 파트너사 목록
- 파트너사 추가/수정/삭제

## API 통합

모든 API 호출은 `src/api/` 디렉토리의 모듈을 통해 관리됩니다.

### 기본 설정

- 기본 URL: `http://localhost:8000/api/v1`
- 인증: JWT 토큰 (Bearer)
- 요청/응답 형식: JSON

### API 클라이언트

```javascript
import client from '@/api/client'

// Axios 인스턴스로 모든 HTTP 메서드 지원
await client.get('/endpoint')
await client.post('/endpoint', data)
await client.put('/endpoint/:id', data)
await client.delete('/endpoint/:id')
```

## 컴포넌트 사용 예시

### KpiCard

```vue
<KpiCard
  label="수신"
  :value="2850000"
  :change="12.5"
  subText="전월 대비"
/>
```

### DataTable

```vue
<DataTable
  :columns="columns"
  :data="data"
>
  <template #cell-status="{ value }">
    <BadgeComponent :text="value" variant="success" />
  </template>
</DataTable>
```

### ModalDialog

```vue
<ModalDialog
  :isOpen="isOpen"
  title="모달 제목"
  @close="isOpen = false"
>
  <p>모달 내용</p>
  <template #footer>
    <button>취소</button>
    <button>확인</button>
  </template>
</ModalDialog>
```

## 포맷팅 유틸리티

```javascript
import { formatCurrency, formatDate, formatDateTime, formatTimeAgo } from '@/utils/format'

formatCurrency(1000000)      // '1,000,000'
formatDate(new Date())       // '2024-04-08'
formatDateTime(new Date())   // '2024-04-08 14:30'
formatTimeAgo(new Date())    // '방금' 또는 '5분 전'
```

## 라우팅

- `/login` - 로그인 페이지
- `/` - 대시보드
- `/dispatch` - 배차 관리
- `/crew` - 배송원 관리
- `/settlement` - 정산
- `/region` - 권역 관리

인증이 필요한 페이지는 미인증 상태에서 `/login`으로 리다이렉트됩니다.

## 개발 팁

### 데모 계정

로그인 페이지에 미리 입력되어 있습니다:
- 이메일: `demo@example.com`
- 비밀번호: `demo1234`

### Mock 데이터

각 스토어에 기본 mock 데이터가 포함되어 있으므로 백엔드 없이도 UI 개발 및 테스트가 가능합니다.

### Tailwind CSS 커스터마이징

`tailwind.config.js`에서 커스텀 색상 및 테마를 설정할 수 있습니다.

## 브라우저 호환성

- Chrome (최신)
- Firefox (최신)
- Safari (최신)
- Edge (최신)

## 라이선스

내부용 - 모든 권리 보유
