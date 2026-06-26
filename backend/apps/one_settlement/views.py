from urllib.parse import quote

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.company_scope import get_company_app_from_request

from .constants import SHIPPER_CODE
from .models import OneDriver, OneSettlementUpload
from .serializers import OneSettlementUploadSerializer
from .services import (
    build_collection_excel,
    build_collection_table,
    delete_one_upload,
    build_driver_statement,
    build_month_summary,
    build_statement_excel,
    build_statement_pdf,
    ensure_one_company_access,
    import_one_file,
    list_drivers,
    update_statement_override,
)


def _current_month():
    return timezone.localdate().strftime("%Y-%m")


class OneUploadViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _company_app(self):
        return ensure_one_company_access(get_company_app_from_request(self.request))

    def list(self, request):
        company_app = self._company_app()
        month = request.query_params.get("month") or _current_month()
        queryset = OneSettlementUpload.objects.filter(
            company_app=company_app,
            shipper_code=SHIPPER_CODE,
            month=month,
        ).order_by("-delivery_date", "-created_at")
        return Response(OneSettlementUploadSerializer(queryset, many=True).data)

    def create(self, request):
        company_app = self._company_app()
        files = request.FILES.getlist("files") or request.FILES.getlist("file")
        if not files and request.FILES.get("file"):
            files = [request.FILES["file"]]
        if not files:
            return Response({"detail": "업로드할 xlsx 파일을 선택해 주세요."}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        imported_count = 0
        duplicate_count = 0
        error_count = 0
        for uploaded_file in files:
            try:
                result = import_one_file(
                    company_app=company_app,
                    uploaded_by=request.user,
                    uploaded_file=uploaded_file,
                )
                upload = result["upload"]
                is_duplicate = bool(result["duplicate"])
                imported_count += 0 if is_duplicate else 1
                duplicate_count += 1 if is_duplicate else 0
                results.append({
                    "ok": True,
                    "duplicate": is_duplicate,
                    "filename": uploaded_file.name,
                    "upload": OneSettlementUploadSerializer(upload).data,
                })
            except Exception as exc:
                error_count += 1
                results.append({
                    "ok": False,
                    "duplicate": False,
                    "filename": uploaded_file.name,
                    "detail": str(exc),
                })

        response_status = status.HTTP_201_CREATED if imported_count else (
            status.HTTP_200_OK if duplicate_count and not error_count else status.HTTP_400_BAD_REQUEST
        )
        return Response({
            "imported_count": imported_count,
            "duplicate_count": duplicate_count,
            "error_count": error_count,
            "results": results,
        }, status=response_status)

    def destroy(self, request, pk=None):
        company_app = self._company_app()
        upload = get_object_or_404(
            OneSettlementUpload,
            id=pk,
            company_app=company_app,
            shipper_code=SHIPPER_CODE,
        )
        result = delete_one_upload(company_app=company_app, upload_id=upload.id)
        return Response(result, status=status.HTTP_200_OK)


class OneSummaryViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        company_app = ensure_one_company_access(get_company_app_from_request(request))
        month = request.query_params.get("month") or _current_month()
        return Response(build_month_summary(company_app, month))

    @action(detail=False, methods=["get"], url_path="collection")
    def collection(self, request):
        company_app = ensure_one_company_access(get_company_app_from_request(request))
        month = request.query_params.get("month") or _current_month()
        page = request.query_params.get("page") or 1
        page_size = request.query_params.get("page_size") or 200
        return Response(build_collection_table(company_app, month, page=page, page_size=page_size))

    @action(detail=False, methods=["get"], url_path="collection-export")
    def collection_xlsx(self, request):
        company_app = ensure_one_company_access(get_company_app_from_request(request))
        month = request.query_params.get("month") or _current_month()
        content = build_collection_excel(company_app, month)
        filename = f"ONE_{month}_취합B_기사.xlsx"
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response


class OneDriverViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        company_app = ensure_one_company_access(get_company_app_from_request(request))
        month = request.query_params.get("month") or _current_month()
        return Response(list_drivers(company_app, month))

    @action(detail=True, methods=["get"], url_path="statement")
    def statement(self, request, pk=None):
        company_app = ensure_one_company_access(get_company_app_from_request(request))
        month = request.query_params.get("month") or _current_month()
        return Response(build_driver_statement(company_app, month, pk))


class OneStatementViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def partial_update(self, request, pk=None):
        company_app = ensure_one_company_access(get_company_app_from_request(request))
        override = update_statement_override(
            override_id=pk,
            company_app=company_app,
            payload=request.data or {},
            user=request.user,
        )
        statement = build_driver_statement(company_app, override.month, override.driver_id)
        return Response(statement)

    @action(detail=True, methods=["get"], url_path="export.xlsx")
    def export_xlsx(self, request, pk=None):
        company_app = ensure_one_company_access(get_company_app_from_request(request))
        driver = OneDriver.objects.get(statement_overrides__id=pk, company_app=company_app)
        override = driver.statement_overrides.get(id=pk, company_app=company_app)
        statement = build_driver_statement(company_app, override.month, driver.id)
        content = build_statement_excel(statement)
        filename = f"ONE_{statement['month']}_{statement['driver']['name']}.xlsx"
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response

    @action(detail=True, methods=["get"], url_path="export.pdf")
    def export_pdf(self, request, pk=None):
        company_app = ensure_one_company_access(get_company_app_from_request(request))
        driver = OneDriver.objects.get(statement_overrides__id=pk, company_app=company_app)
        override = driver.statement_overrides.get(id=pk, company_app=company_app)
        statement = build_driver_statement(company_app, override.month, driver.id)
        content = build_statement_pdf(statement)
        filename = f"ONE_{statement['month']}_{statement['driver']['name']}.pdf"
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response
