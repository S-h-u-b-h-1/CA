from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.models import Client, Document, Note

def universal_search(db: Session, organization_id: str, query: str) -> dict:
    if not query:
        return {"clients": [], "documents": [], "notes": []}

    like_query = f"%{query}%"

    # 1. Search Clients
    clients = db.query(Client).filter(
        Client.organization_id == organization_id,
        Client.deleted_at.is_(None),
        or_(
            Client.client_name.ilike(like_query),
            Client.PAN.ilike(like_query),
            Client.GSTIN.ilike(like_query),
            Client.industry.ilike(like_query),
            Client.contact_person.ilike(like_query),
            Client.contact_email.ilike(like_query)
        )
    ).limit(10).all()

    # 2. Search Documents
    documents = db.query(Document).filter(
        Document.organization_id == organization_id,
        Document.deleted_at.is_(None),
        or_(
            Document.name.ilike(like_query),
            Document.category.ilike(like_query),
            Document.extracted_text.ilike(like_query)
        )
    ).limit(15).all()

    # 3. Search Notes
    notes = db.query(Note).filter(
        Note.organization_id == organization_id,
        Note.deleted_at.is_(None),
        or_(
            Note.title.ilike(like_query),
            Note.content.ilike(like_query)
        )
    ).limit(10).all()

    return {
        "clients": [
            {
                "id": c.id,
                "client_name": c.client_name,
                "client_type": c.client_type,
                "PAN": c.PAN,
                "GSTIN": c.GSTIN,
                "status": c.status
            }
            for c in clients
        ],
        "documents": [
            {
                "id": d.id,
                "name": d.name,
                "category": d.category,
                "processing_status": d.processing_status,
                "client_id": d.client_id
            }
            for d in documents
        ],
        "notes": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content[:200] + ("..." if len(n.content) > 200 else ""),
                "client_id": n.client_id,
                "created_at": n.created_at
            }
            for n in notes
        ]
    }
