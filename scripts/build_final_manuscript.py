"""Build IEEE conference-style LaTeX and PDF from the audited manuscript."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
KEYWORDS = (
    "multi-UAV systems, natural-language planning, validation placement, "
    "failure containment, static plan fidelity, resource measurement"
)
CITATION_NUMBERS = {
    "L1": 1,
    "L2": 2,
    "E1": 3,
    "E2": 4,
    "E3": 5,
    "L7": 6,
    "L8": 7,
    "E4": 8,
}
CITATION_KEYS = {
    "L1": "tacos",
    "L2": "swarm_steward",
    "E1": "roco",
    "E2": "swarm_gpt",
    "E3": "llamar",
    "L7": "language_pddl",
    "L8": "commandswarm",
    "E4": "multiuav_plat",
}
IEEE_REFERENCES = (
    (
        "tacos",
        "A. Nazzari, R. Rubinacci, and M. Lovera, \"TACOS: Task Agnostic "
        "Coordinator of a Multi-Drone System,\" Drones, vol. 10, no. 4, "
        "Art. no. 251, 2026, doi: 10.3390/drones10040251.",
    ),
    (
        "swarm_steward",
        "A. Jarabo-Peñas, J. Bravo-Arrabal, E. G. A. Rolland, and A. L. "
        "Christensen, \"Swarm-Steward: Scalable and Reliable Natural-Language "
        "Coordination of Autonomous Aerial and Ground Robots,\" in Proc. Int. "
        "Conf. Unmanned Aircraft Systems (ICUAS), 2026, 9 pp.",
    ),
    (
        "roco",
        "M. Zhao, S. Jain, and S. Song, \"RoCo: Dialectic Multi-Robot "
        "Collaboration with Large Language Models,\" arXiv:2307.04738, 2023.",
    ),
    (
        "swarm_gpt",
        "A. Jiao et al., \"Swarm-GPT: Combining Large Language Models with "
        "Safe Motion Planning for Robot Choreography Design,\" "
        "arXiv:2312.01059, 2023.",
    ),
    (
        "llamar",
        "S. Nayak et al., \"LLaMAR: Long-Horizon Planning for Multi-Agent "
        "Robots in Partially Observable Environments,\" in Advances in Neural "
        "Information Processing Systems, vol. 37, 2024.",
    ),
    (
        "language_pddl",
        "Y. Xie, C. Yu, T. Zhu, J. Bai, Z. Gong, and H. Soh, \"Translating "
        "Natural Language to Planning Goals with Large-Language Models,\" "
        "arXiv:2302.05128, 2023.",
    ),
    (
        "commandswarm",
        "M. Majid and A. Y. Majid, \"CommandSwarm: Safety-Aware Natural "
        "Language-to-Behavior-Tree Generation for Robotic Swarms,\" "
        "arXiv:2605.07764, 2026.",
    ),
    (
        "multiuav_plat",
        "S. Zhang, Q. Li, Y. Zang, X. Huang, Y. Fu, and C. Zhu, "
        "\"MultiUAV-Plat: An LLM-Oriented Platform, Benchmark and Framework "
        "for Multi-UAV Collaborative Task Planning,\" arXiv:2606.31073, 2026.",
    ),
)


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


def _split_manuscript(markdown: str) -> tuple[str, str, list[str]]:
    lines = markdown.splitlines()
    title = _plain(lines[0].removeprefix("# "))
    abstract_start = lines.index("## Abstract") + 1
    body_start = next(
        index for index, line in enumerate(lines) if line.startswith("## 1.")
    )
    abstract = " ".join(
        line.strip() for line in lines[abstract_start:body_start] if line.strip()
    )
    return title, abstract, lines[body_start:]


def _render_latex(markdown: str) -> str:
    title, abstract, lines = _split_manuscript(markdown)
    body: list[str] = []
    table_rows: list[list[str]] = []
    list_kind: str | None = None
    figure_number = 0
    table_number = 0

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            body.append(f"\\end{{{list_kind}}}")
            list_kind = None

    def flush_table() -> None:
        nonlocal table_number
        if table_rows:
            table_number += 1
            body.extend(_latex_table(table_rows, table_number))
            table_rows.clear()

    for raw in lines:
        line = raw.strip()
        if line == "## References":
            close_list()
            flush_table()
            break
        if line.startswith("|"):
            close_list()
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not all(set(cell) <= {"-", ":"} for cell in cells):
                table_rows.append(cells)
            continue
        flush_table()
        if not line:
            close_list()
            body.append("")
        elif line.startswith("## "):
            close_list()
            body.append(
                f"\\section{{{_latex_text(_strip_section_number(line[3:]))}}}"
            )
        elif line.startswith("### "):
            close_list()
            body.append(
                f"\\subsection{{{_latex_text(_strip_section_number(line[4:]))}}}"
            )
        elif line.startswith("!["):
            close_list()
            match = re.match(r"!\[([^]]+)\]\(([^)]+)\)", line)
            if match:
                figure_number += 1
                caption, path = match.groups()
                body.extend(
                    [
                        "\\begin{figure*}[t]",
                        "\\centering",
                        f"\\includegraphics[width=0.94\\textwidth]{{../{_latex_path(path)}}}",
                        f"\\caption{{{_latex_text(caption)}.}}",
                        f"\\label{{fig:result_{figure_number}}}",
                        "\\end{figure*}",
                    ]
                )
        elif line.startswith("- "):
            if list_kind != "itemize":
                close_list()
                list_kind = "itemize"
                body.append("\\begin{itemize}")
            body.append(f"\\item {_latex_text_with_citations(line[2:])}")
        elif re.match(r"^\d+\.\s", line):
            if list_kind != "enumerate":
                close_list()
                list_kind = "enumerate"
                body.append("\\begin{enumerate}")
            item_text = re.sub(r"^\d+\.\s*", "", line)
            body.append(f"\\item {_latex_text_with_citations(item_text)}")
        else:
            close_list()
            body.append(_latex_text_with_citations(line))
    close_list()
    flush_table()

    references = ["\\begin{thebibliography}{00}"]
    for key, citation in IEEE_REFERENCES:
        references.append(f"\\bibitem{{{key}}} {_latex_text(citation)}")
    references.append("\\end{thebibliography}")

    return "\n".join(
        [
            "\\documentclass[conference]{IEEEtran}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage[T1]{fontenc}",
            "\\usepackage{booktabs}",
            "\\usepackage{graphicx}",
            "\\usepackage[hidelinks]{hyperref}",
            "\\usepackage{microtype}",
            "\\title{" + _latex_text(title) + "}",
            "\\author{\\IEEEauthorblockN{Author information withheld for mentor review}\\\\",
            "\\IEEEauthorblockA{Final manuscript prepared 12 August 2026}}",
            "\\begin{document}",
            "\\maketitle",
            "\\begin{abstract}",
            _latex_text_with_citations(abstract),
            "\\end{abstract}",
            "\\begin{IEEEkeywords}",
            _latex_text(KEYWORDS),
            "\\end{IEEEkeywords}",
            *_collapse_empty(body),
            *references,
            "\\end{document}",
            "",
        ]
    )


def _latex_table(rows: list[list[str]], number: int) -> list[str]:
    if not rows:
        return []
    columns = len(rows[0])
    column_spec = "l" + "c" * (columns - 1)
    rendered = [
        "\\begin{table*}[t]",
        "\\caption{Registered paired accuracy contrasts.}",
        f"\\label{{tab:accuracy_{number}}}",
        "\\centering",
        "\\small",
        "\\resizebox{0.92\\textwidth}{!}{%",
        f"\\begin{{tabular}}{{{column_spec}}}",
        "\\toprule",
    ]
    for index, row in enumerate(rows):
        rendered.append(" & ".join(_latex_text(cell) for cell in row) + " \\\\")
        if index == 0:
            rendered.append("\\midrule")
    rendered.extend(
        [
            "\\bottomrule",
            "\\end{tabular}%",
            "}",
            "\\end{table*}",
        ]
    )
    return rendered


def _render_pdf(markdown: str, source_dir: Path, output: Path) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            BaseDocTemplate,
            Frame,
            FrameBreak,
            Image,
            KeepTogether,
            NextPageTemplate,
            PageBreak,
            PageTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as error:
        raise SystemExit(
            "ReportLab is required to build the PDF; use the bundled workspace Python."
        ) from error

    title, abstract, lines = _split_manuscript(markdown)
    page_width, page_height = LETTER
    margin_x = 0.625 * inch
    margin_top = 0.5 * inch
    margin_bottom = 0.5 * inch
    column_gap = 0.24 * inch
    usable_width = page_width - 2 * margin_x
    column_width = (usable_width - column_gap) / 2
    first_header_height = 3.50 * inch
    first_body_height = page_height - margin_top - margin_bottom - first_header_height

    doc = BaseDocTemplate(
        str(output),
        pagesize=LETTER,
        leftMargin=margin_x,
        rightMargin=margin_x,
        topMargin=margin_top,
        bottomMargin=margin_bottom,
        title=title,
        author="Author information withheld for mentor review",
        subject="Final Shepherd-AI validation-placement manuscript",
    )
    first_frames = [
        Frame(
            margin_x,
            page_height - margin_top - first_header_height,
            usable_width,
            first_header_height,
            id="first_header",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=5,
        ),
        Frame(
            margin_x,
            margin_bottom,
            column_width,
            first_body_height - 7,
            id="first_left",
            leftPadding=0,
            rightPadding=4,
            topPadding=0,
            bottomPadding=0,
        ),
        Frame(
            margin_x + column_width + column_gap,
            margin_bottom,
            column_width,
            first_body_height - 7,
            id="first_right",
            leftPadding=4,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        ),
    ]
    body_frames = [
        Frame(
            margin_x,
            margin_bottom,
            column_width,
            page_height - margin_top - margin_bottom,
            id="body_left",
            leftPadding=0,
            rightPadding=4,
            topPadding=0,
            bottomPadding=0,
        ),
        Frame(
            margin_x + column_width + column_gap,
            margin_bottom,
            column_width,
            page_height - margin_top - margin_bottom,
            id="body_right",
            leftPadding=4,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        ),
    ]
    wide_figure_frame = Frame(
        margin_x,
        margin_bottom,
        usable_width,
        page_height - margin_top - margin_bottom,
        id="wide_figures",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates(
        [
            PageTemplate(
                id="First",
                frames=first_frames,
                onPage=_ieee_page_number,
                autoNextPageTemplate="TwoColumn",
            ),
            PageTemplate(
                id="TwoColumn",
                frames=body_frames,
                onPage=_ieee_page_number,
            ),
            PageTemplate(
                id="WideFigures",
                frames=[wide_figure_frame],
                onPage=_ieee_page_number,
            ),
        ]
    )

    styles = _pdf_styles()
    story: list[object] = [
        Paragraph(_pdf_text(title), styles["title"]),
        Paragraph("Author information withheld for mentor review", styles["author"]),
        Paragraph("Final manuscript prepared 12 August 2026", styles["note"]),
        Paragraph(f"<b>Abstract-</b> {_pdf_text_with_citations(abstract)}", styles["abstract"]),
        Paragraph(f"<b>Index Terms-</b> {_pdf_text(KEYWORDS)}", styles["abstract"]),
        FrameBreak(),
    ]
    paragraph: list[str] = []
    table_rows: list[list[str]] = []
    section_number = 0
    subsection_number = 0
    figure_number = 0
    table_number = 0
    pending_figures: list[tuple[int, str, str]] = []

    def flush_paragraph() -> None:
        if paragraph:
            story.append(
                Paragraph(
                    _pdf_text_with_citations(" ".join(paragraph)), styles["body"]
                )
            )
            paragraph.clear()

    def flush_table() -> None:
        nonlocal table_number
        if not table_rows:
            return
        table_number += 1
        caption = Paragraph(
            f"TABLE {_roman(table_number)}<br/>REGISTERED PAIRED ACCURACY CONTRASTS",
            styles["table_caption"],
        )
        data = [
            [Paragraph(_pdf_text(cell), styles["table"]) for cell in row]
            for row in table_rows
        ]
        widths = [0.63 * inch, 0.58 * inch, 1.03 * inch, 1.03 * inch]
        table = Table(data, colWidths=widths, repeatRows=1, hAlign="CENTER")
        table.setStyle(
            TableStyle(
                [
                    ("LINEABOVE", (0, 0), (-1, 0), 0.7, colors.black),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.35, colors.black),
                    ("LINEBELOW", (0, -1), (-1, -1), 0.7, colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(KeepTogether([caption, table, Spacer(1, 4)]))
        table_rows.clear()

    for raw in lines:
        line = raw.strip()
        if line == "## References":
            flush_paragraph()
            flush_table()
            break
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
            section_number += 1
            subsection_number = 0
            heading = _strip_section_number(line[3:]).upper()
            story.append(
                Paragraph(f"{_roman(section_number)}. {html.escape(heading)}", styles["section"])
            )
        elif line.startswith("### "):
            flush_paragraph()
            subsection_number += 1
            heading = _strip_section_number(line[4:])
            story.append(
                Paragraph(
                    f"{chr(64 + subsection_number)}. <i>{html.escape(heading)}</i>",
                    styles["subsection"],
                )
            )
        elif line.startswith("!["):
            flush_paragraph()
            match = re.match(r"!\[([^]]+)\]\(([^)]+)\)", line)
            if match:
                figure_number += 1
                caption, image_path = match.groups()
                pending_figures.append((figure_number, caption, image_path))
        elif line.startswith("- "):
            flush_paragraph()
            story.append(
                Paragraph(f"- {_pdf_text_with_citations(line[2:])}", styles["list"])
            )
        elif re.match(r"^\d+\.\s", line):
            flush_paragraph()
            item_number, item_text = line.split(".", maxsplit=1)
            story.append(
                Paragraph(
                    f"{item_number}. {_pdf_text_with_citations(item_text.strip())}",
                    styles["list"],
                )
            )
        else:
            paragraph.append(line)
    flush_paragraph()
    flush_table()

    story.append(Paragraph("REFERENCES", styles["section"]))
    for number, (_, citation) in enumerate(IEEE_REFERENCES, start=1):
        story.append(
            Paragraph(
                f"[{number}] {_pdf_text(citation)}",
                styles["reference"],
            )
        )

    if pending_figures:
        story.append(FrameBreak())
        for number, caption, image_path in pending_figures[:2]:
            image = Image(str(source_dir / image_path))
            scale = min(
                column_width / image.imageWidth,
                (2.65 * inch) / image.imageHeight,
            )
            image.drawWidth = image.imageWidth * scale
            image.drawHeight = image.imageHeight * scale
            story.append(
                KeepTogether(
                    [
                        image,
                        Paragraph(
                            f"Fig. {number}.  {_pdf_text(caption)}.",
                            styles["caption"],
                        ),
                    ]
                )
            )
        story.extend([NextPageTemplate("WideFigures"), PageBreak(), Spacer(1, 8)])
        for number, caption, image_path in pending_figures[2:]:
            image = Image(str(source_dir / image_path))
            scale = min(
                usable_width / image.imageWidth,
                (4.15 * inch) / image.imageHeight,
            )
            image.drawWidth = image.imageWidth * scale
            image.drawHeight = image.imageHeight * scale
            story.append(
                KeepTogether(
                    [
                        image,
                        Paragraph(
                            f"Fig. {number}.  {_pdf_text(caption)}.",
                            styles["caption"],
                        ),
                    ]
                )
            )

    doc.build(story)


def _pdf_styles() -> dict[str, object]:
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch

    return {
        "title": ParagraphStyle("IeeeTitle", fontName="Times-Bold", fontSize=16, leading=18, alignment=TA_CENTER, spaceAfter=9),
        "author": ParagraphStyle("IeeeAuthor", fontName="Times-Roman", fontSize=10, leading=12, alignment=TA_CENTER, spaceAfter=2),
        "note": ParagraphStyle("IeeeNote", fontName="Times-Roman", fontSize=7.5, leading=9, alignment=TA_CENTER, spaceAfter=8),
        "abstract": ParagraphStyle("IeeeAbstract", fontName="Times-Roman", fontSize=8.4, leading=9.8, alignment=TA_JUSTIFY, leftIndent=0.25 * inch, rightIndent=0.25 * inch, spaceAfter=5),
        "section": ParagraphStyle("IeeeSection", fontName="Times-Roman", fontSize=9.5, leading=11, alignment=TA_CENTER, spaceBefore=7, spaceAfter=3, keepWithNext=True),
        "subsection": ParagraphStyle("IeeeSubsection", fontName="Times-Italic", fontSize=9, leading=10.5, alignment=TA_LEFT, spaceBefore=5, spaceAfter=2, keepWithNext=True),
        "body": ParagraphStyle("IeeeBody", fontName="Times-Roman", fontSize=8.25, leading=9.65, alignment=TA_JUSTIFY, firstLineIndent=0.14 * inch, spaceAfter=3),
        "list": ParagraphStyle("IeeeList", fontName="Times-Roman", fontSize=8.25, leading=9.65, alignment=TA_JUSTIFY, leftIndent=0.16 * inch, firstLineIndent=-0.12 * inch, spaceAfter=2),
        "caption": ParagraphStyle("IeeeCaption", fontName="Times-Roman", fontSize=7.4, leading=8.4, alignment=TA_CENTER, spaceBefore=2, spaceAfter=5),
        "table_caption": ParagraphStyle("IeeeTableCaption", fontName="Times-Roman", fontSize=7.4, leading=8.4, alignment=TA_CENTER, spaceBefore=4, spaceAfter=3),
        "table": ParagraphStyle("IeeeTableText", fontName="Times-Roman", fontSize=5.8, leading=6.7),
        "reference": ParagraphStyle("IeeeReference", fontName="Times-Roman", fontSize=7.1, leading=8.2, alignment=TA_LEFT, leftIndent=0.18 * inch, firstLineIndent=-0.18 * inch, spaceAfter=2),
    }


def _ieee_page_number(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Times-Roman", 7.5)
    canvas.drawCentredString(document.pagesize[0] / 2, 0.27 * 72, str(document.page))
    canvas.restoreState()


def _plain(text: str) -> str:
    text = re.sub(r"[*`]", "", text).strip()
    return (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("â€“", "-")
        .replace("â€”", "-")
    )


def _pdf_text(text: str) -> str:
    return html.escape(_plain(text), quote=False)


def _pdf_text_with_citations(text: str) -> str:
    rendered = _pdf_text(text)
    for citation, number in CITATION_NUMBERS.items():
        rendered = rendered.replace(f"[{citation}]", f"[{number}]")
    return rendered


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


def _latex_text_with_citations(text: str) -> str:
    placeholders: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        citation = match.group(1)
        placeholder = f"CITATIONPLACEHOLDER{len(placeholders)}"
        placeholders[placeholder] = f"\\cite{{{CITATION_KEYS[citation]}}}"
        return placeholder

    rendered = re.sub(r"\[(L1|L2|E1|E2|E3|L7|L8|E4)\]", replace, text)
    rendered = _latex_text(rendered)
    for placeholder, citation in placeholders.items():
        rendered = rendered.replace(placeholder, citation)
    return rendered


def _latex_path(path: str) -> str:
    return path.replace("\\", "/").replace("{", "\\{").replace("}", "\\}")


def _strip_section_number(text: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", text)


def _roman(number: int) -> str:
    values = ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
    result = []
    remaining = number
    for value, numeral in values:
        while remaining >= value:
            result.append(numeral)
            remaining -= value
    return "".join(result)


def _collapse_empty(lines: Iterable[str]) -> list[str]:
    rendered: list[str] = []
    for line in lines:
        if line or not rendered or rendered[-1]:
            rendered.append(line)
    return rendered


if __name__ == "__main__":
    main()
