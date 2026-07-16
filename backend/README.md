# DocuMind Backend

This is the Django backend service for DocuMind. It provides the REST API endpoints, coordinates Document ingestion, interacts with Azure AI Search, and performs Retrieval-Augmented Generation (RAG) using Azure OpenAI models.

## Local Setup

1. Make sure Python 3.12 is installed.
2. Install Poetry if not already installed:
   ```bash
   python -m pip install poetry
   ```
3. Install dependencies:
   ```bash
   poetry install
   ```
4. Copy `.env.example` from the repository root to `backend/.env` (or let it read the one at the root) and fill in the values.
5. Activate virtual environment:
   ```bash
   poetry shell
   ```
6. Run migrations (once Django applications are created):
   ```bash
   python manage.py migrate
   ```
7. Run the development server:
   ```bash
   python manage.py runserver
   ```
