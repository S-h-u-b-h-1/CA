# GST Notice Parser Schema

The GST Notice parser extracts critical parameters from demand notices.

## Database Table: `gst_notice_entries`

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | String(36) | Primary Key (UUID) |
| `organization_id` | String(36) | Tenant isolation link |
| `document_id` | String(36) | Reference to raw_documents |
| `gstin` | String(15) | Taxpayer GSTIN |
| `notice_number` | String(100)| Reference notice number |
| `issue_date` | DateTime | Notice issuance date |
| `reply_due_date`| DateTime | Last date to file response |
| `section` | String(100)| Applicable section (e.g. Section 73) |
| `authority` | String(255)| Issuing tax authority |
| `amount` | Float | Tax demand amount |
| `penalty` | Float | Penalty demanded |
| `interest` | Float | Interest demanded |
| `reason` | Text | Description of mismatch / compliance issue |
| `risk_level` | String(50) | Risk assessment level (LOW, MEDIUM, HIGH) |
| `referenced_sections` | Text | Linked sections |
