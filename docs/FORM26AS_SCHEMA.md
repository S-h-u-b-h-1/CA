# Form 26AS Parser Schema

The Form 26AS parser extracts information from tax credit statements.

## Database Tables

### `form26as_entries`
Stores individual tax deduction transaction rows.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | String(36) | Primary Key (UUID) |
| `organization_id` | String(36) | Tenant isolation link |
| `document_id` | String(36) | Reference to raw_documents |
| `pan` | String(10) | Taxpayer PAN |
| `assessment_year` | String(10) | Assessment Year (e.g. 2026-27) |
| `financial_year` | String(10) | Financial Year (e.g. 2025-26) |
| `taxpayer_name` | String(255)| Name of taxpayer |
| `deductor_name` | String(255)| Deductor's corporate name |
| `deductor_tan` | String(10) | Deductor's TAN |
| `section` | String(50) | IT Act Section (e.g. 194C, 194J) |
| `amount_paid` | Float | Gross amount paid |
| `tax_deducted` | Float | Tax deducted |
| `tax_deposited` | Float | Tax deposited |

### `deductor_entries`
Stores unique deductors associated with the statement.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | String(36) | Primary Key (UUID) |
| `deductor_name` | String(255)| Corporate name |
| `deductor_tan` | String(10) | TAN code |
| `total_tds` | Float | Combined TDS amount |

### `challan_entries`
Stores advance tax and self-assessment tax challans.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | String(36) | Primary Key (UUID) |
| `challan_number` | String(50) | Challan identification number |
| `bsr_code` | String(20) | BSR code of depositing bank branch |
| `amount` | Float | Deposited amount |
| `date_of_deposit` | DateTime | Date tax was deposited |
