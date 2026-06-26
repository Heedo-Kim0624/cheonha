from django.conf import settings
from django.db import models


class OneDriver(models.Model):
    company_app = models.CharField(max_length=40, db_index=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["company_app", "name"], name="one_driver_company_name_uniq"),
        ]
        indexes = [
            models.Index(fields=["company_app", "name"], name="one_driver_company_name_idx"),
        ]

    def __str__(self):
        return f"{self.company_app}:{self.name}"


class OneSettlementUpload(models.Model):
    class Status(models.TextChoices):
        IMPORTED = "IMPORTED", "Imported"
        NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"
        ERROR = "ERROR", "Error"

    company_app = models.CharField(max_length=40, db_index=True)
    shipper_code = models.CharField(max_length=40, default="one", db_index=True)
    month = models.CharField(max_length=7, db_index=True)
    delivery_date = models.DateField(null=True, blank=True, db_index=True)
    file = models.FileField(upload_to="one/%Y/%m/%d/")
    original_filename = models.CharField(max_length=500, blank=True, default="")
    raw_hash = models.CharField(max_length=64, db_index=True)
    total_rows = models.PositiveIntegerField(default=0)
    order_count = models.PositiveIntegerField(default=0)
    mapped_order_count = models.PositiveIntegerField(default=0)
    unmapped_order_count = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    validation_errors = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IMPORTED, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="one_settlement_uploads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-delivery_date", "-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company_app", "shipper_code", "raw_hash"],
                name="one_upload_company_shipper_raw_hash_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["company_app", "shipper_code", "month"], name="one_upload_company_month_idx"),
            models.Index(fields=["company_app", "shipper_code", "delivery_date"], name="one_upload_company_date_idx"),
        ]

    def __str__(self):
        return f"{self.company_app}/{self.month}/{self.original_filename or self.pk}"


class OneShipmentOrder(models.Model):
    upload = models.ForeignKey(
        OneSettlementUpload,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    company_app = models.CharField(max_length=40, db_index=True)
    shipper_code = models.CharField(max_length=40, default="one", db_index=True)
    month = models.CharField(max_length=7, db_index=True)
    delivery_date = models.DateField(db_index=True)
    driver = models.ForeignKey(OneDriver, on_delete=models.CASCADE, related_name="shipment_orders")
    driver_name = models.CharField(max_length=100, db_index=True)
    order_number = models.CharField(max_length=80, db_index=True)
    fee_name = models.CharField(max_length=200, db_index=True)
    service_code = models.CharField(max_length=40, blank=True, default="", db_index=True)
    category_code = models.CharField(max_length=40, blank=True, default="", db_index=True)
    city = models.CharField(max_length=100, blank=True, default="")
    boxes = models.PositiveIntegerField(default=0)
    extra_boxes = models.PositiveIntegerField(default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    base_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    jongno_extra_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    is_mapped = models.BooleanField(default=False, db_index=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["delivery_date", "driver_name", "fee_name", "order_number"]
        indexes = [
            models.Index(fields=["company_app", "shipper_code", "month", "driver"], name="one_order_driver_month_idx"),
            models.Index(fields=["company_app", "shipper_code", "delivery_date"], name="one_order_company_date_idx"),
            models.Index(fields=["service_code", "category_code"], name="one_order_service_category_idx"),
            models.Index(fields=["company_app", "shipper_code", "month", "delivery_date", "id"], name="one_order_month_date_id_idx"),
            models.Index(fields=["company_app", "shipper_code", "month", "service_code", "category_code"], name="one_order_month_svc_cat_idx"),
            models.Index(fields=["company_app", "shipper_code", "month", "driver", "service_code", "category_code"], name="one_order_month_driver_svc_idx"),
            models.Index(fields=["company_app", "shipper_code", "month", "delivery_date", "driver_name", "service_code", "category_code", "order_number", "id"], name="one_order_month_collect_idx"),
        ]

    def __str__(self):
        return f"{self.delivery_date} {self.driver_name} {self.order_number}"


class OneDriverStatementOverride(models.Model):
    company_app = models.CharField(max_length=40, db_index=True)
    shipper_code = models.CharField(max_length=40, default="one", db_index=True)
    month = models.CharField(max_length=7, db_index=True)
    driver = models.ForeignKey(OneDriver, on_delete=models.CASCADE, related_name="statement_overrides")
    payment_due_date = models.DateField(null=True, blank=True)
    manual_items = models.JSONField(default=list, blank=True)
    memo = models.TextField(blank=True, default="")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="one_statement_overrides",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-month", "driver__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company_app", "shipper_code", "month", "driver"],
                name="one_statement_override_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.company_app}/{self.month}/{self.driver}"
