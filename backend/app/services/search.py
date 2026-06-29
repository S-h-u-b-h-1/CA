from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.models import (
    Client, Document, Note,
    StructuredInvoiceData, StructuredNoticeData,
    KnowledgeGraphNode, KnowledgeChunk, Entity
)

def universal_search(db: Session, organization_id: str, query: str) -> dict:
    if not query:
        return {
            "clients": [], 
            "documents": [], 
            "notes": [],
            "structured_invoices": [],
            "structured_notices": [],
            "knowledge_chunks": [],
            "graph_nodes": []
        }

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

    # 4. Search Structured Invoices
    invoices = db.query(StructuredInvoiceData).filter(
        StructuredInvoiceData.organization_id == organization_id,
        or_(
            StructuredInvoiceData.vendor_name.ilike(like_query),
            StructuredInvoiceData.invoice_number.ilike(like_query),
            StructuredInvoiceData.GSTIN.ilike(like_query),
            StructuredInvoiceData.place_of_supply.ilike(like_query)
        )
    ).limit(10).all()

    # 5. Search Structured Notices
    notices = db.query(StructuredNoticeData).filter(
        StructuredNoticeData.organization_id == organization_id,
        or_(
            StructuredNoticeData.din.ilike(like_query),
            StructuredNoticeData.section.ilike(like_query),
            StructuredNoticeData.assessment_year.ilike(like_query),
            StructuredNoticeData.issuing_authority.ilike(like_query)
        )
    ).limit(10).all()

    # 6. Search Knowledge Chunks
    chunks = db.query(KnowledgeChunk).filter(
        KnowledgeChunk.organization_id == organization_id,
        KnowledgeChunk.text_content.ilike(like_query)
    ).limit(10).all()

    # 7. Search Graph Nodes
    graph_nodes = db.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.organization_id == organization_id,
        or_(
            KnowledgeGraphNode.label.ilike(like_query),
            KnowledgeGraphNode.node_type.ilike(like_query)
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
        ],
        "structured_invoices": [
            {
                "id": inv.id,
                "vendor_name": inv.vendor_name,
                "invoice_number": inv.invoice_number,
                "total_amount": inv.total_amount,
                "GSTIN": inv.GSTIN,
                "created_at": inv.created_at
            }
            for inv in invoices
        ],
        "structured_notices": [
            {
                "id": notc.id,
                "din": notc.din,
                "section": notc.section,
                "assessment_year": notc.assessment_year,
                "tax_demand_amount": notc.tax_demand_amount,
                "created_at": notc.created_at
            }
            for notc in notices
        ],
        "knowledge_chunks": [
            {
                "id": ch.id,
                "text_content": ch.text_content[:200] + ("..." if len(ch.text_content) > 200 else ""),
                "chunk_index": ch.chunk_index
            }
            for ch in chunks
        ],
        "graph_nodes": [
            {
                "id": gn.id,
                "node_type": gn.node_type,
                "label": gn.label,
                "properties": gn.properties_json
            }
            for gn in graph_nodes
        ]
    }
