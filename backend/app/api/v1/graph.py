from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.core.database import get_db
from app.models.models import User, KnowledgeGraphNode, KnowledgeGraphEdge, Entity, EntityAlias
from app.api.deps import get_current_user
from app.services.graph import GraphService
from pydantic import BaseModel

router = APIRouter()

# Schema models
class MergePayload(BaseModel):
    primary_entity_id: str
    secondary_entity_id: str

class AliasPayload(BaseModel):
    entity_id: str
    alias_text: str
    alias_type: str
    confidence_score: Optional[float] = 1.0

@router.get("/nodes")
def list_nodes(
    node_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.organization_id == current_user.organization_id,
        KnowledgeGraphNode.status == "ACTIVE"
    )
    if node_type:
        query = query.filter(KnowledgeGraphNode.node_type == node_type)
    return query.all()

@router.get("/edges")
def list_edges(
    relationship: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(KnowledgeGraphEdge).filter(
        KnowledgeGraphEdge.organization_id == current_user.organization_id,
        KnowledgeGraphEdge.status == "ACTIVE"
    )
    if relationship:
        query = query.filter(KnowledgeGraphEdge.relationship == relationship)
    return query.all()

@router.get("/entity/{entity_id}")
def get_entity_details(
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    entity = db.query(Entity).filter(
        Entity.id == entity_id,
        Entity.organization_id == current_user.organization_id
    ).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
        
    aliases = db.query(EntityAlias).filter(
        EntityAlias.entity_id == entity_id,
        EntityAlias.organization_id == current_user.organization_id
    ).all()
    
    return {
        "entity": entity,
        "aliases": aliases
    }

@router.get("/client/{client_id}")
def get_client_graph(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Fetch Client Node
    client_node = db.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.organization_id == current_user.organization_id,
        KnowledgeGraphNode.node_type == "Client",
        KnowledgeGraphNode.properties_json["client_id"].as_string() == client_id,
        KnowledgeGraphNode.status == "ACTIVE"
    ).first()

    if not client_node:
        return {"nodes": [], "edges": []}

    # Fetch all connected edges and target nodes
    edges = db.query(KnowledgeGraphEdge).filter(
        KnowledgeGraphEdge.organization_id == current_user.organization_id,
        KnowledgeGraphEdge.source_node_id == client_node.id,
        KnowledgeGraphEdge.status == "ACTIVE"
    ).all()

    target_node_ids = [e.target_node_id for e in edges]
    nodes = db.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.organization_id == current_user.organization_id,
        KnowledgeGraphNode.id.in_([client_node.id] + target_node_ids),
        KnowledgeGraphNode.status == "ACTIVE"
    ).all()

    return {
        "nodes": nodes,
        "edges": edges
    }

@router.get("/document/{document_id}")
def get_document_graph(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Fetch Document Node
    doc_node = db.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.organization_id == current_user.organization_id,
        KnowledgeGraphNode.node_type == "DOCUMENT",
        KnowledgeGraphNode.properties_json["document_id"].as_string() == document_id,
        KnowledgeGraphNode.status == "ACTIVE"
    ).first()

    if not doc_node:
        return {"nodes": [], "edges": []}

    # Fetch all connected edges (either source or target)
    edges = db.query(KnowledgeGraphEdge).filter(
        KnowledgeGraphEdge.organization_id == current_user.organization_id,
        KnowledgeGraphEdge.status == "ACTIVE",
        (KnowledgeGraphEdge.source_node_id == doc_node.id) | (KnowledgeGraphEdge.target_node_id == doc_node.id)
    ).all()

    node_ids = set([doc_node.id])
    for e in edges:
        node_ids.add(e.source_node_id)
        node_ids.add(e.target_node_id)

    nodes = db.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.organization_id == current_user.organization_id,
        KnowledgeGraphNode.id.in_(list(node_ids)),
        KnowledgeGraphNode.status == "ACTIVE"
    ).all()

    return {
        "nodes": nodes,
        "edges": edges
    }

@router.post("/build/document/{document_id}")
def build_document_graph_endpoint(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Trigger synchronous run for immediate testing, or background task
    try:
        success = GraphService.build_graph_for_document(db, current_user.organization_id, document_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to build document graph. Ensure document is processed.")
        return {"status": "SUCCESS", "message": "Graph rebuilt successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/build/government/{government_update_id}")
def build_government_graph_endpoint(
    government_update_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        success = GraphService.build_graph_for_government_update(db, government_update_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to build government update graph.")
        return {"status": "SUCCESS", "message": "Government update graph built successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/entities/merge")
def merge_entities_endpoint(
    payload: MergePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = GraphService.merge_entities(
        db=db,
        organization_id=current_user.organization_id,
        primary_id=payload.primary_entity_id,
        secondary_id=payload.secondary_entity_id,
        user_email=current_user.email
    )
    if not success:
        raise HTTPException(status_code=400, detail="Merge failed. Validate entity IDs.")
    return {"status": "SUCCESS", "message": "Entities merged successfully."}

@router.post("/entities/alias")
def create_entity_alias_endpoint(
    payload: AliasPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    entity = db.query(Entity).filter(
        Entity.id == payload.entity_id,
        Entity.organization_id == current_user.organization_id
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Primary entity not found")

    alias = EntityAlias(
        organization_id=current_user.organization_id,
        entity_id=payload.entity_id,
        alias_text=payload.alias_text.strip(),
        alias_type=payload.alias_type,
        confidence_score=payload.confidence_score,
        created_by=current_user.email
    )
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias

@router.get("/search")
def search_graph_endpoint(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    like_query = f"%{q}%"
    nodes = db.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.organization_id == current_user.organization_id,
        KnowledgeGraphNode.status == "ACTIVE",
        KnowledgeGraphNode.label.ilike(like_query)
    ).limit(20).all()
    return nodes
