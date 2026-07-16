# DocuMind Architecture Overview

DocuMind is an enterprise-grade document ingestion and Retrieval-Augmented Generation (RAG) platform. It allows users to upload documents, run multi-modal parsing, build search indexes with dense/sparse vectors, and perform interactive Q&A grounded in their document corpora.

## System Architecture

```mermaid
graph TB
    subgraph Frontend (React/Vite/TS)
        UI[React UI Client]
    end

    subgraph Backend (Django REST Framework)
        API[Django API Endpoint]
        Ingest[Document Ingestion pipeline]
        RAG[RAG Coordinator]
    end

    subgraph Azure Cloud Resources
        DB[(Azure Database for PostgreSQL)]
        Storage[(Azure Blob Storage)]
        Search[Azure AI Search Index]
        OpenAI[Azure OpenAI Service]
        KV[Azure Key Vault]
    end

    UI -->|HTTPS / JSON| API
    API -->|Read/Write Metadata| DB
    API -->|Upload raw files| Storage
    Ingest -->|Retrieve files| Storage
    Ingest -->|Generate Embeddings| OpenAI
    Ingest -->|Upsert Chunks & Vectors| Search
    RAG -->|Semantic Query Hybrid Search| Search
    RAG -->|Generate Grounded Response| OpenAI
    API -->|Retrieve Secrets| KV
```

## Component Breakdown

### 1. Frontend Client
*   **Technology**: React 18, TypeScript, Vite.
*   **Role**: Provides the dashboard for document uploads, processing tracking, and an interactive chat interface for running questions against the documents.

### 2. Backend API & Workers
*   **Technology**: Django 5.x, Django REST Framework, Poetry.
*   **Role**: Handles authentication, user document management, orchestrates ingestion jobs, and implements the RAG pipeline logic.
*   **Psycopg v3**: Interfaces with PostgreSQL database using the latest psycopg driver for optimized connection handling.

### 3. Azure Services Integrations
*   **Azure Database for PostgreSQL (Flexible Server)**: Stores tenant information, document metadata, processing status, and session/conversation logs.
*   **Azure Blob Storage**: Stores the raw uploaded PDF, Word, and Excel documents.
*   **Azure AI Search**: Acts as the vector database and search engine. Employs Hybrid search combining BM25 keyword matching with dense embeddings (`text-embedding-3-large`), and applies Azure's native Semantic Ranker.
*   **Azure OpenAI**: 
    *   `text-embedding-3-large` (3072-dimension vectors) for indexing and query embedding.
    *   `gpt-4o` for synthesizing the final generated answers based strictly on the retrieved context chunks.
*   **Azure Key Vault**: Stores app secrets (API keys, connection strings) securely.
