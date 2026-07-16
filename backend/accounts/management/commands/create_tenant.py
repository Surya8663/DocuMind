from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Tenant, User


class Command(BaseCommand):
    """Django administrative command to bootstrap a new Tenant and its initial Admin user."""

    help = "Bootstraps a new Tenant and its initial Administrator user."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--name",
            type=str,
            required=True,
            help="Name of the tenant organization.",
        )
        parser.add_argument(
            "--slug",
            type=str,
            required=True,
            help="Unique URL slug identifier for the tenant.",
        )
        parser.add_argument(
            "--tier",
            type=str,
            default="TRIAL",
            choices=["TRIAL", "STANDARD", "ENTERPRISE"],
            help="Subscription tier of the tenant (TRIAL/STANDARD/ENTERPRISE).",
        )
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Login email address of the initial administrator user.",
        )
        parser.add_argument(
            "--full-name",
            type=str,
            required=True,
            help="Full name of the initial administrator user.",
        )
        parser.add_argument(
            "--password",
            type=str,
            required=True,
            help="Password for the initial administrator user.",
        )

    def handle(self, *args, **options) -> None:
        name = options["name"]
        slug = options["slug"].lower().strip()
        tier = options["tier"].upper()
        email = options["email"].lower().strip()
        full_name = options["full_name"].strip()
        password = options["password"]

        # Validate that the tenant slug is unique
        if Tenant.objects.filter(slug=slug).exists():
            raise CommandError(f"A tenant with slug '{slug}' already exists.")

        # Validate that the admin email is unique
        if User.objects.filter(email=email).exists():
            raise CommandError(f"A user with email '{email}' already exists.")

        self.stdout.write(
            self.style.WARNING(
                f"Bootstrapping tenant '{name}' and administrator '{email}'..."
            )
        )

        try:
            with transaction.atomic():
                # Define standard naming convention for tenant Azure AI Search indexes
                azure_search_index_name = f"documind-{slug}-index"

                tenant = Tenant.objects.create(
                    name=name,
                    slug=slug,
                    subscription_tier=tier,
                    azure_search_index_name=azure_search_index_name,
                    is_active=True,
                )

                admin_user = User.objects.create_user(
                    email=email,
                    full_name=full_name,
                    password=password,
                    tenant=tenant,
                    role=User.Role.ADMIN,
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created Tenant '{tenant.name}' (ID: {tenant.id}) with index '{tenant.azure_search_index_name}'."
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created admin User '{admin_user.email}' linked to Tenant."
                )
            )

        except Exception as e:
            raise CommandError(f"An error occurred during tenant creation: {str(e)}")
