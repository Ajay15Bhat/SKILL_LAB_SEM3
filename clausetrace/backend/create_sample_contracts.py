"""
Generates 2 realistic sample contract PDFs for ClauseTrace demonstrations:
- v1_vendor_agreement.pdf (30-day notice clause)
- v2_vendor_agreement.pdf (Changed to 60-day notice with penalty fee)
"""

from pathlib import Path
import pymupdf as fitz


def create_sample_contracts():
    out_dir = Path(__file__).parent / "sample_contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # CONTRACT VERSION 1 (30-Day Notice)
    # ---------------------------------------------------------
    v1_doc = fitz.open()
    v1_page = v1_doc.new_page(width=595, height=842)  # Standard A4

    v1_text = """MASTER SERVICES AGREEMENT (VERSION 1.0)
BETWEEN CLOUDSCALE CORP AND DATAVAULT INC

Section 1: Scope of Services
CloudScale Corp agrees to provide managed cloud infrastructure and automated backup storage to DataVault Inc in accordance with Exhibit A.

Section 2: Payment and Invoicing
All invoices shall be payable in full within thirty (30) calendar days from the date of electronic transmission. Late payments shall incur a monthly interest charge of 1.5%.

Section 3: Termination for Convenience
Either party may terminate this Agreement without cause at any time by providing at least thirty (30) days prior written notice to the other party. Upon termination, CloudScale shall assist in migrating client data without additional fees.

Section 4: Limitation of Liability
Neither party shall be liable for any indirect, incidental, special, or consequential damages. The aggregate liability of either party under this Agreement shall not exceed the total fees paid in the preceding twelve (12) months.

Section 5: Governing Law and Dispute Resolution
This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of law principles.
"""
    v1_page.insert_textbox(fitz.Rect(50, 50, 545, 780), v1_text, fontsize=11, fontname="helv")
    v1_path = out_dir / "v1_vendor_agreement.pdf"
    v1_doc.save(str(v1_path))
    v1_doc.close()
    print(f"[OK] Generated: {v1_path}")

    # ---------------------------------------------------------
    # CONTRACT VERSION 2 (60-Day Notice + Termination Penalty)
    # ---------------------------------------------------------
    v2_doc = fitz.open()
    v2_page = v2_doc.new_page(width=595, height=842)  # Standard A4

    v2_text = """MASTER SERVICES AGREEMENT (VERSION 2.0)
BETWEEN CLOUDSCALE CORP AND DATAVAULT INC

Section 1: Scope of Services
CloudScale Corp agrees to provide managed cloud infrastructure, automated backup storage, and enterprise cybersecurity monitoring to DataVault Inc in accordance with Exhibit A.

Section 2: Payment and Invoicing
All invoices shall be payable in full within forty-five (45) calendar days from the date of electronic transmission. Late payments shall incur a monthly interest charge of 2.0%.

Section 3: Termination for Convenience
Either party may terminate this Agreement without cause only by providing at least sixty (60) days prior written notice to the other party, subject to a mandatory early termination fee equal to two (2) months of average recurring charges.

Section 4: Limitation of Liability
Neither party shall be liable for any indirect, incidental, special, or consequential damages. The aggregate liability of either party under this Agreement shall not exceed the total fees paid in the preceding six (6) months.

Section 5: Governing Law and Dispute Resolution
This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of law principles.
"""
    v2_page.insert_textbox(fitz.Rect(50, 50, 545, 780), v2_text, fontsize=11, fontname="helv")
    v2_path = out_dir / "v2_vendor_agreement.pdf"
    v2_doc.save(str(v2_path))
    v2_doc.close()
    print(f"[OK] Generated: {v2_path}")


if __name__ == "__main__":
    create_sample_contracts()

