import time

from django.db import connection, transaction
from django.db.models import F
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view

from inventory.models import Category, InventoryTransaction, Product, Supplier
from inventory.permissions import IsOwnerOrStaff, StaffWriteOrReadOnly
from inventory.serializers import (
    CategorySerializer,
    HealthSerializer,
    InventoryTransactionSerializer,
    ProductSerializer,
    SupplierSerializer,
)

STARTED_AT = time.monotonic()


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [StaffWriteOrReadOnly]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [StaffWriteOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("supplier").prefetch_related("categories")
    serializer_class = ProductSerializer
    permission_classes = [StaffWriteOrReadOnly]


@extend_schema_view(
    retrieve=extend_schema(parameters=[
        OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH),
    ]),
    update=extend_schema(parameters=[
        OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH),
    ]),
    partial_update=extend_schema(parameters=[
        OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH),
    ]),
    destroy=extend_schema(parameters=[
        OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH),
    ]),
)
class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        queryset = InventoryTransaction.objects.select_related("product", "created_by")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        product_id = serializer.validated_data["product"].pk
        movement = serializer.validated_data["movement"]
        quantity = serializer.validated_data["quantity"]
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product_id)
            self._apply_stock_change(product, movement, quantity)
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        with transaction.atomic():
            existing = InventoryTransaction.objects.select_for_update().get(
                pk=self.get_object().pk
            )
            product_ids = {
                existing.product_id,
                serializer.validated_data.get("product", existing.product).pk,
            }
            products = {
                item.pk: item
                for item in Product.objects.select_for_update()
                .filter(pk__in=product_ids)
                .order_by("pk")
            }
            updated_product = serializer.validated_data.get("product", existing.product)
            new_movement = serializer.validated_data.get("movement", existing.movement)
            new_quantity = serializer.validated_data.get("quantity", existing.quantity)
            self._apply_stock_change(
                products[existing.product_id],
                existing.movement,
                existing.quantity,
                reverse=True,
            )
            self._apply_stock_change(
                products[updated_product.pk], new_movement, new_quantity
            )
            serializer.save()

    def perform_destroy(self, instance):
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=instance.product_id)
            self._apply_stock_change(
                product, instance.movement, instance.quantity, reverse=True
            )
            instance.delete()

    @staticmethod
    def _apply_stock_change(product, movement, quantity, reverse=False):
        increase = movement == InventoryTransaction.Movement.IN
        if reverse:
            increase = not increase
        if increase:
            Product.objects.filter(pk=product.pk).update(
                quantity_on_hand=F("quantity_on_hand") + quantity
            )
            product.refresh_from_db(fields=["quantity_on_hand"])
            return
        if product.quantity_on_hand < quantity:
            raise ValidationError(
                {"quantity": "Insufficient stock for this outbound movement."}
            )
        Product.objects.filter(pk=product.pk).update(
            quantity_on_hand=F("quantity_on_hand") - quantity
        )
        product.refresh_from_db(fields=["quantity_on_hand"])


class HealthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=HealthSerializer)
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            database_status = "connected"
            http_status = status.HTTP_200_OK
        except Exception:
            database_status = "disconnected"
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        return Response({
            "status": "ok" if database_status == "connected" else "degraded",
            "database": database_status,
            "uptime_seconds": round(time.monotonic() - STARTED_AT, 2),
        }, status=http_status)
