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
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Seeding Events
@app.on_event("startup")
def startup_event():
    try:
        db = SessionLocal()
        try:
            # Run compliance registry seeding on application launch
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
