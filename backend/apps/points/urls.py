from django.urls import path

from . import views

urlpatterns = [
    path("items/", views.point_items, name="point-items"),
    path("items/<int:item_id>/", views.point_item_detail, name="point-item-detail"),
    path("summaries/", views.crew_point_summaries, name="point-summaries"),
    path("crew/<int:crew_id>/", views.crew_point_detail, name="crew-point-detail"),
    path("crew/<int:crew_id>/set-balance/", views.set_crew_point_balance, name="crew-point-set-balance"),
    path("redemptions/<int:redemption_id>/confirm/", views.confirm_redemption, name="point-redemption-confirm"),
    path("redemptions/<int:redemption_id>/cancel/", views.cancel_redemption, name="point-redemption-cancel"),
]
