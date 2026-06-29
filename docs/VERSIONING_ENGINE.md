# Versioning Engine Specification

This document describes how **CA Intelligence** handles updates and revisions of official government documents without over-writing existing historical knowledge.

---

## Architectural Principles

1. **Immutability of Ingested Text**: Once a version of a circular or gazette notification is downloaded, it is checksum-locked and never modified.
2. **Version Chaining**: When a document number matches an existing database entry but the file hash differs, a new version is created.
3. **Difference Tracking**: The system calculates the textual difference between the previous and new version at a paragraph level. This diff is saved in a JSON payload to power the admin diff viewer.

---

## Database Version Schema (`government_update_versions`)

Revisions are stored in the `government_update_versions` table:
- **`version_number`**: Monotonically increasing index starting at 1.
- **`raw_file_path`** / **`html_content`**: Path to the raw bytes and raw HTML/text transcription of the revision.
- **`markdown_content`**: Layout-normalized markdown representation of the text.
- **`checksum`**: SHA-256 fingerprint of the download.
- **`added_paragraphs`**: JSON array of text paragraphs introduced in this revision.
- **`removed_paragraphs`**: JSON array of text paragraphs deleted or modified from the previous revision.
- **`changed_sections`**: JSON dictionary comparing referenced law sections:
  ```json
  {
    "added_sections": ["Section 194Q", "Section 206C"],
    "removed_sections": ["Section 194"]
  }
  ```
- **`structured_differences`**: Bitwise changes mapping changed paragraph blocks sequentially.

---

## Version Ingestion Flow

```python
# Pseudo-code logic inside BaseConnector.sync()
existing = db.query(GovernmentUpdate).filter_by(document_number=doc_num).first()

if existing:
    prev_ver = db.query(GovernmentUpdateVersion).filter_by(
        government_update_id=existing.id
    ).order_by(GovernmentUpdateVersion.version_number.desc()).first()
    
    if prev_ver.checksum == new_checksum:
        return  # Skip, duplicate detected
        
    next_ver = existing.version + 1
    diff_payload = VersioningEngine.compare_texts(
        prev_ver.markdown_content, 
        new_normalized_markdown
    )
    
    # Save V{next_ver} logs
    new_version_log = GovernmentUpdateVersion(
        government_update_id=existing.id,
        version_number=next_ver,
        markdown_content=new_normalized_markdown,
        checksum=new_checksum,
        added_paragraphs=diff_payload["added_paragraphs"],
        removed_paragraphs=diff_payload["removed_paragraphs"],
        changed_sections=diff_payload["changed_sections"],
        structured_differences=diff_payload["differences"]
    )
```
This design ensures legal teams can review exactly what changed in tax provisions year-over-year.
