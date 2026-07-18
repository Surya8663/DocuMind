"""DocuMind Multi-Tenancy Architectural Decisions & Models

ARCHITECTURAL COMPARISON: SINGLE TENANT PER USER VS. MANY-TO-MANY (TENANT MEMBERSHIP)

For an enterprise B2B SaaS RAG system, we evaluated two tenant-to-user mappings:

1. SINGLE TENANT PER USER (Selected Baseline)
   - Rationale: The custom User model links directly to a single Tenant via a ForeignKey
     (null=True only for global superusers/staff).
   - Tradeoffs:
     * Pros: Maximizes data isolation. Since queries are scoped to user.tenant_id, there is
       virtually zero chance of "tenant leakage" (data leaking between organizations). This is
       a critical security requirement for SOC2, HIPAA, and general enterprise compliance
       when indexing proprietary documents.
     * Cons: A user who is a consultant or auditor needing access to multiple client tenants
       must register separate email accounts or use email sub-addressing (e.g., john+t1@example.com).

2. MANY-TO-MANY (TENANT MEMBERSHIP THROUGH-MODEL)
   - Rationale: Users map to multiple Tenants via a through-model containing tenant-specific roles.
   - Tradeoffs:
     * Pros: Better user experience. A user logs in once and toggles between multiple workspaces
       (similar to Slack, GitHub, or Notion).
     * Cons: Significantly higher risk of tenant leakage bugs. Developers must ensure every single
       query joins and filters by the session's active_tenant_id rather than the user_id. This is
       susceptible to programmer oversight during schema extensions.

Conclusion:
Because DocuMind processes sensitive corporate documentation and interfaces directly with isolated
Azure AI Search indexes (where each tenant gets a separate index mapped in the database), we prioritize
strict data isolation and compliance. Thus, we enforce the Single Tenant per User model. If multi-tenant
access is later requested for support roles or external auditors, we will implement it through explicit,
auditable cross-tenant impersonation permissions rather than relaxing the data isolation model.
"""

import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.postgres.fields import ArrayField
from django.db import models

from core.managers import TenantScopedManager


class Tenant(models.Model):
    """Represents a customer organization or tenant within the DocuMind system."""

    class SubscriptionTier(models.TextChoices):
        TRIAL = "TRIAL", "Trial"
        STANDARD = "STANDARD", "Standard"
        ENTERPRISE = "ENTERPRISE", "Enterprise"

    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    name: models.CharField = models.CharField(max_length=255)
    slug: models.SlugField = models.SlugField(max_length=255, unique=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    subscription_tier: models.CharField = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.TRIAL,
    )
    azure_search_index_name: models.CharField = models.CharField(
        max_length=255,
        help_text="Name of the isolated Azure AI Search index mapped to this tenant.",
    )
    is_active: models.BooleanField = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.subscription_tier})"


class UserManager(BaseUserManager):
    """Custom manager to handle user and superuser creation under multi-tenant constraints."""

    def create_user(
        self,
        email: str,
        full_name: str,
        password: str | None = None,
        tenant: Tenant | None = None,
        role: str = "MEMBER",
        **extra_fields,
    ) -> "User":
        """Creates and saves a User with the given email, full name, tenant, and role."""
        if not email:
            raise ValueError("The Email field must be set.")
        email = self.normalize_email(email)

        # Enforce that non-superusers must belong to a tenant
        is_superuser = extra_fields.get("is_superuser", False)
        is_staff = extra_fields.get("is_staff", False)
        if not tenant and not (is_superuser or is_staff):
            raise ValueError("Regular users must be associated with a valid Tenant.")

        user = self.model(
            email=email,
            full_name=full_name,
            tenant=tenant,
            role=role,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, full_name: str, password: str | None = None, **extra_fields
    ) -> "User":
        """Creates and saves a global superuser without a tenant."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            email=email,
            full_name=full_name,
            password=password,
            tenant=None,
            role=User.Role.ADMIN,
            **extra_fields,
        )


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model containing roles and tenant links, replacing Django defaults."""

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MEMBER = "MEMBER", "Member"
        VIEWER = "VIEWER", "Viewer"

    email: models.EmailField = models.EmailField(unique=True)
    full_name: models.CharField = models.CharField(max_length=255)
    role: models.CharField = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    # PROTECT ensures a tenant cannot be deleted if users are still linked to it.
    tenant: models.ForeignKey = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        null=True,  # Nullable ONLY for global superusers/staff
        blank=True,
        related_name="users",
    )
    is_active: models.BooleanField = models.BooleanField(default=True)
    is_staff: models.BooleanField = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )
    date_joined: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self) -> str:
        tenant_name = self.tenant.name if self.tenant else "Global/System"
        return f"{self.email} ({self.role} @ {tenant_name})"


class Document(models.Model):
    """Represents a raw document uploaded by a user within a tenant's corpus."""

    objects = TenantScopedManager()

    class FileType(models.TextChoices):
        PDF = "PDF", "PDF Document"
        DOCX = "DOCX", "Word Document"
        TXT = "TXT", "Text File"

    class DocType(models.TextChoices):
        POLICY = "POLICY", "Policy"
        CONTRACT = "CONTRACT", "Contract"
        REPORT = "REPORT", "Report"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        PROCESSING = "PROCESSING", "Processing"
        INDEXED = "INDEXED", "Indexed"
        FAILED = "FAILED", "Failed"

    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant: models.ForeignKey = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True,
    )
    uploaded_by: models.ForeignKey = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    title: models.CharField = models.CharField(max_length=255)
    file_type: models.CharField = models.CharField(
        max_length=10,
        choices=FileType.choices,
    )
    blob_storage_path: models.CharField = models.CharField(max_length=1024)
    doc_type: models.CharField = models.CharField(
        max_length=20,
        choices=DocType.choices,
        default=DocType.OTHER,
    )
    status: models.CharField = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )
    uploaded_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    indexed_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    page_count: models.IntegerField = models.IntegerField(null=True, blank=True)
    checksum: models.CharField = models.CharField(max_length=64, db_index=True)

    def __str__(self) -> str:
        return f"{self.title} ({self.file_type}) - {self.tenant.name}"


class DocumentChunk(models.Model):
    """Represents a parsed text chunk from a document, processed with embeddings.

    DENORMALIZATION RATIONALE:
    We explicitly denormalize `tenant_id` onto the DocumentChunk model.
    In a multi-tenant enterprise system, boundary isolation is critical. Direct vector indexing,
    bulk deletion, and retrieval searches filter by `tenant_id` first. Denormalizing this field
    prevents doing SQL JOIN queries back to the Document table for every single chunk retrieval,
    reducing latency and ensuring zero risk of cross-tenant data leaks.
    """

    objects = TenantScopedManager()

    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    document: models.ForeignKey = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    tenant: models.ForeignKey = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index: models.IntegerField = models.IntegerField()
    content: models.TextField = models.TextField()
    token_count: models.IntegerField = models.IntegerField()
    azure_search_doc_id: models.CharField = models.CharField(max_length=255)
    embedding_model: models.CharField = models.CharField(max_length=100)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Composite index for optimized scoped chunk retrievals per document
        indexes = [
            models.Index(fields=["tenant", "document"]),
        ]

    def __str__(self) -> str:
        return f"Chunk {self.chunk_index} of {self.document.title}"


class QueryLog(models.Model):
    """Represents an audit log of a user query and the grounding chunks retrieved."""

    objects = TenantScopedManager()

    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant: models.ForeignKey = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="query_logs",
    )
    user: models.ForeignKey = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="query_logs",
    )
    query_text: models.TextField = models.TextField()
    # ARRAYFIELD VS JSONFIELD CHOICE:
    # ArrayField is used to store the list of UUIDs representing retrieved chunks.
    # It guarantees type-safety (strictly UUIDs), supports Postgres-native array indexing (GIN),
    # and optimizes JOINs and aggregate query speeds compared to unstructured JSONField string parsing.
    retrieved_chunk_ids: ArrayField = ArrayField(models.UUIDField())
    answer_text: models.TextField = models.TextField()
    confidence_score: models.FloatField = models.FloatField()
    escalated: models.BooleanField = models.BooleanField(default=False)
    latency_ms: models.IntegerField = models.IntegerField()
    azure_search_latency_ms: models.IntegerField = models.IntegerField()
    llm_latency_ms: models.IntegerField = models.IntegerField()
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Query by {self.user.email if self.user else 'System'} at {self.created_at}"


class Feedback(models.Model):
    """Represents explicit user rating and comments on a generated response."""

    objects = TenantScopedManager()

    class Rating(models.TextChoices):
        THUMBS_UP = "THUMBS_UP", "Thumbs Up"
        THUMBS_DOWN = "THUMBS_DOWN", "Thumbs Down"

    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    query_log: models.ForeignKey = models.ForeignKey(
        QueryLog,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    user: models.ForeignKey = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedbacks",
    )
    rating: models.CharField = models.CharField(
        max_length=20,
        choices=Rating.choices,
    )
    comment: models.TextField = models.TextField(null=True, blank=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Feedback {self.rating} on Query {self.query_log.id}"
