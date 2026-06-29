from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(
    title="CA Intelligence API",
    description="The AI operating system intelligence layer for Indian Chartered Accountants.",
    version="1.0.0"
)

# Configure CORS for local development and client interfaces
# Allow all in local/development but strictly narrow down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production, e.g. ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Seeding Events
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        # Run compliance registry seeding on application launch
        seed_compliance_sources(db)
    finally:
        db.close()

# Wires routers to main application path
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(org_router, prefix="/api/v1/organizations", tags=["Organizations"])
app.include_router(client_router, prefix="/api/v1/clients", tags=["Client Workspace"])
app.include_router(document_router, prefix="/api/v1/documents", tags=["Document Intelligence"])
app.include_router(compliance_router, prefix="/api/v1/compliance", tags=["Compliance Sources"])
app.include_router(search_router, prefix="/api/v1/search", tags=["Universal Search"])
app.include_router(integrations_router, prefix="/api/v1/integrations", tags=["AKKC Integrations"])

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "CA Intelligence Core API",
        "version": "1.0.0"
    }
