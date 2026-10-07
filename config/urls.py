from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from inventory.views import CategoryViewSet, HealthView, ProductViewSet, SupplierViewSet
from inventory.views import TransactionViewSet

router = DefaultRouter()
router.register("suppliers", SupplierViewSet)
router.register("categories", CategoryViewSet)
router.register("products", ProductViewSet)
router.register("transactions", TransactionViewSet, basename="transaction")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("health/", HealthView.as_view(), name="health"),
]
