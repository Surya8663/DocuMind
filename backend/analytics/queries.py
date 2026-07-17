from datetime import datetime
from uuid import UUID

from django.db import connection


def get_most_queried_documents(tenant_id: str | UUID) -> list[dict]:
    """Retrieves the most-queried document per week for a specific tenant.

    Uses a CTE (Common Table Expression) and a ROW_NUMBER() window function
    to rank documents by retrieval count per week (date truncated).
    """
    query = """
        WITH WeeklyDocQueries AS (
            SELECT 
                date_trunc('week', ql.created_at) AS query_week,
                d.id AS document_id,
                d.title AS document_title,
                COUNT(DISTINCT ql.id) AS query_count
            FROM 
                accounts_querylog ql
            CROSS JOIN 
                unnest(ql.retrieved_chunk_ids) AS chunk_id
            INNER JOIN 
                accounts_documentchunk dc ON dc.id = chunk_id
            INNER JOIN 
                accounts_document d ON d.id = dc.document_id
            WHERE 
                ql.tenant_id = %s
            GROUP BY 
                query_week, d.id, d.title
        ),
        RankedWeeklyDocs AS (
            SELECT 
                query_week,
                document_id,
                document_title,
                query_count,
                ROW_NUMBER() OVER (
                    PARTITION BY query_week 
                    ORDER BY query_count DESC, document_title ASC
                ) as rank
            FROM 
                WeeklyDocQueries
        )
        SELECT 
            query_week,
            document_id,
            document_title,
            query_count
        FROM 
            RankedWeeklyDocs
        WHERE 
            rank = 1
        ORDER BY 
            query_week DESC;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [str(tenant_id)])
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # Format query_week to datetime object for consistency if needed
    for row in results:
        if isinstance(row["query_week"], str):
            row["query_week"] = datetime.fromisoformat(row["query_week"])

    return results


def get_confidence_and_escalation_stats(tenant_id: str | UUID) -> dict:
    """Calculates the average confidence score and escalation rate over the last 30 days.

    Escalation rate is the ratio of queries flagged as escalated to total queries.
    """
    query = """
        SELECT 
            COALESCE(AVG(confidence_score), 0.0) AS avg_confidence,
            COALESCE(
                SUM(CASE WHEN escalated THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0), 
                0.0
            ) AS escalation_rate
        FROM 
            accounts_querylog
        WHERE 
            tenant_id = %s
            AND created_at >= NOW() - INTERVAL '30 days';
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [str(tenant_id)])
        row = cursor.fetchone()
        if row:
            return {
                "avg_confidence": float(row[0]),
                "escalation_rate": float(row[1]),
            }
        return {"avg_confidence": 0.0, "escalation_rate": 0.0}


def get_latency_percentiles(tenant_id: str | UUID) -> dict:
    """Calculates the P50 (median), P95, and P99 latency profiles for a tenant.

    Employs PostgreSQL's native percentile_cont aggregate function.
    """
    query = """
        SELECT 
            COALESCE(percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms), 0.0) AS p50_latency,
            COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms), 0.0) AS p95_latency,
            COALESCE(percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms), 0.0) AS p99_latency
        FROM 
            accounts_querylog
        WHERE 
            tenant_id = %s;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [str(tenant_id)])
        row = cursor.fetchone()
        if row:
            return {
                "p50_latency": float(row[0]),
                "p95_latency": float(row[1]),
                "p99_latency": float(row[2]),
            }
        return {"p50_latency": 0.0, "p95_latency": 0.0, "p99_latency": 0.0}


def get_highest_thumbs_down_users(tenant_id: str | UUID) -> list[dict]:
    """Retrieves users in a tenant ranked by their thumbs-down feedback rate.

    Calculates the proportion of THUMBS_DOWN ratings out of total feedback provided.
    """
    query = """
        SELECT 
            u.id AS user_id,
            u.email AS user_email,
            COUNT(f.id) AS total_feedback,
            COALESCE(
                SUM(CASE WHEN f.rating = 'THUMBS_DOWN' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(f.id), 0), 
                0.0
            ) AS thumbs_down_rate
        FROM 
            accounts_feedback f
        INNER JOIN 
            accounts_user u ON u.id = f.user_id
        WHERE 
            u.tenant_id = %s
        GROUP BY 
            u.id, u.email
        HAVING 
            COUNT(f.id) > 0
        ORDER BY 
            thumbs_down_rate DESC, total_feedback DESC;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [str(tenant_id)])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
