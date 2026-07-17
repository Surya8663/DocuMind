import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Document, DocumentChunk, Feedback, QueryLog, Tenant, User


class Command(BaseCommand):
    """Django administrative command to seed multi-tenant analytics test data."""

    help = "Seeds PostgreSQL with realistic multi-tenant data (120+ QueryLogs, Feedback, Documents)."

    def handle(self, *args, **options) -> None:
        self.stdout.write(self.style.WARNING("Seeding demo data..."))

        # Set seed for deterministic and reproducible test data
        random.seed(42)
        now = timezone.now()

        try:
            with transaction.atomic():
                # 1. Clean existing records (excluding global superusers)
                Feedback.objects.all().delete()
                QueryLog.objects.all().delete()
                DocumentChunk.objects.all().delete()
                Document.objects.all().delete()
                User.objects.filter(is_superuser=False).delete()
                Tenant.objects.all().delete()

                # 2. Create Tenants
                acme = Tenant.objects.create(
                    name="Acme Corp",
                    slug="acme",
                    subscription_tier=Tenant.SubscriptionTier.STANDARD,
                    azure_search_index_name="documind-acme-index",
                )
                wayne = Tenant.objects.create(
                    name="Wayne Enterprises",
                    slug="wayne",
                    subscription_tier=Tenant.SubscriptionTier.ENTERPRISE,
                    azure_search_index_name="documind-wayne-index",
                )

                # 3. Create Tenant Users
                acme_admin = User.objects.create_user(
                    email="admin@acme.com",
                    full_name="Acme Administrator",
                    password="password123",
                    tenant=acme,
                    role=User.Role.ADMIN,
                )
                acme_member = User.objects.create_user(
                    email="member@acme.com",
                    full_name="Acme Member",
                    password="password123",
                    tenant=acme,
                    role=User.Role.MEMBER,
                )
                acme_viewer = User.objects.create_user(
                    email="viewer@acme.com",
                    full_name="Acme Viewer",
                    password="password123",
                    tenant=acme,
                    role=User.Role.VIEWER,
                )

                wayne_admin = User.objects.create_user(
                    email="admin@wayne.com",
                    full_name="Wayne Administrator",
                    password="password123",
                    tenant=wayne,
                    role=User.Role.ADMIN,
                )
                wayne_member = User.objects.create_user(
                    email="member@wayne.com",
                    full_name="Wayne Member",
                    password="password123",
                    tenant=wayne,
                    role=User.Role.MEMBER,
                )

                # 4. Create Documents and Chunks
                acme_titles = [
                    ("HR Policy 2026", Document.DocType.POLICY, "hr_policy_2026.pdf"),
                    (
                        "Vendor NDA Template",
                        Document.DocType.CONTRACT,
                        "vendor_nda.docx",
                    ),
                    ("Q1 Financial Report", Document.DocType.REPORT, "q1_finance.pdf"),
                    ("IT Security Guide", Document.DocType.POLICY, "it_security.txt"),
                    (
                        "Office Lease Contract",
                        Document.DocType.CONTRACT,
                        "office_lease.pdf",
                    ),
                ]

                wayne_titles = [
                    ("Batcave Schematics", Document.DocType.REPORT, "batcave_v2.pdf"),
                    (
                        "Applied Sciences Budget",
                        Document.DocType.REPORT,
                        "applied_sciences.pdf",
                    ),
                    (
                        "Clean Energy Charter",
                        Document.DocType.POLICY,
                        "clean_energy.txt",
                    ),
                    (
                        "Satellite Comm Specs",
                        Document.DocType.REPORT,
                        "satellite_comm.pdf",
                    ),
                    (
                        "R&D Supplier Agreement",
                        Document.DocType.CONTRACT,
                        "supplier_agreement.docx",
                    ),
                ]

                acme_docs = []
                acme_chunks = []
                for i, (title, doc_type, filename) in enumerate(acme_titles):
                    doc = Document.objects.create(
                        tenant=acme,
                        uploaded_by=acme_admin,
                        title=title,
                        file_type=(
                            Document.FileType.PDF
                            if filename.endswith(".pdf")
                            else Document.FileType.TXT
                        ),
                        blob_storage_path=f"acme/raw/{filename}",
                        doc_type=doc_type,
                        status=Document.Status.INDEXED,
                        page_count=random.randint(5, 50),
                        checksum=f"checksum-acme-{i}",
                    )
                    acme_docs.append(doc)
                    # Add 3 chunks per document
                    for j in range(3):
                        chunk = DocumentChunk.objects.create(
                            document=doc,
                            tenant=acme,
                            chunk_index=j,
                            content=f"Content chunk {j} of document {title} mapping text database.",
                            token_count=random.randint(100, 250),
                            azure_search_doc_id=f"acme-chunk-{doc.id}-{j}",
                            embedding_model="text-embedding-3-large",
                        )
                        acme_chunks.append(chunk)

                wayne_docs = []
                wayne_chunks = []
                for i, (title, doc_type, filename) in enumerate(wayne_titles):
                    doc = Document.objects.create(
                        tenant=wayne,
                        uploaded_by=wayne_admin,
                        title=title,
                        file_type=(
                            Document.FileType.PDF
                            if filename.endswith(".pdf")
                            else Document.FileType.TXT
                        ),
                        blob_storage_path=f"wayne/raw/{filename}",
                        doc_type=doc_type,
                        status=Document.Status.INDEXED,
                        page_count=random.randint(10, 100),
                        checksum=f"checksum-wayne-{i}",
                    )
                    wayne_docs.append(doc)
                    # Add 3 chunks per document
                    for j in range(3):
                        chunk = DocumentChunk.objects.create(
                            document=doc,
                            tenant=wayne,
                            chunk_index=j,
                            content=f"Content chunk {j} of document {title} referencing Wayne systems.",
                            token_count=random.randint(150, 300),
                            azure_search_doc_id=f"wayne-chunk-{doc.id}-{j}",
                            embedding_model="text-embedding-3-large",
                        )
                        wayne_chunks.append(chunk)

                # 5. Create QueryLogs (80 for Acme, 45 for Wayne)
                acme_logs = []
                for k in range(80):
                    # Dates spanning last 40 days
                    days_ago = random.randint(0, 40)
                    log_date = now - timedelta(
                        days=days_ago, hours=random.randint(0, 23)
                    )

                    # Retrieve 1 to 3 random chunks from Acme
                    retrieved_chunks = random.sample(acme_chunks, random.randint(1, 3))
                    chunk_uuids = [c.id for c in retrieved_chunks]

                    # Assign user
                    user = random.choice([acme_admin, acme_member, acme_viewer])

                    # Calculate latency breakdown
                    az_lat = random.randint(20, 150)
                    llm_lat = random.randint(300, 1800)
                    tot_lat = az_lat + llm_lat + random.randint(10, 50)

                    log = QueryLog.objects.create(
                        tenant=acme,
                        user=user,
                        query_text=f"Query request {k} relating to corporate guidelines?",
                        retrieved_chunk_ids=chunk_uuids,
                        answer_text=f"Generated answer {k} based on document chunks.",
                        confidence_score=random.uniform(0.45, 0.98),
                        escalated=random.choice(
                            [True, False, False, False, False]
                        ),  # 20% escalation
                        latency_ms=tot_lat,
                        azure_search_latency_ms=az_lat,
                        llm_latency_ms=llm_lat,
                    )
                    # Override auto_now_add for backdated query logs
                    QueryLog.objects.filter(id=log.id).update(created_at=log_date)
                    log.created_at = log_date
                    acme_logs.append(log)

                wayne_logs = []
                for k in range(45):
                    days_ago = random.randint(0, 40)
                    log_date = now - timedelta(
                        days=days_ago, hours=random.randint(0, 23)
                    )

                    # Retrieve chunks from Wayne
                    retrieved_chunks = random.sample(wayne_chunks, random.randint(1, 3))
                    chunk_uuids = [c.id for c in retrieved_chunks]

                    user = random.choice([wayne_admin, wayne_member])

                    az_lat = random.randint(30, 200)
                    llm_lat = random.randint(400, 2500)
                    tot_lat = az_lat + llm_lat + random.randint(10, 80)

                    log = QueryLog.objects.create(
                        tenant=wayne,
                        user=user,
                        query_text=f"Query request {k} on applied engineering?",
                        retrieved_chunk_ids=chunk_uuids,
                        answer_text=f"Generated answer {k} matching Wayne systems context.",
                        confidence_score=random.uniform(0.55, 0.99),
                        escalated=random.choice(
                            [True, False, False, False]
                        ),  # ~25% escalation
                        latency_ms=tot_lat,
                        azure_search_latency_ms=az_lat,
                        llm_latency_ms=llm_lat,
                    )
                    QueryLog.objects.filter(id=log.id).update(created_at=log_date)
                    log.created_at = log_date
                    wayne_logs.append(log)

                # 6. Create Feedback
                # Acme feedback
                for log in acme_logs:
                    if random.choice([True, False]):  # 50% chance of feedback
                        # Determine user and specific rating profile
                        user = log.user
                        rating = Feedback.Rating.THUMBS_UP

                        # If user is acme_member, force high thumbs down rate (80% thumbs down)
                        if user == acme_member:
                            rating = (
                                Feedback.Rating.THUMBS_DOWN
                                if random.random() < 0.8
                                else Feedback.Rating.THUMBS_UP
                            )
                        else:
                            # General user rating profile (75% thumbs up)
                            rating = (
                                Feedback.Rating.THUMBS_UP
                                if random.random() < 0.75
                                else Feedback.Rating.THUMBS_DOWN
                            )

                        Feedback.objects.create(
                            query_log=log,
                            user=user,
                            rating=rating,
                            comment=(
                                "Excellent response!"
                                if rating == Feedback.Rating.THUMBS_UP
                                else "Incorrect document context retrieved."
                            ),
                        )

                # Wayne feedback
                for log in wayne_logs:
                    if random.choice([True, False, False]):  # 33% feedback
                        user = log.user
                        rating = (
                            Feedback.Rating.THUMBS_UP
                            if random.random() < 0.85
                            else Feedback.Rating.THUMBS_DOWN
                        )
                        Feedback.objects.create(
                            query_log=log,
                            user=user,
                            rating=rating,
                            comment="Standard operational rating.",
                        )

            self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during seeding: {str(e)}"))
