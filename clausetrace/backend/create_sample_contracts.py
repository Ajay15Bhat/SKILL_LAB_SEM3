"""
Generates enterprise-grade, beautifully formatted contract PDFs for ClauseTrace.
Includes visual styling:
- Professional header banner & metadata block
- Visual section titles with dividers
- Signature & execution blocks
- Version badges
- Plain text equivalents (.txt) for quick viewing inside VS Code
"""

from pathlib import Path
import pymupdf as fitz


def create_styled_pdf(
    file_path: Path,
    title: str,
    version_tag: str,
    effective_date: str,
    sections: list,
    highlight_section_idx: int = -1,
):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # Standard A4 (595 x 842 pt)

    # 1. Colors (RGB tuples 0.0 to 1.0)
    DARK_NAVY = (0.09, 0.14, 0.22)     # #172438
    PRIMARY_BLUE = (0.15, 0.39, 0.92)  # #2663eb
    TEXT_DARK = (0.12, 0.16, 0.22)     # #1f2937
    TEXT_MUTED = (0.39, 0.45, 0.55)    # #64748b
    BG_LIGHT = (0.96, 0.97, 0.99)      # #f8fafc
    BORDER_COLOR = (0.85, 0.88, 0.92)  # #d9e0ea
    ACCENT_WARN = (0.85, 0.25, 0.20)   # Reddish for modified sections

    # 2. Header Banner
    page.draw_rect(fitz.Rect(0, 0, 595, 80), color=DARK_NAVY, fill=DARK_NAVY)
    page.insert_text((45, 38), "CLAUSETRACE VERIFIED VENDOR AGREEMENT", fontsize=9, fontname="helv", color=(0.6, 0.75, 1.0))
    page.insert_text((45, 60), title, fontsize=15, fontname="hebo", color=(1.0, 1.0, 1.0))

    # Version Badge (Top Right)
    badge_rect = fitz.Rect(470, 25, 550, 55)
    page.draw_rect(badge_rect, color=PRIMARY_BLUE, fill=PRIMARY_BLUE)
    page.insert_text((485, 45), version_tag, fontsize=11, fontname="hebo", color=(1.0, 1.0, 1.0))

    # 3. Metadata Panel
    meta_rect = fitz.Rect(45, 95, 550, 150)
    page.draw_rect(meta_rect, color=BORDER_COLOR, fill=BG_LIGHT)
    page.draw_line(fitz.Point(297, 105), fitz.Point(297, 140), color=BORDER_COLOR, width=1)

    # Left Column
    page.insert_text((60, 115), "PARTIES:", fontsize=8, fontname="hebo", color=TEXT_MUTED)
    page.insert_text((60, 132), "CloudScale Corp (Vendor) & DataVault Inc (Customer)", fontsize=9, fontname="helv", color=TEXT_DARK)

    # Right Column
    page.insert_text((312, 115), "EFFECTIVE DATE & JURISDICTION:", fontsize=8, fontname="hebo", color=TEXT_MUTED)
    page.insert_text((312, 132), f"{effective_date} • State of Delaware", fontsize=9, fontname="helv", color=TEXT_DARK)

    # 4. Sections Body
    y = 175
    for idx, (sec_title, sec_body) in enumerate(sections):
        # Section Header with left accent bar
        is_highlighted = (idx == highlight_section_idx)
        bar_color = ACCENT_WARN if is_highlighted else PRIMARY_BLUE
        
        # Left colored accent line
        page.draw_line(fitz.Point(45, y - 2), fitz.Point(45, y + 12), color=bar_color, width=3)
        page.insert_text((55, y + 10), sec_title, fontsize=11, fontname="hebo", color=DARK_NAVY)
        y += 22

        # Section Text Block
        body_rect = fitz.Rect(55, y, 545, y + 75)
        text_color = (0.7, 0.1, 0.1) if is_highlighted else TEXT_DARK
        
        # Draw background highlight if altered
        if is_highlighted:
            bg_rect = fitz.Rect(50, y - 4, 550, y + 54)
            page.draw_rect(bg_rect, color=(0.95, 0.8, 0.8), fill=(0.99, 0.94, 0.94))

        page.insert_textbox(body_rect, sec_body, fontsize=9.5, fontname="helv", color=text_color)
        y += 62

        # Separator line
        page.draw_line(fitz.Point(45, y), fitz.Point(550, y), color=BORDER_COLOR, width=0.5)
        y += 18

    # 5. Execution & Signatures Block
    sig_box_y = 665
    page.draw_rect(fitz.Rect(45, sig_box_y, 550, sig_box_y + 115), color=BORDER_COLOR, fill=BG_LIGHT)
    page.insert_text((60, sig_box_y + 20), "AUTHORIZED EXECUTION SIGNATURES", fontsize=8, fontname="hebo", color=TEXT_MUTED)
    
    # Vendor signature line
    page.draw_line(fitz.Point(60, sig_box_y + 75), fitz.Point(260, sig_box_y + 75), color=TEXT_MUTED, width=1)
    page.insert_text((60, sig_box_y + 90), "CloudScale Corp Authorized Signatory", fontsize=8, fontname="helv", color=TEXT_DARK)
    page.insert_text((60, sig_box_y + 102), "Name: Marcus Vance, VP Sales", fontsize=7.5, fontname="helv", color=TEXT_MUTED)

    # Customer signature line
    page.draw_line(fitz.Point(320, sig_box_y + 75), fitz.Point(520, sig_box_y + 75), color=TEXT_MUTED, width=1)
    page.insert_text((320, sig_box_y + 90), "DataVault Inc Authorized Reviewer", fontsize=8, fontname="helv", color=TEXT_DARK)
    page.insert_text((320, sig_box_y + 102), "Name: Sarah Jenkins, General Counsel", fontsize=7.5, fontname="helv", color=TEXT_MUTED)

    # 6. Page Footer
    page.draw_line(fitz.Point(45, 805), fitz.Point(550, 805), color=BORDER_COLOR, width=0.5)
    page.insert_text((45, 822), "ClauseTrace Compliance Ledger • Strict Version Integrity Enforced", fontsize=7.5, fontname="helv", color=TEXT_MUTED)
    page.insert_text((515, 822), "Page 1 of 1", fontsize=7.5, fontname="helv", color=TEXT_MUTED)

    doc.save(str(file_path))
    doc.close()
    print(f"[OK] Generated Styled PDF: {file_path}")


def create_sample_contracts():
    out_dir = Path(__file__).parent / "sample_contracts"
    out_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # CONTRACT VERSION 1.0 (30-Day Notice)
    # =========================================================================
    v1_sections = [
        (
            "Section 1: Scope of Managed Cloud Services",
            "CloudScale Corp agrees to provide 99.9% uptime managed cloud infrastructure, automated incremental snapshot storage, and Tier-1 engineering support to DataVault Inc in accordance with Service Level Schedule A.",
        ),
        (
            "Section 2: Payment Terms and Billing Invoicing",
            "All invoices issued under this Agreement shall be due and payable within thirty (30) calendar days from the date of electronic transmission. Uncontested delinquent balances shall accrue interest at 1.5% per month.",
        ),
        (
            "Section 3: Termination for Convenience and Notice Period",
            "Either party may terminate this Agreement without cause at any time by providing at least thirty (30) days prior written notice to the other party. Upon delivery of such notice, CloudScale shall assist in migrating client data without additional penalty or termination fees.",
        ),
        (
            "Section 4: Limitation of Liability and Damages Cap",
            "Neither party shall be liable for indirect, incidental, special, or consequential damages. The aggregate liability of either party under this Agreement shall not exceed the total fees paid by Customer in the preceding twelve (12) months.",
        ),
        (
            "Section 5: Governing Law, Venue, and Dispute Resolution",
            "This Agreement shall be governed by and construed under the laws of the State of Delaware. Any dispute arising out of this Agreement shall be resolved through binding arbitration in Wilmington, Delaware.",
        ),
    ]

    v1_pdf_path = out_dir / "v1_vendor_agreement.pdf"
    create_styled_pdf(
        file_path=v1_pdf_path,
        title="MASTER SERVICES AGREEMENT",
        version_tag="VERSION 1.0",
        effective_date="January 15, 2026",
        sections=v1_sections,
    )

    # Plain text version for instant reading in VS Code
    v1_txt_path = out_dir / "v1_vendor_agreement.txt"
    with open(v1_txt_path, "w", encoding="utf-8") as f:
        f.write("=== MASTER SERVICES AGREEMENT (VERSION 1.0) ===\n\n")
        for title, body in v1_sections:
            f.write(f"{title}\n{body}\n\n")

    # =========================================================================
    # CONTRACT VERSION 2.0 (Altered to 60-Day Notice + Early Termination Fee)
    # =========================================================================
    v2_sections = [
        (
            "Section 1: Scope of Managed Cloud Services",
            "CloudScale Corp agrees to provide 99.9% uptime managed cloud infrastructure, automated incremental snapshot storage, enterprise cybersecurity monitoring, and Tier-1 support to DataVault Inc.",
        ),
        (
            "Section 2: Payment Terms and Billing Invoicing",
            "All invoices issued under this Agreement shall be due and payable within forty-five (45) calendar days from electronic transmission. Delinquent balances shall accrue interest at 2.0% per month.",
        ),
        (
            "Section 3: Termination for Convenience and Notice Period",
            "Either party may terminate this Agreement without cause only by providing at least sixty (60) days prior written notice to the other party, subject to a mandatory early termination fee equal to two (2) months of average recurring charges.",
        ),
        (
            "Section 4: Limitation of Liability and Damages Cap",
            "Neither party shall be liable for indirect, incidental, special, or consequential damages. The aggregate liability of either party under this Agreement shall not exceed the total fees paid by Customer in the preceding six (6) months.",
        ),
        (
            "Section 5: Governing Law, Venue, and Dispute Resolution",
            "This Agreement shall be governed by and construed under the laws of the State of Delaware. Any dispute arising out of this Agreement shall be resolved through binding arbitration in Wilmington, Delaware.",
        ),
    ]

    v2_pdf_path = out_dir / "v2_vendor_agreement.pdf"
    create_styled_pdf(
        file_path=v2_pdf_path,
        title="MASTER SERVICES AGREEMENT",
        version_tag="VERSION 2.0",
        effective_date="March 1, 2026",
        sections=v2_sections,
        highlight_section_idx=2,  # Highlights Section 3 in subtle red
    )

    # Plain text version for instant reading in VS Code
    v2_txt_path = out_dir / "v2_vendor_agreement.txt"
    with open(v2_txt_path, "w", encoding="utf-8") as f:
        f.write("=== MASTER SERVICES AGREEMENT (VERSION 2.0) ===\n")
        f.write("[NOTE: Section 3 altered from 30 days to 60 days + termination penalty]\n\n")
        for title, body in v2_sections:
            f.write(f"{title}\n{body}\n\n")


if __name__ == "__main__":
    create_sample_contracts()
