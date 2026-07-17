from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Document, DocumentChunk, Feedback, QueryLog, Tenant, User


class UserChangeForm(forms.ModelForm):
    """Form to edit users in the Django Admin panel."""

    class Meta:
        model = User
        fields = "__all__"


class UserCreationForm(forms.ModelForm):
    """Form to create users in the Django Admin panel (handles password hashing)."""

    class Meta:
        model = User
        fields = ("email", "full_name", "password")

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Administrative panel config for Tenant model."""

    list_display = (
        "name",
        "slug",
        "subscription_tier",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "slug")
    list_filter = ("subscription_tier", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Administrative panel config for custom User model."""

    form = UserChangeForm
    add_form = UserCreationForm

    list_display = (
        "email",
        "full_name",
        "role",
        "tenant",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "is_active", "is_staff", "tenant")
    search_fields = ("email", "full_name")
    ordering = ("email",)

    # Fields to show when editing user details
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("full_name",)}),
        (
            "Permissions & Roles",
            {
                "fields": (
                    "role",
                    "tenant",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )

    # Fields to show when creating a user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password"),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin configuration for Document model."""

    list_display = (
        "title",
        "file_type",
        "doc_type",
        "tenant",
        "status",
        "uploaded_at",
        "page_count",
    )
    list_filter = ("file_type", "doc_type", "status", "tenant")
    search_fields = ("title", "checksum")
    ordering = ("-uploaded_at",)


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    """Admin configuration for DocumentChunk model."""

    list_display = (
        "document",
        "chunk_index",
        "token_count",
        "tenant",
        "created_at",
    )
    list_filter = ("tenant", "embedding_model")
    search_fields = ("content", "azure_search_doc_id")
    ordering = ("document", "chunk_index")


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    """Admin configuration for QueryLog model."""

    list_display = (
        "query_text",
        "user",
        "tenant",
        "confidence_score",
        "escalated",
        "latency_ms",
        "created_at",
    )
    list_filter = ("escalated", "tenant", "created_at")
    search_fields = ("query_text", "answer_text")
    ordering = ("-created_at",)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """Admin configuration for Feedback model."""

    list_display = ("query_log", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("comment",)
    ordering = ("-created_at",)
