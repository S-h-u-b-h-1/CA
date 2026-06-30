# ITR Preparation Intelligence Engine

The **ITR Preparation Intelligence Engine** aggregates parsed tax values and cross-document reconciliation outputs to help a Chartered Accountant review a return before filing.

## Integration Architecture

```
                 +--------------------------+
                 |  Form 26AS & AIS Parsers |
                 +------------+-------------+
                              |
                              v
                 +------------+-------------+
                 |   Tax Intelligence Engine|
                 +------------+-------------+
                              |
                              v  (Cascade Trigger)
                 +------------+-------------+
                 |  ITR Preparation Engine  |
                 +------------+-------------+
                              |
       +----------------------+----------------------+
       |                      |                      |
       v                      v                      v
+------+-----+         +------+------+         +-----+------+
| ITRProfile |         |ITRReadiness |         | ITRAction  |
+------------+         +-------------+         +------------+
```

## Consolidated Profile Structure
- **itr_profiles:** Stores PAN consistency status, total completeness scores, and processing status.
- **itr_readiness:** Calculates and logs the Readiness percentage.
- **itr_action_items:** Lists filing action tasks referencing specific documents.
- **itr_verification_results:** Maps the automated checks checklists.
