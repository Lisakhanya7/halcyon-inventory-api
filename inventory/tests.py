from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from inventory.models import Category, InventoryTransaction, Product, Supplier


class InventoryApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="staff",
            password="strong-test-password",
            is_staff=True,
        )
        self.user = user_model.objects.create_user(
            username="worker", password="strong-test-password"
        )
        self.supplier = Supplier.objects.create(name="Acme Supply")
        self.category = Category.objects.create(name="Hardware")
        self.product = Product.objects.create(
            sku="BOLT-1",
            name="Steel bolt",
            supplier=self.supplier,
            unit_price=Decimal("1.25"),
        )
        self.product.categories.add(self.category)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_catalog_crud_requires_staff_for_writes(self):
        self.authenticate(self.user)
        self.assertEqual(self.client.get("/api/products/").status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post("/api/products/", {}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.authenticate(self.staff)
        supplier_response = self.client.post(
            "/api/suppliers/", {"name": "North Star", "email": "ops@example.com"}
        )
        self.assertEqual(supplier_response.status_code, status.HTTP_201_CREATED)
        category_response = self.client.post("/api/categories/", {"name": "Fasteners"})
        self.assertEqual(category_response.status_code, status.HTTP_201_CREATED)
        product_response = self.client.patch(
            f"/api/products/{self.product.pk}/", {"name": "Hardened steel bolt"}
        )
        self.assertEqual(product_response.status_code, status.HTTP_200_OK)
        self.assertEqual(product_response.data["name"], "Hardened steel bolt")
        deleted = self.client.delete(f"/api/categories/{category_response.data['id']}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

    def test_movements_change_stock_and_users_only_see_their_own(self):
        self.authenticate(self.user)
        inbound = self.client.post("/api/transactions/", {
            "product": self.product.pk,
            "movement": "IN",
            "quantity": 10,
            "reference": "PO-1",
        })
        self.assertEqual(inbound.status_code, status.HTTP_201_CREATED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_on_hand, 10)

        outbound = self.client.post("/api/transactions/", {
            "product": self.product.pk, "movement": "OUT", "quantity": 8,
        })
        self.assertEqual(outbound.status_code, status.HTTP_201_CREATED)
        insufficient = self.client.post("/api/transactions/", {
            "product": self.product.pk, "movement": "OUT", "quantity": 3,
        })
        self.assertEqual(insufficient.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", insufficient.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_on_hand, 2)

        self.client.patch(
            f"/api/transactions/{outbound.data['id']}/", {"quantity": 9}
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_on_hand, 1)
        self.client.delete(f"/api/transactions/{outbound.data['id']}/")
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_on_hand, 10)

        other = get_user_model().objects.create_user(
            username="other", password="strong-test-password"
        )
        InventoryTransaction.objects.create(
            product=self.product, created_by=other, movement="IN", quantity=1
        )
        self.assertEqual(len(self.client.get("/api/transactions/").data), 1)

    def test_standard_user_cannot_access_another_users_movement(self):
        other = get_user_model().objects.create_user(
            username="other", password="strong-test-password"
        )
        movement = InventoryTransaction.objects.create(
            product=self.product, created_by=other, movement="IN", quantity=2
        )
        self.authenticate(self.user)
        response = self.client.get(f"/api/transactions/{movement.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_product_validation_and_delete(self):
        self.authenticate(self.staff)
        response = self.client.post("/api/products/", {
            "sku": "BAD SKU",
            "name": "Invalid",
            "supplier": self.supplier.pk,
            "unit_price": "2.00",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        deleted = self.client.delete(f"/api/products/{self.product.pk}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

    def test_health_and_jwt_endpoints_are_available(self):
        health = self.client.get("/health/")
        self.assertEqual(health.status_code, status.HTTP_200_OK)
        self.assertEqual(health.data["database"], "connected")
        self.assertIn("uptime_seconds", health.data)
        token = self.client.post("/api/token/", {
            "username": "worker", "password": "strong-test-password",
        })
        self.assertEqual(token.status_code, status.HTTP_200_OK)
        self.assertIn("access", token.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.data['access']}")
        self.assertEqual(self.client.get("/api/products/").status_code, status.HTTP_200_OK)

    def test_api_is_authenticated_by_default(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class InventoryModelTests(APITestCase):
    def test_related_models_and_string_representation(self):
        user = get_user_model().objects.create_user(username="model-user", password="test-password")
        supplier = Supplier.objects.create(name="Model Supplier")
        category = Category.objects.create(name="Model Category")
        product = Product.objects.create(
            sku="MODEL-1", name="Model product", supplier=supplier, unit_price=Decimal("3.50")
        )
        product.categories.add(category)
        movement = InventoryTransaction.objects.create(
            product=product, created_by=user, movement="IN", quantity=4
        )
        self.assertIn(product, category.products.all())
        self.assertEqual(str(supplier), "Model Supplier")
        self.assertEqual(str(category), "Model Category")
        self.assertEqual(str(product), "MODEL-1 - Model product")
        self.assertEqual(str(movement), "IN 4 x MODEL-1")
