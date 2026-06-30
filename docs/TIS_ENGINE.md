# TIS (Taxpayer Information Summary) Intelligence Engine

The **TIS Intelligence Engine** parses Taxpayer Information Summary (TIS) PDFs, registers parsed values in dedicated tables, and compares values against AIS processed value entries and Form 26AS tax credits.

## Ingestion Architecture

```
                    +---------------------------+
                    |    TIS PDF File Upload    |
                    +-------------+-------------+
                                  |
                                  v
                    +-------------+-------------+
                    |   TIS Ingestion Pipeline  |
                    +-------------+-------------+
                                  |
                                  v
                    +-------------+-------------+
                    |        TISParser          |
                    +-------------+-------------+
                                  |
                                  v
                    +-------------+-------------+
                    |     tis_entries (DB)      |
                    +-------------+-------------+
                                  |
                                  v  (Cascade Trigger)
                    +-------------+-------------+
                    |    TaxIntelligenceService |
                    +---------------------------+
```

## Parsing Mechanics
- **TISParser** extracts category metrics (Reported, Derived, and Feedback values) from TIS line-by-line schedules.
- If feedback values differ from derived values, a compliance mismatch alert is generated.
