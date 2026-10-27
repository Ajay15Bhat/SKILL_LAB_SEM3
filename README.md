# ClauseTrace
### Evidence-Grounded Contract Change Impact & Obligation Tracking Platform

[![Tests](https://img.shields.io/badge/Tests-5%20Passing%20(100%25)-success)](clausetrace/backend/tests/test_clausetrace.py)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.13-blue)](clausetrace/backend)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2014%20%7C%20React%20%7C%20Tailwind-black)](clausetrace/frontend)
[![Database](https://img.shields.io/badge/Database-SQLite%20%2F%20Supabase%20Postgres-336791)](clausetrace/backend/app/models)

ClauseTrace is an enterprise-grade contract review and change-impact management system. It allows organizations to upload successive revisions of vendor service agreements, define compliance requirements, inspect extracted clauses with page-level provenance, compare revisions with word-level textual diffing, track operational obligations with overdue warnings, and manage approval state transitions with cryptographic signatures.

---

## Key Invariants & Features

1. **Strict Version Immutability**:
   - Each upload creates a discrete immutable `ContractVersion` record with a SHA-256 fingerprint.
   - Text chunks and clauses maintain exact page number provenance (`page_number`, `char_start`, `char_end`).
   - Old versions and their extractions are never overwritten or mutated.

2. **No Silent Inheritance of Approvals**:
   - When a new revision (e.g., v2) is uploaded, it is initialized strictly in `DRAFT` status.
   - Approval of v1 remains sealed in the historical audit ledger.
   - Approvals are cryptographically bound to the specific version's SHA-256 hash.

3. **Requirement Impact Detection**:
   - Compares successive revisions using sequence matching and word-level diffing.
   - Automatically detects affected requirements when relevant clauses are altered.
   - Evaluates compliance deterministically (e.g., notice periods, payment terms, liability caps) and citations back to original clauses.

4. **Human Review & Justification**:
   - Automated recommendations (`SATISFIED`, `NOT_SATISFIED`, `NEEDS_REVIEW`) can be confirmed or overridden by human reviewers with mandatory justification logs.

5. **Operational Obligations & SLA Tracking**:
   - Tracks contractual deliverables, reporting cadences, and payment schedules.
   - Dynamically flags overdue items based on due dates.

6. **Role-Based Access Control & Multi-Tenancy**:
   - Full organization isolation across all queries.
   - 4 strict roles: `Admin`, `Analyst`, `Reviewer`, and `Auditor`.

---

## Architecture

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

---

## Directory Structure

```
skilllab/
├── README.md
├── clausetrace/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/v1/          # REST Endpoints (contracts, versions, diffs, etc.)
│   │   │   ├── core/            # Config, DB connection, Security & Tenancy
│   │   │   ├── models/          # SQLAlchemy 2.0 domain entities
│   │   │   ├── schemas/         # Pydantic request/response schemas
│   │   │   ├── services/        # Storage, Extractor, Diff, Evaluator, Approval
│   │   │   ├── worker.py        # Background task processor
│   │   │   └── main.py          # FastAPI application entrypoint
│   │   └── tests/
│   │       └── test_clausetrace.py # 100% Passing End-to-End Test Suite
│   └── frontend/
│       ├── src/
│       │   ├── app/             # Next.js App Router (7 complete views)
│       │   └── components/      # UI components & Role Switcher
│       └── package.json
```

---

## Quickstart & Local Setup

### Prerequisites
- Python 3.12+ (or 3.13)
- Node.js 18+ and npm

### 1. Backend Setup

```bash
cd clausetrace/backend

# Install python dependencies
pip install fastapi uvicorn "sqlalchemy<2.1.0" greenlet aiosqlite pydantic pydantic-settings pymupdf python-docx pytest pytest-asyncio httpx

# Run the backend server (automatically initializes demo DB and seeds tenant)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:
- **API Base**: `http://127.0.0.1:8000/api/v1`
- **Swagger Interactive Docs**: `http://127.0.0.1:8000/docs`
- **OpenAPI JSON**: `http://127.0.0.1:8000/openapi.json`

### 2. Run the Background Worker

In a separate terminal:
```bash
cd clausetrace/backend
python -m app.worker
```

### 3. Run the Backend Automated Test Suite

```bash
cd clausetrace/backend
pytest tests/test_clausetrace.py -v
```
*All 5 tests verify the full end-to-end acceptance flow, invalid upload protections, tenancy isolation, obligation overdue mechanics, and metrics aggregation.*

### 4. Frontend Setup

In a separate terminal:
```bash
cd clausetrace/frontend

# Dependencies are already installed; start development server:
npm run dev
```

Visit `http://localhost:3000` in your browser.

---

## Demo Credentials & Roles

ClauseTrace seeds a default demonstration organization (`Acme Enterprise Corp`) with four test accounts:

| Role | Email | Permissions |
|---|---|---|
| **Analyst** | `analyst@clausetrace.io` | Upload contracts, trigger extraction, analyze requirements, propose obligations |
| **Reviewer** | `reviewer@clausetrace.io` | Inspect evidence citations, override/confirm findings, sign & approve versions |
| **Admin** | `admin@clausetrace.io` | Full system governance, approvals, policy management |
| **Auditor** | `auditor@clausetrace.io` | Read-only inspection of evidence, diffs, and the immutable audit timeline |

The frontend includes an interactive **Role Switcher** in the top navigation bar to toggle between personas instantly.
