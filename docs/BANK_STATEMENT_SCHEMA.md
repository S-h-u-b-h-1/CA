# Bank Statement Parser Schema

The Bank Statement parser parses transactional rows from statement sheets.

## Database Table: `bank_statement_transactions`

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | String(36) | Primary Key (UUID) |
| `organization_id` | String(36) | Tenant isolation link |
| `document_id` | String(36) | Reference to raw_documents |
| `account_holder`| String(255)| Customer account name |
| `bank_name` | String(255)| Issuing bank name |
| `account_number`| String(100)| Customer account number |
| `ifsc` | String(20) | Bank branch IFSC |
| `opening_balance`| Float | Balance at opening date |
| `closing_balance`| Float | Balance at statement close |
| `transaction_date`| DateTime | Transaction timestamp |
| `particulars` | Text | Narration string |
| `transaction_type`| String(10) | DEBIT / CREDIT |
| `amount` | Float | Transaction amount |
| `balance` | Float | Running ledger balance |
| `upi_ref` | String(100)| UPI transaction reference code |
| `neft_rtgs_ref` | String(100)| NEFT/RTGS reference code |
| `cheque_number` | String(50) | Cheque number |
