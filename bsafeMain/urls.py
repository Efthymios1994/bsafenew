from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, TechnicianViewSet,AppointmentViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'technicians', TechnicianViewSet)
router.register(r'appointments', AppointmentViewSet, basename='appointment')
urlpatterns = [
    path('', include(router.urls)),
]