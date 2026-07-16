from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import Tenant, User


class TenantModelTest(TestCase):
    """Tests Tenant model creation and field validation rules."""

    def setUp(self) -> None:
        self.tenant_data = {
            "name": "Acme Corp",
            "slug": "acme",
            "azure_search_index_name": "documind-acme-index",
        }

    def test_tenant_creation_success(self) -> None:
        """Verifies tenant is successfully created with correct attributes and defaults."""
        tenant = Tenant.objects.create(**self.tenant_data)
        self.assertEqual(tenant.name, "Acme Corp")
        self.assertEqual(tenant.slug, "acme")
        self.assertEqual(tenant.subscription_tier, Tenant.SubscriptionTier.TRIAL)
        self.assertTrue(tenant.is_active)
        self.assertIsNotNone(tenant.id)

    def test_tenant_slug_uniqueness(self) -> None:
        """Verifies duplicate tenant slugs raise an integrity violation."""
        Tenant.objects.create(**self.tenant_data)
        with self.assertRaises(IntegrityError):
            Tenant.objects.create(
                name="Acme Copy",
                slug="acme",
                azure_search_index_name="documind-acme-index-copy",
            )


class UserModelTest(TestCase):
    """Tests custom User model, roles, and UserManager constraints."""

    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(
            name="Testing Tenant",
            slug="test-tenant",
            azure_search_index_name="documind-test-index",
        )
        self.user_data = {
            "email": "user@example.com",
            "full_name": "John Doe",
            "password": "securepassword123",
            "tenant": self.tenant,
            "role": User.Role.MEMBER,
        }

    def test_create_user_success(self) -> None:
        """Verifies a user is successfully created with appropriate role and tenant."""
        user = User.objects.create_user(
            email="user@example.com",
            full_name="John Doe",
            password="securepassword123",
            tenant=self.tenant,
            role=User.Role.MEMBER,
        )
        self.assertEqual(user.email, "user@example.com")
        self.assertEqual(user.full_name, "John Doe")
        self.assertEqual(user.role, User.Role.MEMBER)
        self.assertEqual(user.tenant, self.tenant)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("securepassword123"))

    def test_create_user_without_email_fails(self) -> None:
        """Verifies that creating a user without an email address raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            User.objects.create_user(
                email="",
                full_name="No Email",
                password="password",
                tenant=self.tenant,
            )
        self.assertEqual(str(ctx.exception), "The Email field must be set.")

    def test_create_regular_user_without_tenant_fails(self) -> None:
        """Verifies that regular users must be linked to a tenant, otherwise raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            User.objects.create_user(
                email="notenant@example.com",
                full_name="No Tenant",
                password="password",
                tenant=None,
            )
        self.assertEqual(
            str(ctx.exception), "Regular users must be associated with a valid Tenant."
        )

    def test_create_superuser_success(self) -> None:
        """Verifies superuser creation requires no tenant and gets ADMIN, is_staff, is_superuser."""
        superuser = User.objects.create_superuser(
            email="admin@documind.com",
            full_name="Global Admin",
            password="adminpassword",
        )
        self.assertEqual(superuser.email, "admin@documind.com")
        self.assertEqual(superuser.role, User.Role.ADMIN)
        self.assertIsNone(superuser.tenant)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)


class CreateTenantCommandTest(TestCase):
    """Tests the create_tenant administrative CLI management command."""

    def test_create_tenant_command_success(self) -> None:
        """Verifies that running create_tenant CLI command generates Tenant and Admin user."""
        call_command(
            "create_tenant",
            name="Initech Org",
            slug="initech",
            tier="STANDARD",
            email="peter@initech.com",
            full_name="Peter Gibbons",
            password="pcs-load-letter",
        )

        tenant = Tenant.objects.get(slug="initech")
        self.assertEqual(tenant.name, "Initech Org")
        self.assertEqual(tenant.subscription_tier, Tenant.SubscriptionTier.STANDARD)
        self.assertEqual(tenant.azure_search_index_name, "documind-initech-index")

        user = User.objects.get(email="peter@initech.com")
        self.assertEqual(user.full_name, "Peter Gibbons")
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertEqual(user.tenant, tenant)
        self.assertTrue(user.check_password("pcs-load-letter"))

    def test_create_tenant_command_duplicate_slug_fails(self) -> None:
        """Verifies that create_tenant raises CommandError if tenant slug is already taken."""
        Tenant.objects.create(
            name="Existing Tenant",
            slug="initech",
            azure_search_index_name="documind-initech-index",
        )

        with self.assertRaises(CommandError) as ctx:
            call_command(
                "create_tenant",
                name="Initech New",
                slug="initech",
                email="peter@initech.com",
                full_name="Peter Gibbons",
                password="pcs-load-letter",
            )
        self.assertIn(
            "A tenant with slug 'initech' already exists.", str(ctx.exception)
        )

    def test_create_tenant_command_duplicate_email_fails(self) -> None:
        """Verifies that create_tenant raises CommandError if email is already taken."""
        tenant = Tenant.objects.create(
            name="Initech Org",
            slug="initech",
            azure_search_index_name="documind-initech-index",
        )
        User.objects.create_user(
            email="peter@initech.com",
            full_name="Peter Original",
            password="password",
            tenant=tenant,
        )

        with self.assertRaises(CommandError) as ctx:
            call_command(
                "create_tenant",
                name="Initech Copy",
                slug="initech-copy",
                email="peter@initech.com",
                full_name="Peter Gibbons",
                password="pcs-load-letter",
            )
        self.assertIn(
            "A user with email 'peter@initech.com' already exists.", str(ctx.exception)
        )
