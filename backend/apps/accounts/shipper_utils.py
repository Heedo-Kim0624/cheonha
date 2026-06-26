from apps.common.company_scope import DEFAULT_COMPANY_APP

DEFAULT_SHIPPER_CODE = "kurly"
FILE_UPLOAD_SHIPPERS = {"kurly"}
TEXT_UPLOAD_SHIPPERS = {"coupang"}


def normalize_shipper_code(value):
    return str(value or DEFAULT_SHIPPER_CODE).strip().lower() or DEFAULT_SHIPPER_CODE


def get_company_enabled_shippers(company_app=None):
    company_app = str(company_app or DEFAULT_COMPANY_APP).strip().lower() or DEFAULT_COMPANY_APP
    try:
        from apps.accounts.models import CompanyApp

        company = CompanyApp.objects.filter(code=company_app).first()
        if company and company.enabled_shippers:
            return [
                normalize_shipper_code(code)
                for code in company.enabled_shippers
                if normalize_shipper_code(code)
            ] or [DEFAULT_SHIPPER_CODE]
    except Exception:
        pass
    return [DEFAULT_SHIPPER_CODE]


def shipper_is_enabled(company_app=None, shipper_code=None):
    shipper_code = normalize_shipper_code(shipper_code)
    return shipper_code in get_company_enabled_shippers(company_app)
