# ITR Verification Engine

The **Verification Engine** checks raw parser records and aggregated summaries to create a structured compliance checklist.

## Automated Audits Matrix

1. **PAN_CONSISTENCY:** Cross-references the PAN on uploaded PDFs against `client.PAN` to verify document ownership.
2. **AY_CONSISTENCY:** Verifies that the document tax assessment year matches the selected assessment year.
3. **DUPLICATE_CHECK:** Alerts if multiple entries in Form 26AS or AIS share matching deductors, sections, and values.
4. **INTEREST_VERIFICATION:** Flags discrepancies where interest categories are reported in AIS but TDS or disclosure matches are absent.
5. **DIVIDEND_VERIFICATION:** Flags cases where dividend income is reported but matching TDS credit is missing.
6. **SUPPORTING_DOCUMENTS:** Verifies that all target checklist documents are uploaded.
7. **HIGH_VALUE_TRANSACTION_CHECK:** Triggers when individual transactions exceed the ₹2,00,000 reporting threshold.
