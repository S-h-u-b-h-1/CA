# Cross-Document Matching Engine

The **Matching Engine** matches tax records across document boundaries. It matches Form 26AS lines against corresponding Annual Information Statement (AIS) transaction lines.

## Correlation Criteria

| Correlation Parameter | Match Check | Action on Failure |
| :--- | :--- | :--- |
| **PAN Verification** | Strict exact match on PAN between Form 26AS and AIS | `CRITICAL` Alarm |
| **AY Verification** | Verify Assessment Year matching | `WARNING` Alarm |
| **Deductor TAN / Name** | Match deductor identifier against reported sources | `WARNING` Mismatch Flag |
| **Amount Reconciliation** | Compare TDS amounts with corresponding transaction values | `MISMATCH` Flag |

## Matching Flow
1. **Document Relationships:** Creates `DocumentRelationship` mappings of type `FORM_26AS_TO_AIS`.
2. **Reconciliation Checks:** Compares aggregate numbers to confirm that Form 26AS TDS is accounted for in the AIS reported categories.
3. **Discrepancy Logging:** Saves mismatch cases inside the `document_matches` table.
