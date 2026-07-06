from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/dashboard/<int:hotel_id>/', consumers.DashboardConsumer.as_asgi()),
    path('ws/telao/<int:hotel_id>/', consumers.TelaoConsumer.as_asgi()),
]
