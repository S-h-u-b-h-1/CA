# TIS Table Schema Definition

The database table `tis_entries` stores parsed category summary values extracted from TIS documents.

## Schema Details

```sql
CREATE TABLE tis_entries (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id),
    client_id VARCHAR(36) REFERENCES clients(id),
    document_id VARCHAR(36) REFERENCES raw_documents(id),
    pan VARCHAR(10),
    assessment_year VARCHAR(10) NOT NULL,
    financial_year VARCHAR(10),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    reported_value FLOAT DEFAULT 0.0,
    derived_value FLOAT DEFAULT 0.0,
    feedback_value FLOAT DEFAULT 0.0,
    transaction_type VARCHAR(50) DEFAULT 'INCOME',
    raw_row_text TEXT,
    created_at TIMESTAMP
);
```
