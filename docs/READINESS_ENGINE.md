# ITR Readiness Score Calculation

The **ITR Readiness Score** quantifies how ready the client's tax file is for return filing. It evaluates document completeness alongside failed compliance rule severity.

## Scoring Weights

The score starts at a baseline of `100.0` points. Deduction rules are applied as follows:

| Factor / Rule Failed | Point Deduction | Importance |
| :--- | :--- | :--- |
| **Missing Form 26AS** | `-30.0` | Primary Tax Credit Document |
| **Missing AIS** | `-30.0` | Primary Income Summary |
| **Missing Form 16** | `-20.0` | Salary Schedule Support |
| **Missing Bank Statement** | `-15.0` | Verification Support |
| **PAN Discrepancy** | `-20.0` | Critical Identity Check |
| **Assessment Year Discrepancy** | `-15.0` | Filing Validity Check |
| **Interest/Dividend Discrepancy** | `-10.0` | Income Reconciliation |
| **Duplicate Entries** | `-5.0` | Transaction Duplication Alert |

## Return Preparation Status
- **PENDING_DOCUMENTS:** Score < 80.0
- **READY_TO_PREPARE:** Score >= 80.0
