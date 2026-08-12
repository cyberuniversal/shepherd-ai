"""Build final LaTeX and PDF manuscripts from the audited Markdown source."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "reports" / "multiuav_validation_placement_manuscript_v1.md",
    )
    parser.add_argument(
        "--tex-output",
        type=Path,
        default=ROOT / "reports" / "final" / "shepherd_ai_manuscript.tex",
    )
    parser.add_argument(
        "--pdf-output",
        type=Path,
        default=ROOT / "reports" / "final" / "shepherd_ai_manuscript.pdf",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    text = source.read_text(encoding="utf-8-sig")
    publication_text = text.split("\n## Artifact Traceability", maxsplit=1)[0]
    args.tex_output.parent.mkdir(parents=True, exist_ok=True)
    args.pdf_output.parent.mkdir(parents=True, exist_ok=True)
    args.tex_output.write_text(
        _render_latex(publication_text), encoding="utf-8", newline="\n"
    )
    _render_pdf(publication_text, source.parent, args.pdf_output)
    print(args.tex_output)
    print(args.pdf_output)


def _render_latex(markdown: str) -> str:
    lines = markdown.splitlines()
    title = _plain(lines[0].removeprefix("# "))
    body = []
    in_table = False
    table_rows: list[list[str]] = []
    for raw in lines[1:]:
        line = raw.strip()
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if all(set(cell) <= {"-", ":"} for cell in cells):
                continue
            table_rows.append(cells)
            in_table = True
            continue
        if in_table:
            body.extend(_latex_table(table_rows))
            table_rows = []
            in_table = False
        if not line:
            body.append("")
        elif line.startswith("## "):
            heading = line[3:]
            if heading == "Abstract":
                body.append("\\begin{abstract}")
            elif heading == "References":
                body.append("\\end{abstract}" if "\\begin{abstract}" in body and "\\end{abstract}" not in body else "")
                body.append("\\section*{References}")
            else:
                if "\\begin{abstract}" in body and "\\end{abstract}" not in body:
                    body.append("\\end{abstract}")
                body.append(f"\\section{{{_latex_text(_strip_section_number(heading))}}}")
        elif line.startswith("### "):
            body.append(f"\\subsection{{{_latex_text(_strip_section_number(line[4:]))}}}")
        elif line.startswith("!["):
            match = re.match(r"!\[([^]]+)\]\(([^)]+)\)", line)
            if match:
                caption, path = match.groups()
                body.extend(
                    [
                        "\\begin{figure}[htbp]",
                        "\\centering",
                        f"\\includegraphics[width=\\linewidth]{{../{_latex_text(path)}}}",
                        f"\\caption{{{_latex_text(caption)}}}",
                        "\\end{figure}",
                    ]
                )
        elif line.startswith("- "):
            if not body or body[-1] != "\\begin{itemize}":
                body.append("\\begin{itemize}")
            body.append(f"\\item {_latex_text(line[2:])}")
        elif line.startswith("**["):
            body.append(_latex_text(line))
        elif line.startswith("**"):
            body.append(f"\\textbf{{{_latex_text(_plain(line))}}}")
        else:
            if body and body[-1].startswith("\\item ") and not line.startswith("-"):
                body.append("\\end{itemize}")
            body.append(_latex_text(line))
    if in_table:
        body.extend(_latex_table(table_rows))
    if body and body[-1].startswith("\\item "):
        body.append("\\end{itemize}")
    body = _collapse_empty(body)
    return "\n".join(
        [
            "\\documentclass[11pt]{article}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage[T1]{fontenc}",
            "\\usepackage[a4paper,margin=1in]{geometry}",
            "\\usepackage{booktabs}",
            "\\usepackage{graphicx}",
            "\\usepackage[hidelinks]{hyperref}",
            "\\usepackage{microtype}",
            "\\title{" + _latex_text(title) + "}",
            "\\author{Author information withheld for mentor review}",
            "\\date{12 August 2026}",
            "\\begin{document}",
            "\\maketitle",
            *body,
            "\\end{document}",
            "",
        ]
    )


def _latex_table(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    columns = len(rows[0])
    spec = "l" * columns
    rendered = ["\\begin{table}[htbp]", "\\centering", f"\\begin{{tabular}}{{{spec}}}", "\\toprule"]
    for index, row in enumerate(rows):
        rendered.append(" & ".join(_latex_text(cell) for cell in row) + " \\\\")
        if index == 0:
            rendered.append("\\midrule")
    rendered.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    return rendered


def _render_pdf(markdown: str, source_dir: Path, output: Path) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Image,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as error:
        raise SystemExit(
            "ReportLab is required to build the PDF; use the bundled workspace Python."
        ) from error

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="PaperTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, leading=23, spaceAfter=10, textColor=colors.HexColor("#17212b")))
    styles.add(ParagraphStyle(name="PaperMeta", parent=styles["Normal"], fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#53616f"), spaceAfter=16))
    styles.add(ParagraphStyle(name="PaperH1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, spaceBefore=12, spaceAfter=7, textColor=colors.HexColor("#0f5c5e")))
    styles.add(ParagraphStyle(name="PaperH2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, spaceBefore=9, spaceAfter=5, textColor=colors.HexColor("#17212b")))
    styles.add(ParagraphStyle(name="PaperBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.3, leading=13, spaceAfter=6, textColor=colors.HexColor("#202a34")))
    styles.add(ParagraphStyle(name="PaperSmall", parent=styles["BodyText"], fontSize=7.7, leading=10, textColor=colors.HexColor("#53616f")))
    styles.add(ParagraphStyle(name="PaperBullet", parent=styles["BodyText"], fontSize=9.2, leading=12.5, leftIndent=12, firstLineIndent=-7, bulletIndent=2, spaceAfter=3))

    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm, title=_plain(markdown.splitlines()[0].removeprefix("# ")), author="Shepherd-AI research project")
    story = []
    lines = markdown.splitlines()
    story.append(Paragraph(_pdf_text(lines[0].removeprefix("# ")), styles["PaperTitle"]))
    story.append(Paragraph("Final mentor-review manuscript | 12 August 2026", styles["PaperMeta"]))
    paragraph: list[str] = []
    table_rows: list[list[str]] = []

    def flush_paragraph() -> None:
        if paragraph:
            story.append(Paragraph(_pdf_text(" ".join(paragraph)), styles["PaperBody"]))
            paragraph.clear()

    def flush_table() -> None:
        if not table_rows:
            return
        data = [[Paragraph(_pdf_text(cell), styles["PaperSmall"]) for cell in row] for row in table_rows]
        widths = [doc.width * 0.32] + [doc.width * 0.68 / (len(data[0]) - 1)] * (len(data[0]) - 1)
        table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f5c5e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#bdc7cf")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f6")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.extend([table, Spacer(1, 7)])
        table_rows.clear()

    for raw in lines[1:]:
        line = raw.strip()
        if line.startswith("|"):
            flush_paragraph()
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not all(set(cell) <= {"-", ":"} for cell in cells):
                table_rows.append(cells)
            continue
        flush_table()
        if not line:
            flush_paragraph()
        elif line.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(_pdf_text(line[3:]), styles["PaperH1"]))
        elif line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(_pdf_text(line[4:]), styles["PaperH2"]))
        elif line.startswith("!["):
            flush_paragraph()
            match = re.match(r"!\[([^]]+)\]\(([^)]+)\)", line)
            if match:
                caption, image_path = match.groups()
                image = Image(str(source_dir / image_path), width=doc.width, height=doc.width * 0.52, kind="proportional")
                story.extend([Spacer(1, 4), image, Paragraph(_pdf_text(caption), styles["PaperSmall"]), Spacer(1, 7)])
        elif line.startswith("- "):
            flush_paragraph()
            story.append(Paragraph("• " + _pdf_text(line[2:]), styles["PaperBullet"]))
        elif line.startswith("**["):
            flush_paragraph()
            story.append(Paragraph(_pdf_text(line), styles["PaperSmall"]))
        elif line.startswith("**"):
            flush_paragraph()
            story.append(Paragraph("<b>" + _pdf_text(_plain(line)) + "</b>", styles["PaperMeta"]))
        else:
            paragraph.append(line)
    flush_paragraph()
    flush_table()
    story.append(PageBreak()) if False else None

    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6b7783"))
        canvas.drawString(18 * mm, 10 * mm, "Shepherd-AI | final mentor-review package")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def _plain(text: str) -> str:
    return re.sub(r"[*`]", "", text).strip()


def _pdf_text(text: str) -> str:
    text = _plain(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _latex_text(text: str) -> str:
    text = _plain(text)
    replacements = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in text)


def _strip_section_number(text: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", text)


def _collapse_empty(lines: Iterable[str]) -> list[str]:
    rendered: list[str] = []
    for line in lines:
        if line or not rendered or rendered[-1]:
            rendered.append(line)
    return rendered


if __name__ == "__main__":
    main()
