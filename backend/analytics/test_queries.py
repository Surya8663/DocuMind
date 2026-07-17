import pytest
from django.core.management import call_command

from accounts.models import Tenant
from analytics.queries import (
    get_confidence_and_escalation_stats,
    get_highest_thumbs_down_users,
    get_latency_percentiles,
    get_most_queried_documents,
)


@pytest.mark.django_db
def test_analytics_queries_aggregation_success() -> None:
    """Verifies that analytics raw SQL queries extract and aggregate seeded data accurately."""
    # Seed the test database programmatically
    call_command("seed_demo_data")

    # Fetch seeded tenants
    acme = Tenant.objects.get(slug="acme")
    wayne = Tenant.objects.get(slug="wayne")

    # --------------------------------------------------------------------------
    # 1. Test get_most_queried_documents
    # --------------------------------------------------------------------------
    acme_weekly = get_most_queried_documents(acme.id)
    assert len(acme_weekly) > 0
    top_week = acme_weekly[0]
    assert "query_week" in top_week
    assert "document_id" in top_week
    assert "document_title" in top_week
    assert "query_count" in top_week
    assert top_week["query_count"] > 0

    # --------------------------------------------------------------------------
    # 2. Test get_confidence_and_escalation_stats
    # --------------------------------------------------------------------------
    acme_stats = get_confidence_and_escalation_stats(acme.id)
    assert 0.0 <= acme_stats["avg_confidence"] <= 1.0
    assert 0.0 <= acme_stats["escalation_rate"] <= 1.0
    assert acme_stats["avg_confidence"] > 0.0

    wayne_stats = get_confidence_and_escalation_stats(wayne.id)
    assert 0.0 <= wayne_stats["avg_confidence"] <= 1.0
    assert 0.0 <= wayne_stats["escalation_rate"] <= 1.0
    assert wayne_stats["avg_confidence"] > 0.0

    # --------------------------------------------------------------------------
    # 3. Test get_latency_percentiles
    # --------------------------------------------------------------------------
    acme_latencies = get_latency_percentiles(acme.id)
    assert "p50_latency" in acme_latencies
    assert "p95_latency" in acme_latencies
    assert "p99_latency" in acme_latencies
    # Verify mathematical ordering of percentiles (P50 <= P95 <= P99)
    assert (
        acme_latencies["p50_latency"]
        <= acme_latencies["p95_latency"]
        <= acme_latencies["p99_latency"]
    )
    assert acme_latencies["p50_latency"] > 0.0

    # --------------------------------------------------------------------------
    # 4. Test get_highest_thumbs_down_users
    # --------------------------------------------------------------------------
    acme_thumbs_down_users = get_highest_thumbs_down_users(acme.id)
    assert len(acme_thumbs_down_users) > 0

    # Ensure acme_member@acme.com is present and has a thumbs-down rate
    member_ratings = [
        user
        for user in acme_thumbs_down_users
        if user["user_email"] == "member@acme.com"
    ]
    assert len(member_ratings) == 1
    member_stats = member_ratings[0]
    assert member_stats["thumbs_down_rate"] >= 0.5  # Seeded to be ~80%
    assert member_stats["total_feedback"] > 0

    # Verify results are ordered by highest thumbs-down rate first
    assert (
        acme_thumbs_down_users[0]["thumbs_down_rate"]
        >= acme_thumbs_down_users[-1]["thumbs_down_rate"]
    )
