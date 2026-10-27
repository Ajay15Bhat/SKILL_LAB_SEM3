# Product Requirements Document (PRD)
## ClauseTrace — Evidence-Grounded Contract Change Impact & Obligation Tracking Platform

| Document Attribute | Details |
| :--- | :--- |
| **Product Name** | **ClauseTrace** |
| **Document Version** | 1.0.0 (Production Release) |
| **Target Release Date**| October 2026 |
| **Author** | Senior Full-Stack & Systems Architecture Team |
| **Status** | Approved / Implemented |
| **Target Audience** | Enterprise Legal Operations, Procurement, Compliance, Security Engineering |

---

## 1. Executive Summary & Vision

### 1.1 The Problem
When enterprise vendors update Master Service Agreements (MSAs), Statements of Work (SOWs), or Data Processing Agreements (DPAs), legal and procurement teams face critical blind spots:
1. **Syntactic vs. Operational Change**: Standard document comparison tools (like Microsoft Word Track Changes or generic diff engines) highlight words added or deleted, but fail to explain whether an altered phrase breaks a corporate compliance rule, changes liability exposure, or invalidates an existing risk approval.
2. **Silent Inheritance Vulnerability**: In traditional contract repositories, uploading an updated agreement often inherits the "Approved" status of its predecessor or replaces it in-place, silently exposing the enterprise to unfavorable notice periods, reduced service levels, or increased liability caps.
3. **Fragmented Evidence & Hallucinations**: Traditional AI contract tools frequently summarize documents without providing exact clause provenance (page numbers, character offsets, verbatim quotes), making citations difficult to verify and introducing legal risk.
4. **Abandoned Obligations**: Post-signature deliverables, reporting requirements, and SLA penalties are buried in contract text and lost across siloed email threads, resulting in unmonitored compliance deadlines and financial penalties.

### 1.2 The ClauseTrace Solution
**ClauseTrace** is an evidence-grounded contract change impact and obligation management platform. It transforms static contract revisions into structured, source-linked entities connected by an immutable lineage:

$$\text{Contract} \longrightarrow \text{Version} \longrightarrow \text{Clause} \longrightarrow \text{Requirement} \longrightarrow \text{Finding} \longrightarrow \text{Approval} \longrightarrow \text{Obligation}$$

Every finding, review, and approval is cryptographically pinned to the exact document version to which it applies. When a new contract revision is uploaded, it **never silently inherits approval** from an earlier version; instead, ClauseTrace isolates the changes, flags affected compliance requirements, and mandates explicit, justified human review.

---

## 2. Core Invariants & Product Principles

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

## 4. End-to-End Primary Acceptance Workflow (The Golden Path)

The system must flawlessly execute and verify the following 12-step sequence:

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

## 5. Functional Module Specifications

### Module A — Multi-Tenant Authentication & Identity
* **Authentication**: Supabase Auth / Bearer token authentication with session impersonation for testing (`X-User-Email`).
* **Tenant Isolation**: Every database record is partitioned by `organization_id`. Cross-tenant queries are blocked at the ORM and API layers with HTTP 403 / 404 responses.
* **Role Verification**: Middleware dependency `require_roles(...)` validates permissions prior to executing mutations.

### Module B — Document Upload & Immutable Versioning
* **Supported Formats**: `.pdf`, `.docx`, `.txt`.
* **Upload Validation**: File size limit (maximum 25 MB), MIME type inspection, file signature checking, and duplicate SHA-256 detection within the same organization (HTTP 409 Conflict).
* **Versioning Semantics**: Version numbers strictly increment monotonically per contract ($v_1, v_2, \dots, v_n$). File binary is stored in private storage (`storage/contracts/{org_id}/{version_id}_{filename}`).

### Module C — Asynchronous Processing & Text Extraction
* **Job States**: `QUEUED` $\rightarrow$ `PROCESSING` $\rightarrow$ `SUCCEEDED` / `FAILED` / `RETRYING`.
* **Worker Execution**: Dedicated background worker claims jobs atomically via `SELECT ... FOR UPDATE` semantics with bounded retries.
* **Extraction Engine**:
  * **PDF**: PyMuPDF extracts text per physical page, capturing page indices ($1, 2, \dots$).
  * **DOCX**: python-docx extracts paragraph blocks, retaining document flow.
  * **Chunking**: Preserves structural boundaries, character spans (`char_start`, `char_end`), and section headings (e.g., "Section 14: Termination").

### Module D — Compliance Requirements & Deterministic Findings
* **Predefined & Custom Categories**:
  1. Termination & Notice Periods
  2. Payment Terms & Penalties
  3. Contract Renewal & Auto-Extension
  4. Confidentiality & Non-Disclosure
  5. Service-Level Agreements (SLAs) & Reporting
  6. Limitation of Liability & Indemnification
* **Deterministic Evaluation Engine**:
  * Token-based semantic search ranks relevant clauses within the target version.
  * Numerical and keyword regex parsers extract durations (e.g., parsing both `"30"` and `"thirty"`), monetary limits, and renewal windows.
  * Status outputs: `SATISFIED`, `PARTIALLY_SATISFIED`, `NOT_SATISFIED`, `NOT_FOUND`, `NEEDS_REVIEW`.
* **Evidence Grounding**: No finding is persisted without an explicit link to `clause_id`, `version_id`, `page_number`, and verbatim citation excerpt.
* **Human-in-the-Loop Override**: Reviewers can override any finding, supplying a new status and a required `review_notes` justification.

### Module E — Version Comparison & Impact Analysis
* **Clause Alignment**: Identifies corresponding sections between Version $A$ and Version $B$ using fuzzy title and content similarity.
* **Word-Level Textual Diffing**: Computes token-level deletions and insertions (`diff_tokens`) rendered as red strikethroughs and green additions.
* **Impact Flagging**: Automatically cross-references changed clauses against active compliance requirements, tagging impacted requirements with a warning: `"Needs Review: Impacted by revisions in Section X"`.

### Module F — Cryptographic Approvals
* **State Machine**: `DRAFT` $\rightarrow$ `UNDER_REVIEW` $\rightarrow$ `APPROVED` or `REJECTED`.
* **Approval Payload**:
  $$\text{Signature} = \text{SHA256}(\text{version\_id} \,\|\, \text{version\_sha256} \,\|\, \text{approver\_id} \,\|\, \text{timestamp})$$
* **Non-Inheritance Assurance**: Activating or approving Version $N$ has strictly zero mutation effect on Version $N+1$.

### Module G — Operational Obligations & SLA Tracking
* **Obligation Metadata**: Title, description, responsible party (`VENDOR`, `CUSTOMER`, `MUTUAL`), due date, recurrence frequency (`ONE_OFF`, `MONTHLY`, `QUARTERLY`, `ANNUALLY`), and status (`PENDING`, `COMPLETED`, `OVERDUE`).
* **Dynamic Overdue Calculation**: Any obligation with status `PENDING` whose `due_date < CURRENT_TIMESTAMP` dynamically resolves to `OVERDUE`.

### Module H — Append-Only Audit Ledger
* **Audit Trail**: Logs all system events with `actor_id`, `action`, `resource_type`, `resource_id`, `timestamp`, and `details_json`.
* **Supported Actions**: `UPLOAD`, `PROCESSING_COMPLETE`, `EVALUATION`, `COMPARISON`, `REVIEW_CONFIRM`, `REVIEW_OVERRIDE`, `APPROVAL`, `REJECTION`.

---

## 6. Frontend Information Architecture

The user interface is implemented as a 7-screen Next.js 14 application:

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

* **Global Top Navbar**: Contains live identity display and an instant **Role Switcher** dropdown (`Analyst`, `Reviewer`, `Admin`, `Auditor`) to evaluate RBAC behaviors without re-authenticating.

---

## 7. Data Model & Entity Relationships

```
 ┌─────────────────┐       1:N       ┌────────────────────────┐
 │  Organization   ├────────────────►│          User          │
 └────────┬────────┘                 └────────────────────────┘
          │ 1:N
          ▼
 ┌─────────────────┐       1:N       ┌────────────────────────┐
 │    Contract     ├────────────────►│    ContractVersion     │
 └────────┬────────┘                 └───────────┬────────────┘
          │                                      │ 1:N
          │ 1:N                                  ├────────────────────────┐
          ▼                                      ▼                        ▼
 ┌─────────────────┐                 ┌───────────────────────┐ ┌──────────────────────┐
 │   Requirement   │                 │        Clause         │ │     VersionDiff      │
 └────────┬────────┘                 └───────────┬───────────┘ └──────────────────────┘
          │                                      │
          └──────────────┬───────────────────────┘
                         ▼
             ┌───────────────────────┐
             │        Finding        │◄──── (Evidence Citation + Review Notes)
             └───────────────────────┘
                         ▲
                         │ 1:N
             ┌───────────┴───────────┐       1:1       ┌──────────────────────┐
             │    ContractVersion    ├────────────────►│       Approval       │
             └───────────┬───────────┘                 └──────────────────────┘
                         │ 1:N
                         ▼
             ┌───────────────────────┐
             │      Obligation       │
             └───────────────────────┘
```

---

## 8. Non-Functional & Operational Requirements

| Category | Requirement | Specification |
| :--- | :--- | :--- |
| **Performance** | API Response Latency | $< 250\text{ ms}$ for standard CRUD endpoints; $< 1\text{ s}$ for full contract text search. |
| **Throughput** | Extraction & Chunking | $< 5\text{ s}$ for standard 20-page PDF/DOCX agreements. |
| **Security** | Document Storage | Storage files saved in non-public directories accessible only via authenticated endpoints. |
| **Data Integrity** | Cryptographic Checksum | SHA-256 computed immediately on raw byte streams before disk writes. |
| **Auditability** | Immutability | Audit logs are strictly append-only; `DELETE` or `UPDATE` operations on audit tables are prohibited. |
| **Resilience** | Worker Job Recovery | Jobs in `PROCESSING` state for $> 15\text{ minutes}$ are transitioned to `RETRYING` or `FAILED`. |

---

## 9. Verification & Quality Gates

The product implementation is validated against the automated test suite in [`clausetrace/backend/tests/test_clausetrace.py`](file:///c:/Users/LENOVO/Desktop/am/skilllab/clausetrace/backend/tests/test_clausetrace.py):

* [x] **Primary Acceptance Workflow**: Upload v1 $\rightarrow$ Extract clauses with page numbers $\rightarrow$ Evaluate 30-day notice requirement (`SATISFIED`) $\rightarrow$ Sign & approve v1 $\rightarrow$ Upload v2 (60-day notice) $\rightarrow$ Verify v2 enters in `DRAFT` while v1 approval remains sealed $\rightarrow$ Run diff to detect clause change $\rightarrow$ Flag requirement $\rightarrow$ Run v2 evaluation (`NOT_SATISFIED`) $\rightarrow$ Human reviewer override with rationale $\rightarrow$ Inspect complete audit trail.
* [x] **File Validation**: Reject non-whitelisted extensions (HTTP 415) and empty files (HTTP 422).
* [x] **Tenant & Security Invariants**: Prevent Analysts and Auditors from approving versions (HTTP 403); prevent cross-organization access (HTTP 403/404); reject duplicate SHA-256 uploads (HTTP 409).
* [x] **Obligation Overdue Mechanics**: Automatically mark past due dates as `OVERDUE`; record completion timestamps.
* [x] **Aggregated Metrics**: Live computation of compliance rates, active contracts, and approval percentages.
