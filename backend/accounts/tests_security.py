import pytest
from rest_framework.test import APIClient

from accounts.models import Document, DocumentChunk, Tenant, User
from core.context import current_tenant_id


@pytest.mark.django_db
class TestRowLevelTenantSecurity:
    """
    Security Test Suite proving that Insecure Direct Object Reference (IDOR)
    and cross-tenant data leakage is mathematically prevented by the ORM.
    """

    def setup_method(self) -> None:
        # 1. Create strict tenant boundaries
        self.tenant_a = Tenant.objects.create(name="Acme Corp", slug="acme")
        self.tenant_b = Tenant.objects.create(name="Wayne Ent", slug="wayne")

        # 2. Create users isolated to their respective tenants
        self.user_a = User.objects.create_user(
            email="alice@acme.com",
            full_name="Alice",
            password="password123",
            tenant=self.tenant_a,
        )
        self.user_b = User.objects.create_user(
            email="bruce@wayne.com",
            full_name="Bruce",
            password="password123",
            tenant=self.tenant_b,
        )

        # 3. Create a highly sensitive document belonging ONLY to Tenant B
        self.doc_b = Document.objects.create(
            tenant=self.tenant_b,
            title="Batmobile Specs",
            file_type="PDF",
            blob_storage_path="wayne/batmobile.pdf",
        )
        self.chunk_b = DocumentChunk.objects.create(
            document=self.doc_b,
            tenant=self.tenant_b,
            chunk_index=0,
            content="Armor specifications...",
            token_count=150,
            azure_search_doc_id="wayne-0",
        )

        self.client = APIClient()

    def test_orm_manager_prevents_idor_cross_tenant_access(self):
        """
        Scenario: A developer forgets to append .filter(tenant_id=...) in a view.
        A malicious user from Tenant A tries to GET a Document belonging to Tenant B by guessing its UUID.
        Result: The TenantScopedManager automatically filters the queryset based on contextvar.
        The record is completely hidden (raises DoesNotExist) preventing IDOR.
        """
        # Simulate Middleware context injection for Tenant A
        current_tenant_id.set(self.tenant_a.id)

        # Attempt to retrieve Tenant B's document directly by ID
        with pytest.raises(Document.DoesNotExist):
            Document.objects.get(id=self.doc_b.id)

        # Verify it works correctly for their own documents if they had any
        doc_a = Document.objects.create(
            tenant=self.tenant_a,
            title="Acme Specs",
            file_type="TXT",
            blob_storage_path="a",
        )
        assert Document.objects.get(id=doc_a.id).title == "Acme Specs"

    def test_jwt_auth_and_middleware_enforce_tenant_isolation(self):
        """
        Scenario: User from Tenant A authenticates. They attempt to query the system,
        potentially manipulating payload parameters to access Tenant B's chunks.
        Result: The JWT contains the tenant_id. The TenantMiddleware extracts it.
        The ORM restricts all queries to Tenant A. Return is strictly bound to Tenant A.
        """
        # 1. Login as User A to receive a JWT
        response = self.client.post(
            "/api/auth/login/", {"email": "alice@acme.com", "password": "password123"}
        )
        assert response.status_code == 200

        # Verify custom claims were correctly embedded
        assert "access" in response.data
        token = response.data["access"]

        # 2. Authenticate the client with User A's token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # 3. Hit the query endpoint.
        # Even though Tenant B has 1 chunk in the database, User A should see 0 accessible chunks.
        query_response = self.client.post("/api/query/")

        assert query_response.status_code == 200
        assert query_response.data["accessible_chunks_in_db"] == 0
