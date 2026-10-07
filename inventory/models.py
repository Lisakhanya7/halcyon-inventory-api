from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class Supplier(models.Model):
    name = models.CharField(max_length=160, unique=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        validators=[RegexValidator(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", "Use a valid SKU.")],
    )
    name = models.CharField(max_length=160, db_index=True)
    description = models.TextField(blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="products")
    categories = models.ManyToManyField(Category, related_name="products", blank=True)
    quantity_on_hand = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["supplier", "active"], name="product_supplier_active_idx")]

    def __str__(self):
        return f"{self.sku} - {self.name}"


class InventoryTransaction(models.Model):
    class Movement(models.TextChoices):
        IN = "IN", "Inbound"
        OUT = "OUT", "Outbound"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="transactions")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_transactions",
    )
    movement = models.CharField(max_length=3, choices=Movement.choices)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "created_at"], name="txn_product_created_idx"),
            models.Index(fields=["created_by", "created_at"], name="txn_user_created_idx"),
        ]

    def __str__(self):
        return f"{self.movement} {self.quantity} x {self.product.sku}"
