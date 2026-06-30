# Tax Intelligence Rules Engine

The **Tax Intelligence Rules Engine** evaluates tax data against multiple compliance rules to generate alarms, notifications, and recommendations.

## Active Rules Matrix

| Rule Name | Severity | Condition / Trigger |
| :--- | :--- | :--- |
| **PAN Mismatch** | `CRITICAL` | Document PAN values mismatch. |
| **AY Mismatch** | `WARNING` | Document Assessment Years mismatch. |
| **Income Missing TDS** | `WARNING` | AIS has reported income category (e.g. Dividend/Interest) > 0 but Form 26AS lacks TDS record. |
| **TDS Missing Income** | `WARNING` | Form 26AS has TDS > 0 but AIS lacks corresponding category. |
| **High TDS Concentration** | `INFO` | Single deductor accounts for > 70% of total tax credit. |
| **Property Purchase** | `INFO` | Immovable property purchase or sale transaction detected. |
| **Large SFT Transaction** | `INFO` | SFT reported amount > ₹5,00,000. |
| **High-Value Mutual Fund** | `INFO` | Mutual Fund transaction amount > ₹2,00,000. |
| **Tax Demand Outstanding** | `WARNING` | Active tax demand > 0. |
| **Tax Refund Claim** | `INFO` | Refund amount > 0. |
| **Duplicate TDS** | `WARNING` | Same deductor, section, and amount entries found multiple times. |
