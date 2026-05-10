from django.urls import path
from .views import RoutePlannerView, HealthView

urlpatterns = [
    path('route/', RoutePlannerView.as_view(), name='route-planner'),
    path('health/', HealthView.as_view(), name='health'),
]
