from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


def _kv_table(data: Dict[str, Any], col1="Field", col2="Value"):
    rows = [[col1, col2]] + [[str(k), str(v)] for k, v in data.items()]
    t = Table(rows, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f0f0")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#333333")),
        ("BOX", (0,0), (-1,-1), 0.25, colors.black),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#cccccc")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ]))
    return t


def build_claim_packet_pdf(payload: Dict[str, Any],
                           coverage: Dict[str, Any],
                           risk: Dict[str, Any]) -> bytes:
    """
    payload: original claim input
    coverage: response from /claims/coverage
    risk: response from /claims/risk
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)

    styles = getSampleStyleSheet()
    H1, H2, H3 = styles["Heading1"], styles["Heading2"], styles["Heading3"]
    Body = styles["BodyText"]

    story = []
    story.append(Paragraph("ClaimSight AI — Case Packet", H1))
    story.append(Paragraph(datetime.utcnow().strftime("Generated: %Y-%m-%d %H:%M UTC"), Body))
    story.append(Spacer(1, 14))

    # Claim summary
    story.append(Paragraph("Claim Summary", H2))
    claim_fields = {
        "Claim ID": payload.get("claim_id"),
        "Policy ID": payload.get("policy_id"),
        "Loss Type": payload.get("loss_type"),
        "Amount": payload.get("amount"),
        "ZIP": payload.get("zip"),
        "Notes": payload.get("notes", "")[:500],
    }
    story.append(_kv_table(claim_fields))
    story.append(Spacer(1, 12))

    # Coverage determination
    story.append(Paragraph("Coverage Determination", H2))
    cov_fields = {
        "Decision": coverage.get("coverage"),
        "Rationale": coverage.get("rationale", "")[:1000],
    }
    story.append(_kv_table(cov_fields))
    story.append(Spacer(1, 8))

    # Endorsements table
    endos = coverage.get("endorsements") or []
    story.append(Paragraph("Endorsements (from PAS/PC)", H3))
    if endos:
        rows = [["Code", "Description"]] + [[e.get("code",""), e.get("desc","")] for e in endos]
        t = Table(rows, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f0f0")),
            ("BOX", (0,0), (-1,-1), 0.25, colors.black),
            ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#cccccc")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("None.", Body))
    story.append(Spacer(1, 8))

    # Citations list
    cites = coverage.get("citations") or []
    story.append(Paragraph("Policy Citations", H3))
    if cites:
        rows = [["Citation"]] + [[c] for c in cites]
        t = Table(rows, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f0f0")),
            ("BOX", (0,0), (-1,-1), 0.25, colors.black),
            ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#cccccc")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("None.", Body))
    story.append(Spacer(1, 12))

    # Risk
    story.append(Paragraph("Risk Score (Explainability)", H2))
    risk_fields = {
        "Score": risk.get("score"),
        "Reasons": ", ".join(risk.get("reasons", []))[:500],
        "Top Features": ", ".join(risk.get("top_features", [])),
    }
    story.append(_kv_table(risk_fields))
    story.append(Spacer(1, 18))

    # Fine print
    story.append(Paragraph(
        "Disclaimer: This packet is generated from synthetic data and demo logic for evaluation purposes.",
        Body
    ))

    doc.build(story)
    return buf.getvalue()
