# Client Health Score Engine

The **Client Health Score** measures tax readiness and compliance. It is calculated dynamically based on data quality factors and active warnings.

## Calculation Formula

The score has a baseline max of 100 points, derived from three factors:

1. **Document Completeness (Max 40 points):**
   - 15 points for `Form 26AS` upload.
   - 15 points for `AIS` upload.
   - 10 points for `TIS` upload.
2. **ITR Readiness (Max 30 points):**
   - Multiplies the raw ITR readiness percentage (0 to 100) by a factor of 0.3.
3. **Mismatches & Tasks Deductions (Max 30 points, deducts from 30):**
   - Deducts 10 points for each `CRITICAL` mismatch or action item.
   - Deducts 5 points for each `WARNING` severity mismatch or warning item.
   - Deducts 3 points for each unresolved checklist task.

## Classifications

- **Excellent (80 - 100):** Clean client state, ready to draft return.
- **Good (60 - 79):** Most documents present, minor items to resolve.
- **Needs Attention (40 - 59):** Missing core documents or active tax mismatches.
- **Critical (0 - 39):** Multiple critical alerts and unresolved items.
