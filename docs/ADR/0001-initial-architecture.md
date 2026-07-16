# ADR 0001: Initial Tech Stack and Azure Architecture

*   **Status**: Accepted
*   **Date**: 2026-07-16
*   **Authors**: DocuMind Team

## Context

We need to build "DocuMind", an enterprise-grade document ingestion and RAG search platform. The core requirements are reliability, high performance for vector queries, seamless integrations with Azure security/infra standards, robust testability, and standard developer quality gates.

We need to decide on:
1.  Backend language/framework
2.  Frontend scaffolding
3.  Vector database & search provider
4.  LLM & Embedding models provider
5.  Secrets and document storage

## Decision

We chose the following technologies and cloud services:

1.  **Backend**: **Python 3.12** + **Django 5.x** + **Django REST Framework (DRF)**.
    *   *Rationale*: Python is the industry standard for AI/LLM integration. Django provides a mature, robust administrative framework, built-in ORM, migration tooling, and excellent community support. DRF allows building clean, structured REST endpoints.
    *   *Dependency Manager*: **Poetry**. Replaces raw `pip freeze` to provide strict dependency locking, virtual environment management, and deterministic builds.
    *   *Database Adapter*: **Psycopg v3** (`psycopg`). Provides native integration with PostgreSQL 16 and superior performance over legacy psycopg2.
2.  **Frontend**: **React 18** + **TypeScript** + **Vite**.
    *   *Rationale*: React provides a modular, declarative UI ecosystem. Vite offers sub-second hot module replacement (HMR) and fast production builds. TypeScript enforces strict types for frontend API responses.
3.  **Vector Search & Database**: **Azure AI Search (Standard S1 tier)** + **PostgreSQL Flexible Server (with pgvector)**.
    *   *Rationale*: Azure AI Search supports high-performance Hybrid Search (keyword BM25 + Vector) and includes the Microsoft Semantic Ranker for re-ranking. PostgreSQL with `pgvector` will act as a secondary, metadata-rich relational database and fallback vector store.
4.  **LLM / AI Model Provider**: **Azure OpenAI** (`gpt-4o`, `text-embedding-3-large`).
    *   *Rationale*: Ensures enterprise compliance, data security, and high rate limits under Azure service level agreements (SLAs).
5.  **Storage & Secrets**: **Azure Blob Storage** (raw documents) and **Azure Key Vault** (RBAC-integrated secret management).
6.  **Infrastructure as Code (IaC)**: **Bicep**.
    *   *Rationale*: Native Azure template tooling that supports modular definitions and integrates smoothly with standard Azure CLI deployments without requiring external state management.

## Consequences

*   **Platform Dependency**: The architecture is strongly coupled with Azure Cloud Services. Deploying to other clouds (like AWS or GCP) would require updating the IaC templates and writing adapters for AI Search / OpenAI.
*   **Billing**: Running S1 Search Service and PostgreSQL Flexible Server carries immediate base hourly charges, which must be accounted for in budget planning.
*   **CI/CD Constraints**: GitHub workflows must configure Python 3.12, install poetry, and cache virtual environments to maintain fast execution loops.
