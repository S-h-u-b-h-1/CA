# TIS Cross-Document Reconciliation Rules

The **Matching Engine** correlates TIS values against Form 26AS and AIS entries.

## Cross-Document Validation Rules

### 1. TIS vs AIS reported values mismatch
- Category reported value totals in TIS are matched against AIS processed value totals.
- Discrepancy threshold: `abs(TIS - AIS) > ₹10`.
- Severity: **WARNING**.

### 2. TIS Feedback vs Derived value mismatch
- Identifies if a client's tax feedback differs from derived system calculations.
- Discrepancy threshold: `abs(feedback_value - derived_value) > ₹10`.
- Severity: **WARNING**.

### 3. Unexpected High-Value Transactions
- Triggers if individual reported category exceeds ₹5,00,000.
- Severity: **WARNING**.
