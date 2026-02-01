from __future__ import annotations

import csv
import json
import html
from pathlib import Path
from typing import Dict, List, Any

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def export_csv(results: Dict[str, List[Dict[str, Any]]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Type", "Name", "Status"])
        for obj_type, items in results.items():
            for item in items:
                writer.writerow([obj_type, item.get("name", ""), item.get("status", "")])


def export_html(results: Dict[str, List[Dict[str, Any]]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for obj_type, items in results.items():
        for item in items:
            rows.append((obj_type, item.get("name", ""), item.get("status", "")))

    html = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><title>SQL Compare Report</title>",
        "<style>table{border-collapse:collapse;width:100%;}th,td{border:1px solid #ccc;padding:6px;} .IDENTICAL{background:#f2f2f2;} .DIFFERENT{background:#fffacd;} .MISSING_IN_TARGET{background:#e6ffe6;} .MISSING_IN_SOURCE{background:#ffe6e6;}</style>",
        "</head><body>",
        "<h2>SQL Compare Report</h2>",
        "<table><tr><th>Type</th><th>Name</th><th>Status</th></tr>",
    ]
    for obj_type, name, status in rows:
        obj = html.escape(obj_type)
        nm = html.escape(name)
        st = html.escape(status)
        html.append(f"<tr class='{st}'><td>{obj}</td><td>{nm}</td><td>{st}</td></tr>")
    html.append("</table></body></html>")

    path.write_text("\n".join(html), encoding="utf-8")


def export_json(results: Dict[str, List[Dict[str, Any]]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")


def export_excel(results: Dict[str, List[Dict[str, Any]]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Objects"
    ws.append(["Type", "Name", "Status"])
    for obj_type, items in results.items():
        for item in items:
            ws.append([obj_type, item.get("name", ""), item.get("status", "")])
    wb.save(path)


def export_pdf(results: Dict[str, List[Dict[str, Any]]], path: Path) -> None:
    """Export comparison results to a simple PDF report.

    The PDF contains a title and a single table with Type/Name/Status
    columns. It is intentionally lightweight but suitable for sharing
    compare results.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4))
    styles = getSampleStyleSheet()

    elements: list[Any] = []
    title = Paragraph("SQL Compare Report", styles["Heading1"])
    elements.append(title)
    elements.append(Spacer(1, 12))

    data: list[list[str]] = [["Type", "Name", "Status"]]
    for obj_type, items in results.items():
        for item in items:
            data.append([
                str(obj_type),
                str(item.get("name", "")),
                str(item.get("status", "")),
            ])

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
            ]
        )
    )

    elements.append(table)
    doc.build(elements)
