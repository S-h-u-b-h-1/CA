# Change Detection Engine Specification

This document details the mechanics of the **Change Detection Engine** in **CA Intelligence**, which automatically highlights revisions between statutory notifications.

---

## Comparison Mechanics

The `VersioningEngine` in `app.services.versioning` compares two documents using a paragraph-level diffing algorithm based on the Gestalt Pattern Matching technique implemented in Python's `difflib.SequenceMatcher`.

### Ingestion & Chunking
1. The engine strips carriage returns and splits the layout-normalized markdown text by double newlines (`\n\n`) into a list of paragraph strings.
2. Blank lines are filtered out to ensure comparisons focus strictly on semantic text blocks.

### Matching Opcodes
The `SequenceMatcher` aligns the old paragraph list and new paragraph list, identifying blocks that are:
- `insert`: Text block was introduced in the new version.
- `delete`: Text block was removed in the new version.
- `replace`: Text block was modified. The engine records both the old paragraph and the new replacement paragraph side-by-side to highlight inline differences.

---

## Statutory Citation Differences

In addition to pure text changes, the engine extracts amendments to legal references (sections and rules).

### Regex Extraction
The engine applies standard regulatory citation search patterns:
```python
sec_pattern = r"\b(?:Section|Sec\.?|Rule)\s+([0-9A-Za-z\(\)]+)\b"
```
It extracts all cited rules and sections from both document versions.

### Delta Compilation
By comparing the sets of extracted citations, it compiles two list indicators:
- **Added Sections**: Law sections cited in the new version but missing in the previous version. E.g. indicating newly introduced provisions.
- **Removed Sections**: Law sections cited in the previous version but removed from the new version. E.g. indicating repealed or amended provisions.

---

## JSON Diff Format

The differences are saved inside `government_update_versions.structured_differences` matching the following schema:

```json
{
  "added_paragraphs": [
    "1. Compliance filing deadlines under section 143(1) are extended to July 31."
  ],
  "removed_paragraphs": [
    "1. Compliance filing deadlines under section 143(1) are extended to June 30."
  ],
  "changed_sections": {
    "added_sections": [],
    "removed_sections": []
  },
  "differences": {
    "added_count": 1,
    "removed_count": 1,
    "changed_count": 1,
    "detailed_changes": [
      {
        "old_content": "1. Compliance filing deadlines under section 143(1) are extended to June 30.",
        "new_content": "1. Compliance filing deadlines under section 143(1) are extended to July 31."
      }
    ]
  }
}
```

This structured diff is consumed directly by the Admin Panel revision dashboard to display additions (green) and deletions (red) side-by-side.
