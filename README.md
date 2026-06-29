# CA Intelligence

**AI Intelligence Layer for Indian Chartered Accountants.**

CA Intelligence is a new full-stack AI Operating System designed specifically for Indian Chartered Accountants (CAs) and firm partners. It enables firms to manage clients, documents, compliance records, notices, tax research, and internal intelligence. It is architected to later integrate with the practice management system **AKKC** through API integrations.

---

## Architecture & Tech Stack

- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS, ShadCN/Radix UI UI elements.
- **Backend**: FastAPI (Python), SQLAlchemy ORM, Pydantic, Alembic migrations.
- **Database**: PostgreSQL (with `pgvector` for future AI vector embeddings), SQLite (fallback for fast dev runs).
- **Storage**: Local filesystem storage (development) with modular providers for S3 / Cloud Storage in production.
- **Security**: JWT authentication, organization-based multi-tenant isolation, role-based permission gates.

---

## Repository Structure

```text
├── backend/            # FastAPI python application
├── frontend/           # Next.js typescript web app
├── docs/               # Architecture and functional documentation
├── docker-compose.yml  # Local multi-service orchestrator
├── README.md           # This file
└── .env.example        # Environment variable templates
```

---

## Quick Start (Local Run)

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- PostgreSQL (Optional, defaults to SQLite local database file for development)

### 1. Run Backend

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy env file and adjust if necessary:
   ```bash
   cp ../.env.example .env
   ```
5. Run migrations:
   ```bash
   alembic upgrade head
   ```
6. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

The backend API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Run Frontend

1. Navigate to the `frontend/` directory:
   ```bash
   cd ../frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the Next.js dev server:
   ```bash
   npm run dev
   ```

The dashboard will be active at [http://localhost:3000](http://localhost:3000).

---

## Run with Docker Compose

To start the database, backend, and frontend together:
```bash
docker-compose up --build
```
This launches:
- PostgreSQL on port `5432`
- FastAPI backend on port `8000`
- Next.js frontend on port `3000`
