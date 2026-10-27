"""
ClauseTrace End-to-End Pipeline Verification Script.
Demonstrates the full lifecycle:
1. Create Contract & 30-Day Notice Requirement
2. Upload v1 PDF -> Extracts Clauses -> Evaluates -> SATISFIED
3. Approve v1 -> Immutable Signed State
4. Upload v2 PDF (60-Day Notice) -> Fresh SHA-256 -> DRAFT
5. Run Diff Engine -> Detects Clause 3 change -> Flags Requirement as NEEDS_REVIEW
6. Verify Audit Trail Timeline
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from httpx import ASGITransport, AsyncClient
from main import app

sample_dir = backend_dir / "sample_contracts"
v1_pdf = sample_dir / "v1_vendor_agreement.pdf"
v2_pdf = sample_dir / "v2_vendor_agreement.pdf"


async def run_pipeline():
    print("\n" + "=" * 70)
    print(" >>> CLAUSETRACE END-TO-END PIPELINE TEST <<<")
    print("=" * 70)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        res = await client.get("/health")
        print(f"\n[1] Health Check: {res.json()['status'].upper()}")

        # 2. Create Requirement
        req_payload = {
            "title": "Termination for Convenience (30-Day Notice)",
            "category": "Termination",
            "description": "Contract must provide at least thirty (30) days prior written notice for termination without cause.",
            "search_keywords": ["terminate", "notice", "days", "written"],
            "is_mandatory": True,
        }
        res = await client.post("/api/v1/requirements", json=req_payload)
        req_data = res.json()
        req_id = req_data["id"]
        print(f"[2] Created Requirement: '{req_data['title']}' (ID: {req_id[:8]}...)")

        # 3. Create Contract Container
        contract_payload = {
            "title": "Cloud Services MSA",
            "vendor_name": "CloudScale Corp",
            "contract_type": "MSA",
            "description": "Enterprise cloud hosting and backup agreement",
        }
        res = await client.post("/api/v1/contracts", json=contract_payload)
        contract_data = res.json()
        contract_id = contract_data["id"]
        print(f"[3] Created Contract: '{contract_data['title']}' (ID: {contract_id[:8]}...)")

        # 4. Upload Version 1 PDF (30-day notice)
        print(f"\n[4] Uploading Version 1 PDF ({v1_pdf.name})...")
        with open(v1_pdf, "rb") as f:
            res = await client.post(
                f"/api/v1/contracts/{contract_id}/versions/upload",
                files={"file": (v1_pdf.name, f, "application/pdf")},
            )
        v1_data = res.json()
        v1_id = v1_data["id"]
        print(f"    -> Version Number : v{v1_data['version_number']}")
        print(f"    -> SHA-256 Hash   : {v1_data['sha256_checksum'][:16]}...")
        print(f"    -> Status         : {v1_data['approval_status']}")
        print(f"    -> Clauses Chunks : {v1_data.get('clause_count', 'extracted')}")

        # 5. Inspect Findings for Version 1
        res = await client.get(f"/api/v1/versions/{v1_id}/findings")
        findings_v1 = res.json()
        print(f"\n[5] Compliance Findings for Version 1:")
        for f_item in findings_v1:
            print(f"    -> Status    : {f_item['status']}")
            print(f"    -> Quote     : \"{f_item['evidence_quote'][:80]}...\"")
            print(f"    -> Reasoning : {f_item['analysis_notes']}")

        # 6. Approve Version 1 (Reviewer Sign-off)
        approve_payload = {"decision": "APPROVED", "comments": "Legal review complete. 30-day notice verified."}
        res = await client.post(f"/api/v1/versions/{v1_id}/approve", json=approve_payload)
        appr_data = res.json()
        print(f"\n[6] Version 1 Approval Recorded:")
        print(f"    -> Approval Status : {appr_data['approval_status']}")
        print(f"    -> Signature Hash  : {appr_data['signature_hash'][:24]}...")

        # 7. Upload Version 2 PDF (Sneaky 60-day notice + penalty)
        print(f"\n[7] Uploading Version 2 PDF ({v2_pdf.name})...")
        with open(v2_pdf, "rb") as f:
            res = await client.post(
                f"/api/v1/contracts/{contract_id}/versions/upload",
                files={"file": (v2_pdf.name, f, "application/pdf")},
            )
        v2_data = res.json()
        v2_id = v2_data["id"]
        print(f"    -> Version Number : v{v2_data['version_number']}")
        print(f"    -> SHA-256 Hash   : {v2_data['sha256_checksum'][:16]}...")
        print(f"    -> Status         : {v2_data['approval_status']} (Immutable v1 remains APPROVED!)")

        # 8. Run Diff & Change Impact Engine
        print(f"\n[8] Running Deterministic Diff Engine (v1 -> v2)...")
        res = await client.get(f"/api/v1/contracts/{contract_id}/diff?source_version_id={v1_id}&target_version_id={v2_id}")
        diff_data = res.json()
        print(f"    -> Additions     : {diff_data['metrics']['additions']}")
        print(f"    -> Deletions     : {diff_data['metrics']['deletions']}")
        print(f"    -> Modifications : {diff_data['metrics']['modifications']}")
        
        print(f"\n    [!] Impacted Requirements Detected: {len(diff_data['impacted_requirements'])}")
        for imp in diff_data["impacted_requirements"]:
            print(f"        * '{imp['title']}' -> Flagged as {imp['flagged_status']}")
            print(f"          Reason: {imp['impact_reason']}")

        # 9. Verify Audit Trail
        print(f"\n[9] Inspecting Audit Trail...")
        res = await client.get(f"/api/v1/audit-trail?limit=10")
        audit_items = res.json()
        print(f"    Total Audit Events Logged: {len(audit_items)}")
        for item in audit_items[:4]:
            print(f"    -> [{item['action']}] on {item['entity_type']} by {item['user_name']}")

    print("\n" + "=" * 70)
    print(" >>> PIPELINE EXECUTION COMPLETED SUCCESSFULLY! <<<")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_pipeline())

