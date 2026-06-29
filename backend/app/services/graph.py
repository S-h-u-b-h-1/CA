import re
import json
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models.models import (
    Entity, EntityRelationship, EntityAlias,
    KnowledgeGraphNode, KnowledgeGraphEdge, RawDocument, GovernmentUpdate, Citation
)
from app.services.extractor import LegalReferenceExtractor

def normalize_entity_name(name: str) -> str:
    """
    Normalizes company/person names by removing punctuation, spaces, and corporate suffixes.
    e.g. "A K Kataruka & Co" -> "akkataruka"
    """
    if not name:
        return ""
    # Lowercase
    n = name.lower().strip()
    # Remove corporate suffixes
    n = re.sub(r"\b(pvt|private|ltd|limited|co|company|corp|corporation|inc|and company|& co|& company)\b", "", n)
    # Remove non-alphanumeric characters
    n = re.sub(r"[^a-z0-9]", "", n)
    return n.strip()

class GraphService:
    @staticmethod
    def resolve_entity(db: Session, organization_id: str, entity_type: str, value: str) -> Entity:
        """
        Deduplicates and resolves entities. If a matching alias or normalized entity name
        exists, it maps to the resolved primary entity and creates an alias entry.
        """
        val_clean = value.strip()
        
        # 1. Exact Match
        exact_entity = db.query(Entity).filter(
            Entity.organization_id == organization_id,
            Entity.entity_type == entity_type,
            Entity.value == val_clean,
            Entity.status == "ACTIVE"
        ).first()
        
        if exact_entity:
            return exact_entity

        # 2. Check Entity Alias Table
        alias_entry = db.query(EntityAlias).filter(
            EntityAlias.organization_id == organization_id,
            EntityAlias.alias_text == val_clean,
            EntityAlias.alias_type == entity_type
        ).first()

        if alias_entry:
            primary = db.query(Entity).filter(
                Entity.id == alias_entry.entity_id,
                Entity.status == "ACTIVE"
            ).first()
            if primary:
                return primary

        # 3. For Named Entities, perform Normalized Match
        if entity_type in ["Name", "Company", "Person", "ORGANIZATION", "CLIENT"]:
            norm_val = normalize_entity_name(val_clean)
            
            # Retrieve all active name entities
            all_name_entities = db.query(Entity).filter(
                Entity.organization_id == organization_id,
                Entity.entity_type == entity_type,
                Entity.status == "ACTIVE"
            ).all()

            for ent in all_name_entities:
                if normalize_entity_name(ent.value) == norm_val:
                    # Link as alias
                    alias = EntityAlias(
                        organization_id=organization_id,
                        entity_id=ent.id,
                        alias_text=val_clean,
                        alias_type=entity_type,
                        confidence_score=0.9,
                        created_by="SYSTEM"
                    )
                    db.add(alias)
                    db.commit()
                    return ent

        # 4. Fallback: Create new primary entity
        new_ent = Entity(
            organization_id=organization_id,
            entity_type=entity_type,
            value=val_clean,
            metadata_json={"resolved_at": datetime.utcnow().isoformat()}
        )
        db.add(new_ent)
        db.commit()
        db.refresh(new_ent)
        
        # Self-index in alias table
        alias = EntityAlias(
            organization_id=organization_id,
            entity_id=new_ent.id,
            alias_text=val_clean,
            alias_type=entity_type,
            confidence_score=1.0,
            created_by="SYSTEM"
        )
        db.add(alias)
        db.commit()
        
        return new_ent

    @staticmethod
    def merge_entities(db: Session, organization_id: str, primary_id: str, secondary_id: str, user_email: str = "SYSTEM") -> bool:
        """
        Merges two entity nodes. Rewires all references and logs the alias.
        """
        primary = db.query(Entity).filter(Entity.id == primary_id, Entity.organization_id == organization_id).first()
        secondary = db.query(Entity).filter(Entity.id == secondary_id, Entity.organization_id == organization_id).first()
        
        if not primary or not secondary:
            return False

        # Rewrite entity relationships
        db.query(EntityRelationship).filter(
            EntityRelationship.source_entity_id == secondary_id
        ).update({EntityRelationship.source_entity_id: primary_id})

        db.query(EntityRelationship).filter(
            EntityRelationship.target_entity_id == secondary_id
        ).update({EntityRelationship.target_entity_id: primary_id})

        # Rewrite citations
        db.query(Citation).filter(
            Citation.target_entity_id == secondary_id
        ).update({Citation.target_entity_id: primary_id})

        # Rewrite existing aliases of secondary to point to primary
        db.query(EntityAlias).filter(
            EntityAlias.entity_id == secondary_id,
            EntityAlias.organization_id == organization_id
        ).update({EntityAlias.entity_id: primary_id})

        # Create Alias mapping if not already exists
        existing_alias = db.query(EntityAlias).filter(
            EntityAlias.organization_id == organization_id,
            EntityAlias.entity_id == primary_id,
            EntityAlias.alias_text == secondary.value
        ).first()
        if not existing_alias:
            alias = EntityAlias(
                organization_id=organization_id,
                entity_id=primary_id,
                alias_text=secondary.value,
                alias_type=secondary.entity_type,
                confidence_score=1.0,
                created_by=user_email
            )
            db.add(alias)

        # Deactivate secondary entity
        secondary.status = "MERGED"
        secondary.metadata_json = {
            **(secondary.metadata_json or {}),
            "merged_into": primary_id,
            "merged_at": datetime.utcnow().isoformat(),
            "merged_by": user_email
        }
        
        db.commit()
        return True

    @staticmethod
    def add_node(db: Session, organization_id: str, node_type: str, label: str, properties: Dict[str, Any] = None) -> KnowledgeGraphNode:
        """
        Helper to add or get a node in the Knowledge Graph.
        """
        node = db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.organization_id == organization_id,
            KnowledgeGraphNode.node_type == node_type,
            KnowledgeGraphNode.label == label
        ).first()

        if not node:
            node = KnowledgeGraphNode(
                organization_id=organization_id,
                node_type=node_type,
                label=label,
                properties_json=properties or {}
            )
            db.add(node)
            db.commit()
            db.refresh(node)
        else:
            if properties:
                node.properties_json = {**(node.properties_json or {}), **properties}
                db.commit()
        return node

    @staticmethod
    def add_edge(db: Session, organization_id: str, source_node_id: str, target_node_id: str, relationship: str, properties: Dict[str, Any] = None) -> KnowledgeGraphEdge:
        """
        Helper to add an edge in the Knowledge Graph.
        """
        edge = db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.organization_id == organization_id,
            KnowledgeGraphEdge.source_node_id == source_node_id,
            KnowledgeGraphEdge.target_node_id == target_node_id,
            KnowledgeGraphEdge.relationship == relationship
        ).first()

        if not edge:
            edge = KnowledgeGraphEdge(
                organization_id=organization_id,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                relationship=relationship,
                properties_json=properties or {}
            )
            db.add(edge)
            db.commit()
            db.refresh(edge)
        else:
            if properties:
                edge.properties_json = {**(edge.properties_json or {}), **properties}
                db.commit()
        return edge

    @staticmethod
    def build_graph_for_document(db: Session, organization_id: str, doc_id: str) -> bool:
        """
        Walks text content of a RawDocument, extracts entities, acts, rules, and sets up
        nodes and edges in the Knowledge Graph.
        """
        doc = db.query(RawDocument).filter(RawDocument.id == doc_id, RawDocument.organization_id == organization_id).first()
        if not doc:
            return False

        # Get OCR extracted text
        from app.models.models import ProcessedDocument
        proc_doc = db.query(ProcessedDocument).filter(ProcessedDocument.raw_document_id == doc_id).first()
        text = proc_doc.ocr_text if proc_doc else ""
        if not text:
            return False

        # Extract refs
        extracted = LegalReferenceExtractor.extract_all(text)

        # 1. Create Document Node
        doc_node = GraphService.add_node(
            db, organization_id, "DOCUMENT", doc.name,
            {"document_id": doc_id, "mime_type": doc.mime_type, "uploaded_at": doc.created_at.isoformat() if doc.created_at else None}
        )

        # 2. Link Client Node if client_id is available
        if doc.client_id:
            from app.models.models import Client
            client = db.query(Client).filter(Client.id == doc.client_id).first()
            client_name = client.client_name if client else f"Client_{doc.client_id[:8]}"
            client_node = GraphService.add_node(
                db, organization_id, "CLIENT", client_name,
                {"client_id": doc.client_id, "PAN": client.PAN if client else None, "GSTIN": client.GSTIN if client else None}
            )
            GraphService.add_edge(db, organization_id, client_node.id, doc_node.id, "FILED_FOR")

        # 3. Create and Link Entity Nodes
        for etype in ["PAN", "GSTIN", "CIN", "DIN", "TAN"]:
            for val in extracted.get(etype, []):
                # Resolve primary entity
                ent = GraphService.resolve_entity(db, organization_id, etype, val)
                
                # Add node
                node = GraphService.add_node(db, organization_id, etype, val, {"entity_id": ent.id})
                GraphService.add_edge(db, organization_id, doc_node.id, node.id, "EXTRACTED_FROM")

        # 4. Create and Link Legal Reference Nodes
        for sec in extracted.get("SECTION", []):
            node = GraphService.add_node(db, organization_id, "SECTION", sec, {"act": "Income Tax Act" if "income tax" in text.lower() else "CGST Act"})
            GraphService.add_edge(db, organization_id, doc_node.id, node.id, "REFERENCES")

        for rule in extracted.get("RULE", []):
            node = GraphService.add_node(db, organization_id, "RULE", rule, {"act": "Income Tax Act" if "income tax" in text.lower() else "CGST Act"})
            GraphService.add_edge(db, organization_id, doc_node.id, node.id, "REFERENCES")

        for circ in extracted.get("CIRCULAR", []):
            node = GraphService.add_node(db, organization_id, "CIRCULAR", circ)
            GraphService.add_edge(db, organization_id, doc_node.id, node.id, "REFERENCES")

        for notif in extracted.get("NOTIFICATION", []):
            node = GraphService.add_node(db, organization_id, "NOTIFICATION", notif)
            GraphService.add_edge(db, organization_id, doc_node.id, node.id, "REFERENCES")

        # 5. Extract and Link Deductors/Sections from Form 26AS Entries
        from app.models.models import Form26ASEntry, AISEntry, GSTNoticeEntry
        f26_entries = db.query(Form26ASEntry).filter(Form26ASEntry.document_id == doc_id).all()
        for f26 in f26_entries:
            if f26.deductor_name:
                ded_node = GraphService.add_node(db, organization_id, "DEDUCTOR", f26.deductor_name, {"tan": f26.deductor_tan})
                GraphService.add_edge(db, organization_id, doc_node.id, ded_node.id, "PAID_BY")
                
                # Link Document -> PAN
                if f26.pan:
                    pan_node = GraphService.add_node(db, organization_id, "PAN", f26.pan)
                    GraphService.add_edge(db, organization_id, doc_node.id, pan_node.id, "BELONGS_TO")
                    
                    # Link PAN -> Assessment Year
                    if f26.assessment_year:
                        ay_node = GraphService.add_node(db, organization_id, "ASSESSMENT_YEAR", f26.assessment_year)
                        GraphService.add_edge(db, organization_id, pan_node.id, ay_node.id, "FOR_YEAR")
                        
                        # Link Assessment Year -> Deductor
                        GraphService.add_edge(db, organization_id, ay_node.id, ded_node.id, "HAS_DEDUCTOR")
                        
                # Link Deductor -> Section
                if f26.section:
                    sec_node = GraphService.add_node(db, organization_id, "SECTION", f26.section)
                    GraphService.add_edge(db, organization_id, ded_node.id, sec_node.id, "DEDUCTED_UNDER")

        # 6. Extract and Link AIS Details
        ais_entries = db.query(AISEntry).filter(AISEntry.document_id == doc_id).all()
        for ais in ais_entries:
            if ais.pan:
                pan_node = GraphService.add_node(db, organization_id, "PAN", ais.pan)
                GraphService.add_edge(db, organization_id, doc_node.id, pan_node.id, "BELONGS_TO")
                if ais.assessment_year:
                    ay_node = GraphService.add_node(db, organization_id, "ASSESSMENT_YEAR", ais.assessment_year)
                    GraphService.add_edge(db, organization_id, pan_node.id, ay_node.id, "FOR_YEAR")

        # 7. Extract and Link GST Notices
        gst_entries = db.query(GSTNoticeEntry).filter(GSTNoticeEntry.document_id == doc_id).all()
        for gst in gst_entries:
            if gst.gstin:
                gst_node = GraphService.add_node(db, organization_id, "GSTIN", gst.gstin)
                GraphService.add_edge(db, organization_id, doc_node.id, gst_node.id, "ISSUED_TO")
            if gst.notice_number:
                notice_node = GraphService.add_node(db, organization_id, "NOTICE", gst.notice_number, {"section": gst.section, "authority": gst.authority})
                GraphService.add_edge(db, organization_id, doc_node.id, notice_node.id, "COMPLIANCE_NOTICE")

        return True

    @staticmethod
    def build_graph_for_government_update(db: Session, update_id: str) -> bool:
        """
        Parses a GovernmentUpdate to populate acts, sections, authorities, rules, etc.
        All nodes are organization-scoped (system updates are populated across the organization scope).
        """
        update = db.query(GovernmentUpdate).filter(GovernmentUpdate.id == update_id).first()
        if not update:
            return False

        # Since government updates are global/cross-tenant, we populate graph nodes
        # for all active organizations in the database to maintain strictly scoped tenant graph views.
        from app.models.models import Organization
        orgs = db.query(Organization).filter(Organization.deleted_at.is_(None)).all()
        
        text = update.html_content or ""
        extracted = LegalReferenceExtractor.extract_all(text)

        for org in orgs:
            organization_id = org.id
            
            # Create Update Node
            update_node = GraphService.add_node(
                db, organization_id, "GOVERNMENT_UPDATE", update.document_number or f"Update_{update_id[:8]}",
                {"update_id": update_id, "title": update.title, "authority": update.issuing_authority}
            )

            # Create Authority Node
            auth_node = GraphService.add_node(db, organization_id, "AUTHORITY", update.issuing_authority)
            GraphService.add_edge(db, organization_id, update_node.id, auth_node.id, "ISSUED_BY")

            # Create and Link Legal Reference Nodes
            for sec in extracted.get("SECTION", []):
                node = GraphService.add_node(db, organization_id, "SECTION", sec, {"act": update.related_acts[0] if update.related_acts else "Direct Tax"})
                GraphService.add_edge(db, organization_id, update_node.id, node.id, "REFERENCES")

            for rule in extracted.get("RULE", []):
                node = GraphService.add_node(db, organization_id, "RULE", rule, {"act": update.related_acts[0] if update.related_acts else "Direct Tax"})
                GraphService.add_edge(db, organization_id, update_node.id, node.id, "REFERENCES")

            for circ in extracted.get("CIRCULAR", []):
                node = GraphService.add_node(db, organization_id, "CIRCULAR", circ)
                GraphService.add_edge(db, organization_id, update_node.id, node.id, "REFERENCES")

            for notif in extracted.get("NOTIFICATION", []):
                node = GraphService.add_node(db, organization_id, "NOTIFICATION", notif)
                GraphService.add_edge(db, organization_id, update_node.id, node.id, "REFERENCES")

        return True
