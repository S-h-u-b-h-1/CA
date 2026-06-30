# Client Workspace Aggregate API

The endpoint `GET /api/v1/clients/{client_id}/workspace` consolidates all client workspace parameters into a single response to optimize front-end rendering performance.

## Aggregated JSON Payload

```json
{
  "overview": {
    "client_name": "Suasion Finvest Pvt Ltd",
    "PAN": "AADCS6785Q",
    "GSTIN": "27AADCS6785Q1Z1",
    "status": "ACTIVE",
    "assessment_year": "2025-26",
    "financial_year": "2024-25",
    "assigned_manager": "Unassigned",
    "assigned_partner": "Unassigned",
    "created_at": "2026-06-30T10:00:00Z",
    "last_activity": "2026-06-30T12:00:00Z",
    "health_score": "Good",
    "health_score_value": 75.0
  },
  "documents": [
    {
      "id": "doc-uuid",
      "name": "Form26AS.pdf",
      "category": "Form 26AS",
      "processing_status": "COMPLETED",
      "parser_status": "COMPLETED",
      "version": "1.0",
      "confidence": 95.0,
      "processing_time": 3.2
    }
  ],
  "tax_intelligence": {
    "total_tds": 24890.0,
    "income_summary": {
      "interest": 12500.0,
      "dividend": 1400.0,
      "salary": 0.0,
      "securities": 0.0,
      "mutual_fund": 0.0,
      "property": 0.0,
      "sft": 0.0
    },
    "refund": 0.0,
    "demand": 0.0,
    "high_value_transactions": 0,
    "mismatches": [],
    "insights": []
  },
  "itr_preparation": {
    "readiness_score": 75.0,
    "missing_documents": [],
    "verification_checklist": [],
    "pending_actions": [],
    "warnings": [],
    "completion_percentage": 75.0
  },
  "research": {
    "recent_queries": [],
    "saved_notes": [],
    "bookmarks": [],
    "suggestions": []
  },
  "tasks": [],
  "notes": [],
  "timeline": []
}
```
