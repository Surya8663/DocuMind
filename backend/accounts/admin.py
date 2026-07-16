from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Tenant, User


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
