# ClauseTrace — Complete System Guide & Master Documentation
### Evidence-Grounded Contract Change Impact & Obligation Tracking Platform

[![Tests](https://img.shields.io/badge/Tests-5%20Passing%20(100%25)-success)](clausetrace/backend/tests/test_clausetrace.py)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.13-blue)](clausetrace/backend)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2014%20%7C%20React%20%7C%20Tailwind-black)](clausetrace/frontend)
[![Database](https://img.shields.io/badge/Database-SQLite%20%2F%20Supabase%20Postgres-336791)](clausetrace/backend/app/models)

---

## 1. Executive Summary & Product Vision

### The Problem
When vendors release new versions of Master Service Agreements (MSAs), Statements of Work (SOWs), or Service Level Agreements (SLAs), enterprise legal and procurement teams face critical blind spots:
1. **Syntactic vs. Operational Change:** Standard word-comparison diff tools highlight added and deleted text, but fail to explain whether an altered phrase breaks a corporate compliance rule, changes liability exposure, or invalidates a prior risk approval.
2. **Silent Inheritance Vulnerability:** In traditional document repositories, uploading an updated agreement often inherits the "Approved" status of its predecessor or replaces it in-place, silently exposing the enterprise to unfavorable notice periods, reduced service levels, or increased liability caps.
3. **Fragmented Evidence & Hallucinations:** Traditional AI contract tools frequently summarize documents without providing exact clause provenance (page numbers, character offsets, verbatim quotes), making citations difficult to verify and introducing legal risk.
4. **Abandoned Obligations:** Post-signature deliverables, reporting requirements, and SLA penalties are buried in contract text and lost across siloed email threads, resulting in unmonitored compliance deadlines and financial penalties.

### The Solution
**ClauseTrace** is an evidence-grounded contract change impact and obligation management platform. It transforms static contract revisions into structured, source-linked entities connected by an immutable lineage:

$$\text{Contract} \longrightarrow \text{Version} \longrightarrow \text{Clause} \longrightarrow \text{Requirement} \longrightarrow \text{Finding} \longrightarrow \text{Approval} \longrightarrow \text{Obligation}$$

Every finding, review, and approval is cryptographically pinned to the exact document version to which it applies. When a new contract revision is uploaded, it **never silently inherits approval** from an earlier version; instead, ClauseTrace isolates the changes, flags affected compliance requirements, and mandates explicit, justified human review.

---

## 2. Core System Invariants

ClauseTrace enforces the following system invariants:

1. **Strict Version Immutability**:
   - Every document upload generates an immutable `ContractVersion` record tagged with a cryptographic SHA-256 checksum.
   - Historical text chunks, page offsets, and metadata are never mutated, overwritten, or deleted upon subsequent uploads.
2. **Zero Silent Inheritance of Approvals**:
   - Revisions (e.g., v2, v3) always enter the system strictly in `DRAFT` status.
   - Prior version approvals remain sealed in the historical audit ledger. A new version must undergo independent review and explicit sign-off.
3. **Evidence-Grounded Citations (Zero-Hallucination Baseline)**:
   - Every requirement evaluation citation references exact source coordinates: `version_id`, `chunk_id`, `page_number`, and character start/end offsets.
   - Deterministic rule evaluation operates independently of external LLMs, ensuring 100% offline availability and repeatable outcomes.
4. **Dual-Record Review Provenance**:
   - Automated recommendations (`SATISFIED`, `NOT_SATISFIED`, `NEEDS_REVIEW`) are preserved permanently alongside any human overrides.
   - Any modification by a human reviewer requires an authenticated identity, timestamp, and mandatory written justification.
5. **Cryptographic Signatures for Approvals**:
   - Version approvals compute a SHA-256 seal across the `version_id`, `file_sha256`, `approver_id`, and `approved_at` timestamp.
6. **Multi-Tenant Isolation**:
   - Complete logical and database isolation per organization across contracts, versions, clauses, requirements, findings, obligations, and audit events.

---

## 3. User Personas & Permissions Matrix

| Persona | Role Key | Primary Responsibilities | Permissions & Capabilities |
| :--- | :--- | :--- | :--- |
| **Legal Operations Analyst** | `ANALYST` | Uploads vendor contracts, triggers extraction, defines corporate review requirements, and reviews automated findings. | Upload documents, trigger analysis, create requirements, propose obligations. *Cannot sign or approve contract versions.* |
| **Senior Counsel / Reviewer** | `REVIEWER` | Inspects evidence citations, overrides or confirms automated findings, and grants formal version approval. | All Analyst permissions + human override confirmation, version rejection, cryptographic version approval. |
| **Director of Procurement** | `ADMIN` | Manages corporate compliance policies, oversees organization members, and exercises executive approval authority. | Full system access: manage users, create/edit global requirements, force re-evaluations, grant version approvals. |
| **Compliance Auditor** | `AUDITOR` | Inspects historical versions, reviews diff logs, verifies approval chains, and exports regulatory proof. | Read-only inspection across all contracts, versions, diffs, findings, obligations, and audit timelines. *Cannot mutate data.* |

---

## 4. End-to-End Primary Acceptance Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Legal Analyst
    actor System as ClauseTrace Engine
    actor Reviewer as Senior Reviewer

    Analyst->>System: 1. Upload Contract v1 (PDF/DOCX)
    System->>System: 2. Store privately, compute SHA-256, create Version 1 (DRAFT), enqueue Job
    System->>System: 3. Worker extracts text, sections, and page provenance (p. 1, offsets)
    Analyst->>System: 4. Define Requirement: "Termination notice period must not exceed 30 days"
    System->>System: 5. Search text, extract "thirty (30) days", generate Finding -> SATISFIED (Page 1)
    Reviewer->>System: 6. Inspect citation, approve Version 1 with cryptographic SHA-256 seal
    Analyst->>System: 7. Upload Contract v2 (increases notice period to 60 days)
    System->>System: 8. Create Version 2 in DRAFT; Version 1 approval remains sealed (No silent inheritance)
    System->>System: 9. Compare v1 vs v2 -> word-level diff highlights "30 days" -> "60 days"; flag Notice Requirement
    System->>System: 10. Run analysis on v2 -> evaluates 60 days against 30-day max -> NOT_SATISFIED
    Reviewer->>System: 11. Inspect side-by-side diff & citation; record decision with written justification
    System->>System: 12. Append-only ledger updates: upload, extraction, comparison, finding, and approval events
```

---

## 5. Technology Stack & System Architecture

```
                    ┌─────────────────────────────────────────┐
                    │        Next.js 14 Web Frontend          │
                    │   (Contracts, Diffs, Reviews, Audits)   │
                    └────────────────────┬────────────────────┘
                                         │ REST API / JSON
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │           FastAPI Monolith              │
                    │  (Auth, Upload, Evaluation, Approvals)  │
                    └───────────┬─────────────────┬───────────┘
                                │                 │
                       Database │                 │ Background Job
                                ▼                 ▼
               ┌───────────────────────┐   ┌─────────────────────────┐
               │  PostgreSQL / SQLite  │   │  Background Job Worker  │
               │  (Tenants, Versions,  │◄──┤  (Text extraction,      │
               │   Clauses, Audits)    │   │   chunking, provenance) │
               └───────────────────────┘   └─────────────────────────┘
```

* **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0 Async, Pydantic v2.
* **Extraction:** PyMuPDF (`fitz`) for PDF page extraction, `python-docx` for Word documents.
* **Storage & Queue:** Private local/S3-compatible bucket, database-backed background task table with worker daemon.
* **Database:** SQLite (local development) / Supabase PostgreSQL (production) with cross-compatible `sqlalchemy.Uuid(as_uuid=True)`.
* **Frontend:** Next.js 14 (App Router), React 18, Tailwind CSS, Lucide Icons.

---

## 6. How to Run the Application

### Prerequisites
* Python 3.12+ or 3.13
* Node.js 18+ and npm

### Terminal 1: Start Backend API Server
```powershell
cd c:\Users\LENOVO\Desktop\am\skilllab\clausetrace\backend

# Install python dependencies:
pip install fastapi uvicorn "sqlalchemy<2.1.0" greenlet aiosqlite pydantic pydantic-settings pymupdf python-docx pytest pytest-asyncio httpx

# Start FastAPI server on port 8000:
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
* **API Documentation:** `http://127.0.0.1:8000/docs`
* **Metrics:** `http://127.0.0.1:8000/api/v1/overview/metrics`

### Terminal 2: Start Background Task Worker
```powershell
cd c:\Users\LENOVO\Desktop\am\skilllab\clausetrace\backend

# Run the background worker daemon:
python -m app.worker
```

### Terminal 3: Start Next.js Frontend
```powershell
cd c:\Users\LENOVO\Desktop\am\skilllab\clausetrace\frontend

# Launch Next.js dev server on port 3000:
npm run dev
```
* **Frontend UI:** `http://localhost:3000`

### Run Automated Tests
```powershell
cd c:\Users\LENOVO\Desktop\am\skilllab\clausetrace\backend
pytest tests/test_clausetrace.py -v
```
*(All 5 test suites pass with 100% green status).*

---

## 7. Demo Accounts & Seeded Personas

The database automatically initializes a demo organization (**Acme Enterprise Corp**) with 4 test credentials:

| Role | Email | Capabilities |
| :--- | :--- | :--- |
| **Analyst** | `analyst@clausetrace.io` | Upload contracts, trigger extraction, define requirements, propose obligations |
| **Reviewer** | `reviewer@clausetrace.io` | Inspect citations, confirm/override findings, execute cryptographic approvals |
| **Admin** | `admin@clausetrace.io` | Full system access, policy management, approvals |
| **Auditor** | `auditor@clausetrace.io` | Read-only inspection of diffs, clauses, and the immutable audit timeline |

*Use the **Role Switcher** dropdown in the top navbar to toggle between these personas instantly without re-logging in.*

---

## 8. Frontend Navigation & Screen Map

```
clausetrace/frontend/src/app/
├── page.tsx                     # 1. Overview Dashboard (KPIs, Active Contracts, Audit Feed)
├── contracts/
│   ├── page.tsx                 # 2a. Contract Directory & Filters
│   └── [id]/page.tsx            # 2b. Contract Detail (Revisions, Clauses, Findings, Sign-off)
├── upload/page.tsx              # 3. Document Uploader & Processing Job Monitor
├── reviews/page.tsx             # 4. Requirements & Finding Review / Human Override Modal
├── compare/page.tsx             # 5. Side-by-Side Version Diff & Impact Warning Inspector
├── obligations/page.tsx         # 6. Obligations & SLA Tracker with Overdue Highlighting
└── audit/page.tsx               # 7. Immutable Audit Timeline & Verification Log
```

---

## 9. REST API Reference

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/contracts` | Create contract & upload Version 1 | Analyst, Admin |
| `GET` | `/api/v1/contracts` | List all organization contracts | All |
| `GET` | `/api/v1/contracts/{id}` | Get contract details & revision tabs | All |
| `POST` | `/api/v1/contracts/{id}/versions` | Upload new revision (e.g. v2) | Analyst, Admin |
| `GET` | `/api/v1/versions/{id}/clauses` | Inspect extracted clauses & page numbers | All |
| `POST` | `/api/v1/versions/{id}/analyze` | Trigger deterministic compliance evaluation | Analyst, Reviewer, Admin |
| `POST` | `/api/v1/versions/{v1}/compare/{v2}` | Compute word-level diff & impact flags | All |
| `POST` | `/api/v1/versions/{id}/approvals` | Sign and approve contract version | **Reviewer, Admin only** |
| `PATCH` | `/api/v1/findings/{id}` | Human reviewer override with rationale | Reviewer, Admin |
| `GET` | `/api/v1/obligations` | List obligations with overdue calculations | All |
| `GET` | `/api/v1/audit` | Query append-only audit trail | All |
| `GET` | `/api/v1/overview/metrics` | Dashboard statistics & compliance metrics | All |
