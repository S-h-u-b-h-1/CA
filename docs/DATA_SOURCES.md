# CA Intelligence: Compliance Data Sources Registry

This registry tracks the external official systems and internal document repositories used by CA Intelligence to fetch real-time rules, client records, circulars, and notifications.

---

## Data Source Directory

| Source Name | Category | Access Method | Auth Required | Storage Allowed | Purpose / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Income Tax e-Filing API** | Income Tax | ERI API / Direct Integration | Yes | Yes (Metadata / Selected Returns) | Accessing client ITR status, Form 26AS, AIS/TIS data securely under ERI license. |
| **GSTN API (via GSP)** | GST | GSP Paid API | Yes | Yes | Accessing GSTR-1, GSTR-3B, GSTR-2B client files and filing status. |
| **CBIC Circulars & Notifications** | Indirect Tax | RSS Feed / Scraping / Public API | No | Yes (Cached Index) | Indexing official circulars, notifications, tariff updates, and custom GST rates. |
| **GST Council Portal** | GST | Scraping / Manual Feed | No | Yes | Cataloging council decisions and recommendations. |
| **MCA Portal / V3 Data** | MCA / ROC | Paid API / Public Scraping | Yes (API Access) | Yes | Indexing director listings, CIN details, charge details, and ROC filing filings. |
| **e-Gazette India** | Central Government | Web Scraping / PDF Parse | No | Yes (Indexed text) | Official notifications regarding acts, bills, and notifications. |
| **RBI Notifications** | Banking / FEMA | RSS / Scraping | No | Yes | Circulars affecting commercial transactions, FEMA, and banking operations. |
| **eCourts Services** | Legal Disputes | Paid API / CAPTCHA Bypass API | Yes (or Scraping) | Yes | Tracking tax tribunal and high court litigation status for client cases. |
| **data.gov.in** | Open Data | Public REST API | No | Yes | General statistics and financial indexes. |
| **Client Uploads (ITR, GST, BS)** | Private Data | Direct File Upload (PDF/XLSX) | Yes | Yes (Secure & Isolated) | Client documents uploaded by CA firm for notice reply drafting and analysis. |
| **Internal Firm Knowledge** | Custom | File Upload / DB Storage | Yes | Yes | Firm-specific templates, internal memos, and audit checklists. |

---

## Security & Compliance Architecture Guidelines

1. **Authentication Boundary**: Under no circumstances should direct scraping of client-authenticated portals (such as bypassing Income Tax or GST OTP/credentials without standard API channels) be done. Use official ERI or GSP channels.
2. **Authorized Data Retention**: Under Indian IT rules (Section 43A of IT Act), financial information must be stored with strict organization-level access controls.
3. **Data Caching**: Public resources (CBIC circulars, RBI updates) can be globally cached and index-searched across all tenants. Private client uploads must never be indexed globally.
