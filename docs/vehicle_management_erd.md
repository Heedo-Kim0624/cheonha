# 차량관리 데이터베이스 ERD

이 문서는 운영 통합관리의 차량관리 도메인을 Vue 프론트엔드와 백엔드 API가 분리된 구조로 관리하기 위한 기준 ERD다.

- Django app: `backend/apps/vehicle_management`
- API prefix: `/api/v1/vehicle/`
- DB table prefix: `vehicle_mgmt_`
- 주의: 기존 현장관리 앱용 요청 테이블과 운영 통합관리 웹용 `fleet_*` 테이블을 함께 사용한다.
- DB 호환성: 로컬 sqlite와 운영 PostgreSQL 모두에서 migration이 가능하도록 별도 PostgreSQL schema 대신 `vehicle_mgmt_*` 테이블명을 사용한다.

## Mermaid ERD

```mermaid
erDiagram
    Company ||--o{ Vehicle : owns
    Company ||--o{ PitRecord : has
    Company ||--o{ CalendarEvent : has
    Company ||--o{ SubscriptionRequest : receives
    Company ||--o{ ReturnRequest : receives
    Company ||--o{ ASRequest : receives

    Vehicle ||--o{ PitRecord : matched_by_short_number
    Vehicle ||--o{ SubscriptionRequestVehicle : assigned
    Vehicle ||--o{ FleetVehicleRecord : history
    Vehicle ||--o{ FleetVehicleDocument : documents
    Vehicle ||--o{ FleetSubscriptionContract : contracts
    Vehicle ||--o{ FleetReturnRecord : returns
    Vehicle ||--o{ FleetInsurancePolicy : insurances
    Vehicle ||--o{ FleetAccidentCase : accidents

    SubscriptionRequest ||--o{ SubscriptionRequestVehicle : matched_vehicles
    ReturnRequest ||--o{ ReturnRequestPhoto : photos

    PitRecord ||--o{ CalendarEvent : related_pit_record
    SubscriptionRequest ||--o{ CalendarEvent : related_subscription
    ReturnRequest ||--o{ CalendarEvent : related_return
    ASRequest ||--o{ CalendarEvent : related_as
    Vehicle ||--o{ CalendarEvent : related_vehicle

    Company ||--o{ FleetVehicleRecord : has
    Company ||--o{ FleetVehicleDocument : has
    Company ||--o{ FleetSubscriptionContract : has
    Company ||--o{ FleetReturnRecord : has
    Company ||--o{ FleetInsurancePolicy : has
    Company ||--o{ FleetAccidentCase : has

    FleetVehicleRecord ||--o{ FleetVehicleDocument : scoped_documents
    FleetVehicleRecord ||--o{ FleetSubscriptionContract : scoped_contracts
    FleetVehicleRecord ||--o{ FleetReturnRecord : scoped_returns
    FleetVehicleRecord ||--o{ FleetInsurancePolicy : scoped_insurances
    FleetVehicleRecord ||--o{ FleetAccidentCase : scoped_accidents
    FleetSubscriptionContract ||--o{ FleetReturnRecord : return_records

    Company {
        bigint id PK
        varchar code UK
        varchar name
        int sort_order
        boolean is_active
        datetime created_at
    }

    Vehicle {
        bigint id PK
        bigint company_id FK
        varchar vehicle_number
        varchar vehicle_number_short
        varchar vin_tid
        varchar model
        date shipped_at
        varchar fleet
        varchar driver
        varchar hgi
        file registration_certificate
        datetime registration_certificate_uploaded_at
        varchar placement_status
        varchar operation_type
        text notes
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    PitRecord {
        bigint id PK
        bigint company_id FK
        bigint vehicle_id FK
        varchar vehicle_number_short
        date in_date
        date out_date
        varchar reason
        text note
        boolean note_highlight
        bigint created_by_id FK
        datetime created_at
        datetime updated_at
    }

    CalendarEvent {
        bigint id PK
        bigint company_id FK
        varchar kind
        date event_date
        time event_time
        varchar title
        text body
        bigint related_vehicle_id FK
        bigint related_pit_record_id FK
        bigint related_subscription_id FK
        bigint related_return_id FK
        bigint related_as_id FK
        bigint created_by_id FK
        datetime created_at
        datetime updated_at
    }

    SubscriptionRequest {
        bigint id PK
        bigint company_id FK
        varchar team_code
        varchar phone
        date requested_date
        int quantity
        varchar status
        text reject_reason
        datetime completed_at
        datetime created_at
        datetime updated_at
    }

    SubscriptionRequestVehicle {
        bigint id PK
        bigint request_id FK
        bigint vehicle_id FK
        datetime created_at
    }

    ReturnRequest {
        bigint id PK
        bigint company_id FK
        varchar team_code
        varchar phone
        varchar vehicle_number
        text reason
        date hope_date
        time hope_time
        date confirmed_date
        time confirmed_time
        text block_reason
        varchar available_dates
        varchar status
        datetime created_at
        datetime updated_at
    }

    ReturnRequestPhoto {
        bigint id PK
        bigint request_id FK
        varchar kind
        file image
        datetime created_at
    }

    ASRequest {
        bigint id PK
        bigint company_id FK
        varchar team_code
        varchar phone
        varchar vehicle_number
        varchar owner_name
        varchar owner_phone
        text reason
        text admin_comment
        text calendar_note
        varchar status
        datetime completed_at
        datetime created_at
        datetime updated_at
    }

    FleetVehicleRecord {
        bigint id PK
        bigint company_id FK
        bigint vehicle_id FK
        varchar vehicle_number
        varchar vin
        varchar model
        date start_date
        date end_date
        varchar status
        varchar certificate_name
        date certificate_uploaded_at
        text note
        bigint created_by_id FK
        datetime created_at
        datetime updated_at
    }

    FleetVehicleDocument {
        bigint id PK
        bigint company_id FK
        bigint vehicle_id FK
        bigint vehicle_record_id FK
        varchar vehicle_number
        varchar document_type
        file file
        text note
        bigint created_by_id FK
        datetime created_at
        datetime uploaded_at
    }

    FleetSubscriptionContract {
        bigint id PK
        bigint company_id FK
        bigint vehicle_id FK
        bigint vehicle_record_id FK
        varchar vehicle_number
        varchar customer
        varchar contact
        date start_date
        date end_date
        int monthly_fee
        int deposit
        varchar status
        varchar sign_status
        file contract_file
        text note
        bigint created_by_id FK
        datetime created_at
        datetime updated_at
    }

    FleetReturnRecord {
        bigint id PK
        bigint company_id FK
        bigint subscription_id FK
        bigint vehicle_id FK
        bigint vehicle_record_id FK
        varchar vehicle_number
        varchar customer
        datetime scheduled_at
        datetime actual_at
        varchar location
        varchar status
        json photos
        json checks
        text note
        json repairs
        bigint created_by_id FK
        datetime created_at
        datetime updated_at
    }

    FleetInsurancePolicy {
        bigint id PK
        bigint company_id FK
        bigint vehicle_id FK
        bigint vehicle_record_id FK
        varchar vehicle_number
        varchar insurer
        varchar policy_no
        date start_date
        date end_date
        decimal previous_rate
        decimal current_rate
        varchar status
        json payments
        text note
        bigint created_by_id FK
        datetime created_at
        datetime updated_at
    }

    FleetAccidentCase {
        bigint id PK
        bigint company_id FK
        bigint vehicle_id FK
        bigint vehicle_record_id FK
        varchar source_key
        varchar vehicle_number
        varchar vehicle_vin
        varchar driver
        datetime accident_at
        varchar location
        text description
        varchar coverage
        varchar victim
        int compensation
        int personal_compensation
        int property_compensation
        int paid
        varchar manager
        varchar status
        text compensation_note
        json items
        bigint created_by_id FK
        datetime created_at
        datetime updated_at
    }
```

## 화면/API 경계

| Vue 화면 | 주 API | 주요 테이블 |
|---|---|---|
| 차량관리 대시보드 | `GET /vehicle/fleet-site/` | `Vehicle`, `FleetVehicleRecord`, `FleetSubscriptionContract`, `FleetReturnRecord`, `FleetInsurancePolicy`, `FleetAccidentCase`, `FleetVehicleDocument` |
| 차량 목록 | `GET /vehicle/fleet-site/`, `PATCH /vehicle/fleet-records/{id}/status/`, `PATCH /vehicle/vehicles/{id}/status/` | `Vehicle`, `FleetVehicleRecord` |
| 구독 전자계약 | `GET /vehicle/fleet-site/`, `/vehicle/fleet-subscriptions/` | `FleetSubscriptionContract` |
| 반납/수리비 | `GET /vehicle/fleet-site/`, `/vehicle/fleet-returns/` | `FleetReturnRecord` |
| 보험 | `GET /vehicle/fleet-site/`, `/vehicle/fleet-insurances/` | `FleetInsurancePolicy` |
| 사고 관리 | `GET /vehicle/fleet-site/`, `/vehicle/fleet-accidents/` | `FleetAccidentCase` |
| 현장관리 앱 요청 | `/vehicle/subscriptions/`, `/vehicle/returns/`, `/vehicle/as-requests/` | `SubscriptionRequest`, `ReturnRequest`, `ASRequest` |

## 설계 메모

- 운영 웹의 현재 기준 화면은 `fleet_*` 테이블을 중심으로 한다.
- `Vehicle`은 실제 차량 마스터이며, `FleetVehicleRecord`는 대폐차와 차량번호 기준 이력을 보존한다.
- `FleetSiteViewSet`은 여러 테이블을 차량번호별 그룹으로 묶어 Vue 화면에 전달하는 read-model 역할을 한다.
- 정적 `/fleet-management/` HTML은 마이그레이션 기간 동안 fallback으로 유지하되, 신규 진입점은 Vue 라우트 `/portal/vehicle/*`로 둔다.
