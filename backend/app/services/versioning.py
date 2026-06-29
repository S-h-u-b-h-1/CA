import re
import difflib
from typing import Dict, List, Any

class VersioningEngine:
    @staticmethod
    def compare_texts(old_text: str, new_text: str) -> Dict[str, Any]:
        """
        Calculates differences between two document texts on a paragraph basis.
        Extracts added paragraphs, removed paragraphs, and changes in referenced law sections.
        """
        if not old_text:
            old_text = ""
        if not new_text:
            new_text = ""

        # Normalize carriage returns and split by paragraph
        old_paras = [p.strip() for p in old_text.replace("\r", "").split("\n\n") if p.strip()]
        new_paras = [p.strip() for p in new_text.replace("\r", "").split("\n\n") if p.strip()]

        matcher = difflib.SequenceMatcher(None, old_paras, new_paras)
        
        added: List[str] = []
        removed: List[str] = []
        changed: List[Dict[str, str]] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                for idx in range(j1, j2):
                    added.append(new_paras[idx])
            elif tag == 'delete':
                for idx in range(i1, i2):
                    removed.append(old_paras[idx])
            elif tag == 'replace':
                # Map old and new line replacements sequentially
                for o_idx in range(i1, i2):
                    removed.append(old_paras[o_idx])
                for n_idx in range(j1, j2):
                    added.append(new_paras[n_idx])
                    
                    corresponding_old = old_paras[i1 + (n_idx - j1)] if (i1 + (n_idx - j1)) < i2 else ""
                    changed.append({
                        "old_content": corresponding_old,
                        "new_content": new_paras[n_idx]
                    })

        # Section-level changes analysis (e.g. Section 143(1)(a) or Rule 12D)
        sec_pattern = r"\b(?:Section|Sec\.?|Rule)\s+([0-9A-Za-z\(\)]+)\b"
        old_sections = set(re.findall(sec_pattern, old_text, re.IGNORECASE))
        new_sections = set(re.findall(sec_pattern, new_text, re.IGNORECASE))

        added_sections = list(new_sections - old_sections)
        removed_sections = list(old_sections - new_sections)

        return {
            "added_paragraphs": added,
            "removed_paragraphs": removed,
            "changed_sections": {
                "added_sections": added_sections,
                "removed_sections": removed_sections
            },
            "differences": {
                "added_count": len(added),
                "removed_count": len(removed),
                "changed_count": len(changed),
                "detailed_changes": changed
            }
        }
