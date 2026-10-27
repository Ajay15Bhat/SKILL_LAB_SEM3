# ClauseTrace — Contract Review & Change-Impact Platform

> **An evidence-grounded, immutable contract review and change-impact analysis platform.**  
> Built for compliance analysts and legal reviewers to upload vendor service agreements, inspect extracted clauses, evaluate policy rules, visually compare revisions, and approve specific versions with a cryptographic audit trail.

---

## 1. Executive Summary & Core Workflow

Enterprise vendor agreements and Master Service Agreements (MSAs) evolve over time. When a vendor sends "Version 2", critical terms are often subtly changed (e.g., termination notice increased from 30 days to 60 days, or new termination penalty fees added).

ClauseTrace solves this with a **deterministic, evidence-grounded pipeline**:

$$\text{Contract} \longrightarrow \text{Version (v1)} \longrightarrow \text{Clauses} \longrightarrow \text{Requirement} \longrightarrow \text{Finding} \longrightarrow \text{Approval}$$
$$\Downarrow \text{ (Upload v2)}$$
$$\text{Version (v2)} \longrightarrow \text{Deterministic Diff} \longrightarrow \text{Impact Engine Flags Requirement} \longrightarrow \text{Fresh Review}$$

### The Acceptance Criteria Demo Scenario
1. **Upload v1:** Analyst uploads Version 1 of an agreement. The system computes a SHA-256 fingerprint, extracts clauses page-by-page, and evaluates a *"30-day termination notice"* requirement.
2. **Grounded Finding:** The hybrid search engine locates Clause 3, extracts the quote, and marks the finding as **`SATISFIED`**.
3. **Reviewer Sign-Off:** A Reviewer approves Version 1. Status changes to **`APPROVED`** with a cryptographic signature hash.
4. **Upload v2 (Sneaky Revision):** The vendor updates the agreement to 60 days notice with a termination fee. Analyst uploads Version 2.
5. **Immutable History:** Version 1 remains **`APPROVED`** in history. Version 2 is created in **`DRAFT`**.
6. **Diff & Change Impact:** The backend runs a clause-by-clause diff, highlights the altered sentence, and **automatically flags the 30-day notice requirement in v2 as `NEEDS_REVIEW`**!
7. **Audit Ledger:** Every upload, evaluation, override, diff, and approval is immutably logged.

---

## 2. Key Architectural Decisions (Why We Made Them)

To ensure this project is **high-performing, robust, and easily defensible during academic and technical evaluations**, we made five strategic architectural choices:

### A. The "Sweet-Spot" 6-Table Schema (Pruning Enterprise Bloat)
* **Initial Enterprise Spec:** 12 tables (multi-tenant company switchers, task queues, separate obligations boards, version diff tables, approvals tables).
* **Our Decision:** Streamlined down to **6 purposeful, high-value tables**:
  1. `users` (Analyst vs. Reviewer personas)
  2. `contracts` (Agreement container)
  3. `contract_versions` (Immutable revisions with SHA-256 fingerprints & approval state)
  4. `clauses` (Segmented text chunks with PostgreSQL `tsvector` full-text search)
  5. `requirements` (Compliance rules / review policies)
  6. `findings` (Version-tied evaluations enforcing *No Silent Inheritance*)
  7. `audit_logs` (Append-only event ledger with PostgreSQL database immutability triggers)
* **Rationale:** Diffing is computed dynamically on the fly (saving database space and ensuring fresh calculations), approvals are tied directly to versions, and the schema can be fully understood and explained in 2 minutes.

### B. The Hybrid Retrieval Architecture (PostgreSQL FTS + Gemini Flash)
* **The Problem:** Blindly feeding 50-page legal PDFs into an LLM is slow, expensive, prone to hallucinations, and violates legal auditability. Pure keyword search misses semantic equivalents (e.g., *"one month"* vs. *"30 days"*).
* **Our Decision (Hybrid Pipeline):**
  1. **Deterministic Filter:** PostgreSQL native Full-Text Search (`tsvector` + `ts_rank_cd` Cover Density ranking) scans the contract in 5ms to retrieve the top 4 candidate clauses.
  2. **Semantic Judge:** Google Gemini Flash evaluates only those candidate clauses against the formal legal requirement, returning structured JSON with an exact quote and confidence score.
  3. **Human-in-the-Loop:** AI only *proposes* findings; human Reviewers must confirm or override. AI never makes autonomous legal decisions.

### C. Strict Guardrails: "No Silent Inheritance"
* **Rule:** A new contract revision must **never** inherit approvals or findings from a previous version without explicit recalculation.
* **Implementation:** The `findings` table enforces a composite unique constraint `(requirement_id, contract_version_id)`. When v2 is uploaded, fresh findings are created exclusively for v2.

### D. Deterministic Text Diffing via Standard `difflib`
* **Decision:** We use Python’s built-in `difflib` to compute unified clause diffs and word-level modifications.
* **Change Impact:** The engine inspects which clause in v1 grounded each compliance requirement. If that clause was altered in v2, that requirement is automatically flagged for mandatory reassessment.

### E. Private Local File Storage
* **Decision:** PDFs are stored server-side in `./storage/contracts/{sha256}.pdf`.
* **Rationale:** Keeps documents strictly private (not exposed over public URLs), prevents duplicate uploads via SHA-256 deduplication, and avoids cloud bucket CORS issues.

---

## 3. Current Progress: What Has Happened Till Now

### Phase 1: Database Architecture & Models ✅ (Completed & Verified)
* [x] Designed declarative SQLAlchemy 2.x models with UUID primary keys and timestamp mixins.
* [x] Configured Supabase PostgreSQL with `asyncpg` asynchronous database driver.
* [x] Implemented PostgreSQL GIN full-text search index (`ix_clauses_fts`) on generated `tsvector` columns.
* [x] Added PostgreSQL trigger (`trg_audit_immutable`) that throws exceptions on any `UPDATE` or `DELETE` attempt on audit logs.
* [x] Created database seed users (`Alex Analyst` and `Rachel Reviewer`).
* [x] Built automated connection and environment test script (`test_setup.py`).

### Phase 2: FastAPI Core Backend & Services ✅ (Completed & Verified)
* [x] **Configuration:** Pydantic Settings reading `.env` with auto-normalizing database URLs.
* [x] **PDF Ingestion:** Streaming upload endpoint calculating SHA-256 checksums in memory and preventing duplicates (`POST /api/v1/contracts/{id}/versions/upload`).
* [x] **Clause Segmentation:** PyMuPDF (`fitz`) service extracting text blocks, page numbers, and section headers into `clauses`.
* [x] **Hybrid Evaluation:** Combined PostgreSQL `tsvector` candidate search + Gemini Flash structured legal reasoning (`POST /api/v1/versions/{id}/evaluate`).
* [x] **Human Review Override:** Endpoints allowing Reviewers to confirm or override findings with audit logging (`PATCH /api/v1/findings/{id}`).
* [x] **Deterministic Diffing:** Clause-by-clause comparator with visual red/green line diffs (`GET /api/v1/contracts/{id}/diff`).
* [x] **Change Impact Engine:** Automated detection of modified clauses and flagging of affected compliance rules.
* [x] **Approvals State Machine:** Reviewer sign-off generating cryptographic SHA-256 digital signature hashes (`POST /api/v1/versions/{id}/approve`).
* [x] **Audit Trail:** Chronological timeline endpoint (`GET /api/v1/audit-trail`).
* [x] **Sample Contracts:** Automated generator creating real test PDFs (`v1_vendor_agreement.pdf` and `v2_vendor_agreement.pdf`).
* [x] **Interactive Swagger Docs:** Live at `http://localhost:8000/docs`.

---

## 4. What Is Left to Do (Phase 3: Next.js Frontend)

* [ ] **Next.js (App Router) Setup:** TypeScript, Tailwind CSS, and shadcn/ui components.
* [ ] **Contract Workspace:**
  * Contract list & overview card.
  * PDF drag-and-drop upload zone with instant version badge (`v1`, `v2`).
  * Page-by-page clause browser.
* [ ] **Compliance Requirements Panel:**
  * Checklist of rules (e.g. 30-Day Notice, Liability Cap).
  * Finding status badges (`SATISFIED`, `NEEDS_REVIEW`, `NOT_SATISFIED`).
  * Evidence drawer showing extracted quotes, confidence scores, and Reviewer override buttons.
* [ ] **Side-by-Side Visual Diff Viewer:**
  * Compares v1 vs v2 side by side.
  * Green highlights for added text, red strikethrough for deleted text.
  * Impact alert pill: *"Section 3 changed -> Flags 30-Day Notice requirement"*.
* [ ] **Interactive Audit Timeline:**
  * Chronological visual feed showing who uploaded, evaluated, modified, or approved each version.

---

## 5. Quickstart: How to Run and Test Right Now

### Prerequisites
* Python 3.10+ (tested on Python 3.14)
* A free [Supabase](https://supabase.com) project
* A free [Google Gemini API Key](https://aistudio.google.com/)

### 1. Configure Environment (`.env`)
In `clausetrace/backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
STORAGE_LOCAL_DIR=./storage/contracts
```
*(Note: If your database password contains an `@`, URL-encode it as `%40`)*.

### 2. Run Database Schema in Supabase
Copy the SQL from `clausetrace/backend/scripts/init_schema_and_rls.sql`, paste it into the **Supabase SQL Editor**, and click **Run**.

### 3. Verify Connection
```powershell
.\clausetrace\backend\.venv\Scripts\python .\clausetrace\backend\test_setup.py
```

### 4. Run the Automated End-to-End Test Pipeline
```powershell
.\clausetrace\backend\.venv\Scripts\python .\clausetrace\backend\test_pipeline.py
```
*This uploads v1, evaluates the 30-day notice, approves v1, uploads v2 (60-day notice), runs the diff engine, flags the requirement for review, and prints the audit trail in ~10 seconds!*

### 5. Start the FastAPI Development Server (Swagger UI)
```powershell
.\clausetrace\backend\.venv\Scripts\uvicorn main:app --reload --app-dir clausetrace/backend
```
Open your browser to:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)** to test all endpoints interactively.

---

## 6. Project Structure

```
SKILL_LAB_SEM3/
├── README.md                          # Master project documentation
└── clausetrace/
    ├── README.md                      # ClauseTrace documentation
    ├── .gitignore                     # Git protection for .env and storage
    └── backend/
        ├── .env                       # Local secrets (Database & Gemini Key)
        ├── requirements.txt           # Minimal 8 backend dependencies
        ├── main.py                    # FastAPI entrypoint & router registry
        ├── test_setup.py              # Automated connection diagnostic script
        ├── test_pipeline.py           # End-to-end integration test runner
        ├── create_sample_contracts.py # Script generating sample PDFs
        ├── sample_contracts/          # Realistic v1 & v2 sample PDFs
        │   ├── v1_vendor_agreement.pdf
        │   └── v2_vendor_agreement.pdf
        ├── storage/contracts/         # Local secure document vault
        ├── scripts/
        │   └── init_schema_and_rls.sql# Clean 6-table DDL & triggers
        └── app/
            ├── core/                  # Database & config settings
            ├── models/                # SQLAlchemy 2.x declarative models
            ├── schemas/               # Pydantic request/response schemas
            ├── services/              # PyMuPDF extractor, FTS+Gemini search, difflib
            └── api/                   # REST API routes (contracts, diff, approvals, audit)
```

