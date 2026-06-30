from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Ensure local 'app' package is discoverable inside Vercel serverless environments
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.seeds import seed_compliance_sources

# Import Routers
from app.api.v1.auth import router as auth_router, org_router
from app.api.v1.clients import router as client_router
from app.api.v1.documents import router as document_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.search import router as search_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.observability import router as observability_router
from app.api.v1.citations import router as citations_router
from app.api.v1.graph import router as graph_router


app = FastAPI(
    title="CA Intelligence API",
    description="The AI operating system intelligence layer for Indian Chartered Accountants.",
    version="1.0.0"
)

# Configure CORS for local development and client interfaces
# Allow all in local/development but strictly narrow down in production
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
allow_all = "*" in origins or not origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if allow_all else origins,
    allow_origin_regex=r"https?://.*" if allow_all else r"https://.*\.vercel\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_schema_migration(db):
    from sqlalchemy import text
    columns_26as = [
        ("client_id", "VARCHAR(36)"),
        ("raw_row_text", "TEXT"),
        ("section_code", "VARCHAR(50)")
    ]
    for col_name, col_type in columns_26as:
        try:
            db.execute(text(f"ALTER TABLE form26as_entries ADD COLUMN {col_name} {col_type}"))
            db.commit()
            print(f"Schema Migration: Column '{col_name}' successfully added to 'form26as_entries'.")
        except Exception:
            db.rollback()

    columns_ais = [
        ("client_id", "VARCHAR(36)"),
        ("taxpayer_name", "VARCHAR(255)"),
        ("information_category", "VARCHAR(100)"),
        ("information_source", "VARCHAR(100)"),
        ("source_name", "VARCHAR(255)"),
        ("reported_value", "FLOAT"),
        ("processed_value", "FLOAT"),
        ("accepted_value", "FLOAT"),
        ("derived_value", "FLOAT"),
        ("transaction_type", "VARCHAR(50)"),
        ("raw_row_text", "TEXT")
    ]
    for col_name, col_type in columns_ais:
        try:
            db.execute(text(f"ALTER TABLE ais_entries ADD COLUMN {col_name} {col_type}"))
            db.commit()
            print(f"Schema Migration: Column '{col_name}' successfully added to 'ais_entries'.")
        except Exception:
            db.rollback()

# Startup Seeding Events
@app.on_event("startup")
def startup_event():
    try:
        db = SessionLocal()
        try:
            run_schema_migration(db)
            seed_compliance_sources(db)
        finally:
            db.close()
    except Exception as e:
        import sys
        print(f"Startup Warning: Database seeding was skipped. Error details: {e}", file=sys.stderr)

# Wires routers to main application path
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(org_router, prefix="/api/v1/organizations", tags=["Organizations"])
app.include_router(client_router, prefix="/api/v1/clients", tags=["Client Workspace"])
app.include_router(document_router, prefix="/api/v1/documents", tags=["Document Intelligence"])
app.include_router(compliance_router, prefix="/api/v1/compliance", tags=["Compliance Sources"])
app.include_router(search_router, prefix="/api/v1/search", tags=["Universal Search"])
app.include_router(integrations_router, prefix="/api/v1/integrations", tags=["AKKC Integrations"])
app.include_router(observability_router, prefix="/api/v1/observability", tags=["Observability"])
app.include_router(citations_router, prefix="/api/v1/citations", tags=["Citations"])
app.include_router(graph_router, prefix="/api/v1/graph", tags=["Knowledge Graph"])


@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "CA Intelligence Core API",
        "version": "1.0.0"
    }

@app.get("/api")
@app.get("/api/")
def read_api_root():
    return {
        "status": "healthy",
        "service": "CA Intelligence Core API (Monorepo API Route)",
        "version": "1.0.0"
    }
