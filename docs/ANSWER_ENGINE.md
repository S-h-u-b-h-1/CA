# Answer Engine Design

The **Answer Engine** acts as the synthesis layer between search results and the research workspace output.

## Synthesis Logic

1. **Token Matching:** Evaluates search query terms against indexed titles, sections, and keywords inside the database.
2. **Relevance Scoring:** Computes weightings favoring exact section and title matches over content frequency.
3. **No-Hallucination Guard:** If no sources match the search keywords, the engine stops and outputs a strict zero-evidence response:
   *"No authoritative sources found in the database. As per CA rules, no answers can be generated without verified sources."*
4. **Client Context Correlation:** Intersects the matched law with selected client documents, active tax mismatches, or outstanding action items.
