from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.core.database import get_db
from app.models.models import User, ResearchSource, ResearchQuery, ResearchResult, ResearchBookmark, ResearchNote
from app.schemas.research import (
    ResearchSourceResponse, ResearchQueryRequest, ResearchResultResponse,
    ResearchNoteRequest, ResearchNoteResponse, ResearchBookmarkRequest,
    ResearchBookmarkResponse, ResearchHistoryResponse
)
from app.api.deps import get_current_user
from app.services.research import ResearchService

router = APIRouter()

@router.post("/query", response_model=ResearchResultResponse)
def execute_research_query(
    payload: ResearchQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = ResearchService.generate_answer(
            db=db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            query_text=payload.query_text,
            client_id=payload.client_id,
            assessment_year=payload.assessment_year or "2025-26",
            filters=payload.filters
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during query execution: {str(e)}"
        )

@router.get("/history", response_model=List[ResearchHistoryResponse])
def get_research_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    queries = db.query(ResearchQuery).filter(
        ResearchQuery.organization_id == current_user.organization_id
    ).order_by(ResearchQuery.created_at.desc()).limit(50).all()
    
    history = []
    for q in queries:
        result_record = db.query(ResearchResult).filter(
            ResearchResult.query_id == q.id
        ).first()
        
        result_payload = None
        if result_record:
            result_payload = {
                "id": result_record.id,
                "summary": result_record.summary,
                "applicable_law": result_record.applicable_law,
                "relevant_sections": result_record.relevant_sections,
                "relevant_circulars": result_record.relevant_circulars,
                "relevant_notifications": result_record.relevant_notifications,
                "considerations": result_record.considerations,
                "risks": result_record.risks,
                "confidence": result_record.confidence,
                "references": result_record.references_json or [],
                "created_at": result_record.created_at
            }

        history.append({
            "id": q.id,
            "query_text": q.query_text,
            "created_at": q.created_at,
            "result": result_payload
        })
    return history

@router.get("/sources", response_model=List[ResearchSourceResponse])
def get_research_sources(
    authority: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ResearchSource).filter(ResearchSource.status == "ACTIVE")
    if authority:
        query = query.filter(ResearchSource.authority == authority)
    if category:
        query = query.filter(ResearchSource.category == category)
    return query.all()

@router.post("/note", response_model=ResearchNoteResponse)
def create_research_note(
    payload: ResearchNoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        note = ResearchNote(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            client_id=payload.client_id,
            assessment_year=payload.assessment_year,
            document_id=payload.document_id,
            title=payload.title,
            content=payload.content,
            section_reference=payload.section_reference,
            authority_reference=payload.authority_reference,
            tags=payload.tags,
            is_pinned=payload.is_pinned or False
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating note: {str(e)}"
        )

@router.get("/note/{id}", response_model=ResearchNoteResponse)
def get_research_note(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(ResearchNote).filter(
        ResearchNote.id == id,
        ResearchNote.organization_id == current_user.organization_id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Research note not found")
    return note

@router.put("/note/{id}", response_model=ResearchNoteResponse)
def update_research_note(
    id: str,
    payload: ResearchNoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(ResearchNote).filter(
        ResearchNote.id == id,
        ResearchNote.organization_id == current_user.organization_id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Research note not found")
    
    note.client_id = payload.client_id
    note.assessment_year = payload.assessment_year
    note.document_id = payload.document_id
    note.title = payload.title
    note.content = payload.content
    note.section_reference = payload.section_reference
    note.authority_reference = payload.authority_reference
    note.tags = payload.tags
    if payload.is_pinned is not None:
        note.is_pinned = payload.is_pinned

    db.commit()
    db.refresh(note)
    return note

@router.delete("/note/{id}")
def delete_research_note(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(ResearchNote).filter(
        ResearchNote.id == id,
        ResearchNote.organization_id == current_user.organization_id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Research note not found")
    db.delete(note)
    db.commit()
    return {"message": "Research note deleted successfully"}

@router.post("/bookmark", response_model=ResearchBookmarkResponse)
def create_research_bookmark(
    payload: ResearchBookmarkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    source = db.query(ResearchSource).filter(ResearchSource.id == payload.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source authority not found")
    
    # Check if duplicate
    existing = db.query(ResearchBookmark).filter(
        ResearchBookmark.organization_id == current_user.organization_id,
        ResearchBookmark.source_id == payload.source_id
    ).first()
    if existing:
        return {
            "id": existing.id,
            "source_id": existing.source_id,
            "notes": existing.notes,
            "created_at": existing.created_at,
            "source": source
        }
        
    bookmark = ResearchBookmark(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        source_id=payload.source_id,
        notes=payload.notes
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    
    return {
        "id": bookmark.id,
        "source_id": bookmark.source_id,
        "notes": bookmark.notes,
        "created_at": bookmark.created_at,
        "source": source
    }

@router.get("/bookmarks", response_model=List[ResearchBookmarkResponse])
def get_research_bookmarks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bookmarks = db.query(ResearchBookmark).filter(
        ResearchBookmark.organization_id == current_user.organization_id
    ).all()
    
    res = []
    for b in bookmarks:
        src = db.query(ResearchSource).filter(ResearchSource.id == b.source_id).first()
        if src:
            res.append({
                "id": b.id,
                "source_id": b.source_id,
                "notes": b.notes,
                "created_at": b.created_at,
                "source": src
            })
    return res

@router.delete("/bookmark/{id}")
def delete_research_bookmark(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bookmark = db.query(ResearchBookmark).filter(
        ResearchBookmark.id == id,
        ResearchBookmark.organization_id == current_user.organization_id
    ).first()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    db.delete(bookmark)
    db.commit()
    return {"message": "Bookmark removed successfully"}
