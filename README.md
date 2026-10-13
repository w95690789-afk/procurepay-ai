# 🤖 ProcurePay AI — Smart Finances, Better Business
### Enterprise Autonomous B2B Procurement, Multimodal Vision, SAT 3-Way Audit, Multi-DMS Ledger & Instant PayPal Settlement
**Submission for PayPal AI Hackathon 2026 (Devpost)**

[![Live Demo](https://img.shields.io/badge/Production%20Demo-Vercel%20Live-success?style=for-the-badge&logo=vercel)](https://procurepay-ai.vercel.app)
[![PayPal Developer](https://img.shields.io/badge/PayPal-Orders%20%2B%20Payouts%20%2B%20Disputes%20v2.5-003087?style=for-the-badge&logo=paypal)](https://developer.paypal.com)
[![AG Grid](https://img.shields.io/badge/AG%20Grid-v31%20Enterprise%20Partner-teal?style=for-the-badge&logo=aggrid)](https://www.ag-grid.com)
[![Groq AI](https://img.shields.io/badge/Groq-Llama%203.3%20%2B%20Vision-orange?style=for-the-badge)](https://groq.com)

---

## 💡 Inspiration & The B2B Friction Problem

In modern enterprise operations, the procurement-to-pay (P2P) lifecycle is plagued by massive cognitive friction, human delays, and compliance liabilities:
* **Unstructured Ingestion:** Technicians request parts via messy WhatsApp voice notes, informal emails, or photos of burned machine plates with no standardized catalog SKU.
* **Orphan & Uncatalogued Items:** Over 40% of factory requisitions refer to uncatalogued items, stalling purchasing workflows for days.
* **Invoice Fraud & Discrepancies:** 15% of supplier invoices contain hidden price surges (+15% to +35%), unapproved items, or originate from blacklisted tax shell companies (e.g., Mexican SAT Art. 69-B EFOS).
* **Slow Vendor Settlement:** Traditional manual supplier disbursement takes **16 days**, straining critical supply chain relationships.
* **ERP Fragmentation:** Fragmented corporate accounting requires manual translation across divergent ERPs (SAP Business One, Intelisis, Microsoft Dynamics 365, and CONTPAQi).

**ProcurePay AI** solves this end-to-end by orchestrating a sovereign squad of cognitive agents wrapped in the **FINNOVA** executive design system, automating the entire journey from damaged part photo to instant PayPal settlement in **4.2 seconds**, with zero data leakage and human-in-the-loop governance.

---

## ⚡ Architecture & End-to-End Autonomous Workflow

```mermaid
graph TD
    A["📷 Multimodal Ingestion<br/>(Photo of Damaged Part / WhatsApp / Email / Excel FMA-017 / SAT XML)"] --> B["🧠 Vision & Orphan Item Classifier<br/>(Groq Llama Vision + 3-Tier AI Normalization)"]
    B --> C["📁 SharePoint M365 Document Hub<br/>(Autonomous Lifecycle Sync)"]
    C --> D["🤖 Multi-Vendor RFQ Consolidator<br/>(Cost 60% • SLA 25% • Rating 15%)"]
    D --> E["⚖️ SAT 3-Way Matching Auditor<br/>(PO vs Quote vs Invoice & Art. 69-B EFOS)"]
    E --> F{"Auditor Forensic Verdict"}
    
    F -->|"🚨 Fraud / Price Surge / EFOS"| G["⚖️ PayPal AI Dispute Engine<br/>(Cryptographic SHA-256 Claim Filed via Disputes API)"]
    F -->|"✅ Audit Passed (100% Exact)"| H["📊 Cognitive Accounting Engine<br/>(Balanced Debe/Haber & Multi-DMS: SAP/Intelisis/Dynamics/CONTPAQi)"]
    
    H --> I{"Amount Policy Check<br/>Amount <= $500 USD?"}
    I -->|"⚡ Autonomous Pass (< $500)"| J["💳 PayPal Payouts API v1<br/>(Instant Autonomous Settlement in 4.2s)"]
    I -->|"👤 Executive Approval (> $500)"| K["🔐 PayPal Orders API v2<br/>(Smart Checkout Link for Human Approval)"]
```

---

## 🌟 Key Capabilities & Innovations

### 1. 🎨 FINNOVA Executive Design System
* **Light & Clean Metric Canvas:** Pill navigation (`Overview`, `Estimates`, `Invoices`, `Payments`, `Contabilidad NIF`, `SharePoint`).
* **4 Financial KPI Cards:** Overdue/SAT Risk ($24,850), Due Next Month ($142,560 with interactive monthly chart), Settlement Velocity (**4.2s** vs 16 days manual), and Available Instant Payout (**$186,540** in PayPal Sandbox with payment selector).
* **Deep Indigo Master-Detail Drawer (`#0f172a` & `#312e81`):** Left-side unpaid invoice ledger with right-side rich item breakdown, tax withholdings, and instant action triggers.

### 2. 📷 Multimodal Industrial Vision Inspection
* Ingests photographs of damaged components (sensors, servo motors, bearings, pneumatic valves).
* Extracts technical nameplates, voltage/dimensions, suggests master catalog SKUs, and auto-generates purchase requisitions.

### 3. ⚖️ Automated PayPal Dispute Resolution Engine
* When forensic 3-Way matching audits fail due to EFOS blacklists or price alteration, ProcurePay AI does not just block disbursement: it automatically constructs a formal legal dossier with cryptographic SHA-256 audit seals and files the claim via the **PayPal Customer Disputes API v1**.

### 4. 📊 Multi-DMS & Fiscal Accounting Engine (NIF C-4 / SAT)
* Generates balanced double-entry journal entries (Total Debe = Total Haber).
* Automatically calculates Mexican tax withholdings: **4% VAT withholding** on freight logistics and **10.667% VAT / 10% ISR** on leasing.
* Real-time multi-ERP translator live switcher:
  * **SAP Business One** (`600-400-01`)
  * **Intelisis ERP México** (`GAS-MTO-01`)
  * **Microsoft Dynamics 365** (`EXP-MAINT-40`)
  * **CONTPAQi** (`602-004-000`)

### 5. 📁 SharePoint M365 Document Lifecycle Simulator
* Live synchronization with enterprise folders: `/Buzon_Entrada_Requisiciones`, `/En_Cotizacion`, and `/Aprobados_Pagados` with audit compliance dossiers.

---

## 🛠️ Tech Stack & Integrations

* **Payment & Treasury Rails:**
  * **PayPal Payouts API v1:** Zero-touch batch disbursement under $500 threshold.
  * **PayPal Orders API v2:** Human-in-the-loop authorization checkout for high-value purchases.
  * **PayPal Customer Disputes API v1:** Automated dispute and evidence submission.
  * **OAuth2 Bearer Token Authentication:** Auto-renewing sandbox session.
* **AI & Multimodal Orchestration:**
  * **Groq Llama 3.3 70B & Llama 3.2 11B Vision:** Sub-second reasoning and photo analysis.
  * **OpenRouter Cognitive Gateway:** Fallback reasoning with structured JSON schemas.
* **Enterprise Table Partner:**
  * **AG Grid v31 (Official Hackathon Partner):** Enterprise interactive matrix for supplier quotes, audit histories, and catalog search.
* **Backend:** Python 3.14, FastAPI, Uvicorn, Pydantic, Pandas, OpenPyXL.
* **Frontend:** Tailwind CSS, Phosphor Icons, Vanilla JavaScript, AG Grid Alpine theme.
* **Cloud Infrastructure:** Vercel Serverless Production with CI/CD deployment.

---

## 🧪 1-Click Executive Presets (Interactive Evaluation)

1. **Preset 1: FMA-017 Requisition + Orphan Classifier + Instant PayPal Settlement**
   * Processes multi-item maintenance order, classifies orphan nitrile gloves & sensors, audits prices, and disburses payment in 4.2s.
2. **Preset 2: Freight Logistics + 4% VAT Withholding (Art. 1-A LIVA)**
   * Tests specialized fiscal withholdings, generating balanced journal entry with retentions.
3. **Preset 3: High-Value Robotic Equipment > $500 (Fanuc AC Servo)**
   * Detects total of $2,737.60 USD exceeding auto-threshold, generating PayPal Orders approval link for director authorization.
4. **Preset 4: SAT 69-B Fraud Block + Automated PayPal Dispute**
   * Intercepts blacklisted EFOS ghost vendor and 331% price surge, halting disbursement and filing a formal PayPal dispute docket with SHA-256 evidence.

---

## 🌐 Live Production Links

* **Live Cloud Application:** [https://procurepay-ai.vercel.app](https://procurepay-ai.vercel.app)
* **GitHub Repository:** [https://github.com/w95690789-afk/procurepay-ai](https://github.com/w95690789-afk/procurepay-ai)
* **License:** MIT License
