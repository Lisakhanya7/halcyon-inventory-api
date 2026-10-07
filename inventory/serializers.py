from rest_framework import serializers

from inventory.models import Category, InventoryTransaction, Product, Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "email", "created_at"]
        read_only_fields = ["id", "created_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]
        read_only_fields = ["id"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id", "sku", "name", "description", "supplier", "categories",
            "quantity_on_hand", "unit_price", "active", "created_at",
        ]
        read_only_fields = ["id", "quantity_on_hand", "created_at"]


class InventoryTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryTransaction
        fields = ["id", "product", "movement", "quantity", "reference", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    database = serializers.CharField()
    uptime_seconds = serializers.FloatField()
