from rest_framework.routers import DefaultRouter
from .views import (
    CompanyViewSet, VehicleViewSet, PitRecordViewSet, CalendarEventViewSet,
    SubscriptionRequestViewSet, ReturnRequestViewSet, ASRequestViewSet,
    FleetSiteViewSet, FleetVehicleRecordViewSet, FleetVehicleDocumentViewSet,
    FleetSubscriptionContractViewSet, FleetReturnRecordViewSet,
    FleetInsurancePolicyViewSet, FleetAccidentCaseViewSet,
    FleetInspectionScheduleViewSet, FleetProfitRuleVersionViewSet,
    FleetProfitImportBatchViewSet, FleetProfitRawEntryViewSet,
    FleetProfitAdjustmentViewSet, FleetProfitMonthlySnapshotViewSet,
    FleetMonthlyCloseViewSet,
)

router = DefaultRouter()
router.register(r'companies',     CompanyViewSet,             basename='vm-company')
router.register(r'vehicles',      VehicleViewSet,             basename='vm-vehicle')
router.register(r'pit-records',   PitRecordViewSet,           basename='vm-pit')
router.register(r'calendar',      CalendarEventViewSet,       basename='vm-calendar')
router.register(r'subscriptions', SubscriptionRequestViewSet, basename='vm-subscription')
router.register(r'returns',       ReturnRequestViewSet,       basename='vm-return')
router.register(r'as-requests',   ASRequestViewSet,           basename='vm-as')
router.register(r'fleet-site',    FleetSiteViewSet,           basename='vm-fleet-site')
router.register(r'fleet-records', FleetVehicleRecordViewSet,  basename='vm-fleet-record')
router.register(r'fleet-documents', FleetVehicleDocumentViewSet, basename='vm-fleet-document')
router.register(r'fleet-subscriptions', FleetSubscriptionContractViewSet, basename='vm-fleet-subscription')
router.register(r'fleet-returns', FleetReturnRecordViewSet,   basename='vm-fleet-return')
router.register(r'fleet-insurances', FleetInsurancePolicyViewSet, basename='vm-fleet-insurance')
router.register(r'fleet-accidents', FleetAccidentCaseViewSet, basename='vm-fleet-accident')
router.register(r'fleet-inspections', FleetInspectionScheduleViewSet, basename='vm-fleet-inspection')
router.register(r'fleet-profit-rules', FleetProfitRuleVersionViewSet, basename='vm-fleet-profit-rule')
router.register(r'fleet-profit-batches', FleetProfitImportBatchViewSet, basename='vm-fleet-profit-batch')
router.register(r'fleet-profit-raw', FleetProfitRawEntryViewSet, basename='vm-fleet-profit-raw')
router.register(r'fleet-profit-adjustments', FleetProfitAdjustmentViewSet, basename='vm-fleet-profit-adjustment')
router.register(r'fleet-profit-snapshots', FleetProfitMonthlySnapshotViewSet, basename='vm-fleet-profit-snapshot')
router.register(r'fleet-monthly-closes', FleetMonthlyCloseViewSet, basename='vm-fleet-monthly-close')

urlpatterns = router.urls
