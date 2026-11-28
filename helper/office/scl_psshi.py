"""DOCX adapter for the SCL PSSHI study-skills report."""

from __future__ import annotations

import math
import logging
import posixpath
import re
import shutil
from pathlib import Path
from typing import Mapping

from lxml import etree
from PIL import Image, ImageOps

import config
from helper.diagram.scl_report4 import chart_radar
from helper.diagram.scl_report3.report import _register_bundled_iran_font, _shape_svg_text
from helper.office.word_helper import (
    _replace_scl_report3_text_tokens,
    convert_docx_to_pdf,
    unzip_word_file,
    zip_word_folder,
)
from quiz_packages.scl.legacy_v1.scoring import bookmark_scl_object


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
NS = {"w": WORD_NS, "r": REL_NS}

PSSHI_SKILLS = (
    "timePSSHI", "placePSSHI", "readingPSSHI", "writtingPSSHI",
    "memoryPSSHI", "motivationPSSHI", "examPSSHI",
)
PSSHI_CHALLENGES = ("anx", "dep", "ocd", "motive", "conf")
PSYCH_FACTOR_TO_CHALLENGE = {
    "anxiety": "anx",
    "depression": "dep",
    "ocd": "ocd",
    "motivation": "motive",
    "self_confident": "conf",
}
PSSHI_RADAR_TARGET = "image4.png"
PSSHI_RADAR_RELATIONSHIP_TARGET = "media/image4.png"
_MARKER_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:timePSSHI[1-4]|placePSSHI[1-4]|readingPSSHI[1-4]|"
    r"writtingPSSHI[1-4]|memoryPSSHI[1-4]|motivationPSSHI[1-4]|examPSSHI[1-4]|"
    r"anx|dep|ocd|motive|conf)(?![A-Za-z0-9_])"
)


def build_psshi_levels(labels: Mapping[str, object]) -> dict[str, int]:
    """Map scored PSSHI item sums to the template's four presentation levels.

    PSSHI answers are already scored 0–4 per item. Existing report bands use
    0–1, 1–2, 2–3 and 3–4; the chart numbers levels in the opposite direction,
    with level 1 strongest. This adapter does not alter or persist source scores.
    """
    result = {}
    for skill in PSSHI_SKILLS:
        if skill not in labels or skill not in bookmark_scl_object:
            raise ValueError(f"Missing authoritative PSSHI result: {skill}")
        count = bookmark_scl_object[skill]["count"]
        if not count:
            raise ValueError(f"PSSHI item count is not configured for {skill}")
        raw = labels[skill]
        if isinstance(raw, bool):
            raise ValueError(f"Invalid PSSHI score for {skill}: {raw!r}")
        try:
            score = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid PSSHI score for {skill}: {raw!r}") from exc
        mean = score / count
        if not math.isfinite(mean) or mean < 0 or mean > 4:
            raise ValueError(f"PSSHI score outside the expected 0–4 mean for {skill}: {mean}")
        # A score at an exact band boundary belongs to the band beginning there.
        band = min(int(mean), 3)
        result[skill] = 4 - band
    return result


def select_psshi_challenge(psychological_order, psychological_scores: Mapping[str, object]) -> str:
    """Select the top existing psychological priority with stable tie ordering."""
    expected_factors = tuple(PSYCH_FACTOR_TO_CHALLENGE)
    ordered = tuple(psychological_order)
    if len(ordered) != len(expected_factors) or set(ordered) != set(expected_factors):
        raise ValueError("SCL context must contain the complete ordered five-factor psychological assessment")
    scores = {}
    for factor in expected_factors:
        if factor not in psychological_scores:
            raise ValueError(f"SCL context is missing the psychological score for {factor}")
        try:
            score = float(psychological_scores[factor])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid SCL psychological score for {factor}") from exc
        if not math.isfinite(score) or score < 0:
            raise ValueError(f"Invalid SCL psychological score for {factor}: {score}")
        scores[factor] = score
    maximum = max(scores.values())
    if maximum <= 0:
        raise ValueError("No positive psychological challenge is available for the PSSHI advice section")
    if scores[ordered[0]] != maximum:
        raise ValueError("SCL context psychological order does not match its authoritative factor scores")
    return PSYCH_FACTOR_TO_CHALLENGE[ordered[0]]


def _paragraph_text(paragraph) -> str:
    return "".join(node.text or "" for node in paragraph.iter(f"{{{WORD_NS}}}t"))


def _conditional_marker(text: str) -> str | None:
    if text in PSSHI_CHALLENGES:
        return text
    for skill in PSSHI_SKILLS:
        if text in {f"{skill}{level}" for level in range(1, 5)}:
            return text
    return None


def _filter_psshi_blocks(tree: etree._ElementTree, levels: Mapping[str, int], selected_challenge: str) -> None:
    expected_tokens = {f"{skill}{level}" for skill in PSSHI_SKILLS for level in range(1, 5)} | set(PSSHI_CHALLENGES)
    occurrences = {token: 0 for token in expected_tokens}
    kept_pairs = {token: 0 for token in expected_tokens}
    stack: list[tuple[str, bool]] = []
    remove = []
    candidate_rows = set()
    candidate_cells = set()

    for paragraph in tree.getroot().iter(f"{{{WORD_NS}}}p"):
        content = _paragraph_text(paragraph)
        marker = _conditional_marker(content)
        if marker is None:
            if _MARKER_PATTERN.search(content):
                raise ValueError(f"PSSHI conditional marker is not isolated in its Word paragraph: {content!r}")
            if stack and not all(keep for _, keep in stack):
                remove.append(paragraph)
            continue

        occurrences[marker] += 1
        parent = paragraph.getparent()
        while parent is not None and parent.tag != f"{{{WORD_NS}}}tr":
            parent = parent.getparent()
        if parent is not None:
            candidate_rows.add(parent)
        cell = paragraph.getparent()
        while cell is not None and cell.tag != f"{{{WORD_NS}}}tc":
            cell = cell.getparent()
        if cell is not None:
            candidate_cells.add(cell)

        if stack and stack[-1][0] == marker:
            _, selected = stack.pop()
            if selected and all(parent_keep for _, parent_keep in stack):
                kept_pairs[marker] += 1
        else:
            if any(open_marker == marker for open_marker, _ in stack):
                raise ValueError(f"Nested/repeated PSSHI conditional marker is malformed: {marker}")
            if marker in PSSHI_CHALLENGES:
                selected = marker == selected_challenge
            else:
                skill, level_text = marker[:-1], marker[-1]
                selected = levels[skill] == int(level_text)
            stack.append((marker, selected))
        remove.append(paragraph)

    if stack:
        raise ValueError(f"Unclosed PSSHI conditional block: {stack[-1][0]}")

    expected_pairs = {
        token: (8 if token in PSSHI_CHALLENGES else 2)
        for token in expected_tokens
    }
    for token, expected in expected_pairs.items():
        if occurrences[token] != expected * 2:
            raise ValueError(
                f"Unexpected PSSHI template marker count for {token}: "
                f"expected {expected * 2}, found {occurrences[token]}"
            )
        should_keep = (
            token == selected_challenge
            if token in PSSHI_CHALLENGES
            else int(token[-1]) == levels[token[:-1]]
        )
        if kept_pairs[token] != (expected if should_keep else 0):
            raise ValueError(f"PSSHI template did not retain the selected block count for {token}")

    for paragraph in remove:
        parent = paragraph.getparent()
        if parent is not None:
            parent.remove(paragraph)

    # Only prune rows that became empty because their conditional paragraphs were removed.
    for row in candidate_rows:
        if row.getparent() is None:
            continue
        visible_text = "".join(row.itertext()).strip()
        has_visual = any(next(row.iter(f"{{{namespace}}}{tag}"), None) is not None for namespace, tag in (
            (WORD_NS, "drawing"), (WORD_NS, "pict"), (WORD_NS, "object"),
        ))
        if not visible_text and not has_visual:
            row.getparent().remove(row)

    for cell in candidate_cells:
        if cell.getparent() is None:
            continue
        if not cell.xpath("./w:p | ./w:tbl", namespaces=NS):
            etree.SubElement(cell, f"{{{WORD_NS}}}p")

    remaining = []
    for paragraph in tree.getroot().iter(f"{{{WORD_NS}}}p"):
        content = _paragraph_text(paragraph)
        if _conditional_marker(content) or _MARKER_PATTERN.search(content):
            remaining.append(content)
    if remaining:
        raise ValueError(f"PSSHI conditional markers remain after selection: {remaining[:8]}")


def _relax_orphan_skill_page_breaks(tree: etree._ElementTree) -> None:
    """Let the next section follow the short advice blocks on the known orphan pages."""
    body = tree.getroot().find(f"{{{WORD_NS}}}body")
    if body is None:
        raise ValueError("PSSHI document.xml has no Word body")
    targets = ("۳. مهارت مطالعه", "۷. مهارت امتحان دادن")
    removed = set()
    children = list(body)
    for title in targets:
        matching_tables = [
            child for child in children
            if child.tag == f"{{{WORD_NS}}}tbl" and title in "".join(child.itertext())
        ]
        if len(matching_tables) != 1:
            raise ValueError(f"Expected one PSSHI section table titled {title!r}; found {len(matching_tables)}")
        index = children.index(matching_tables[0]) + 1
        if index >= len(children):
            raise ValueError(f"PSSHI section {title!r} has no following page-break paragraph")
        following = children[index]
        page_break = (
            following.tag == f"{{{WORD_NS}}}p"
            and bool(following.xpath('.//w:br[@w:type="page"]', namespaces=NS))
        )
        if not page_break:
            raise ValueError(f"PSSHI page-break layout changed after section {title!r}")
        body.remove(following)
        removed.add(title)
    if removed != set(targets):
        raise ValueError("PSSHI orphan-page layout adjustment did not match its expected sections")


def _resolve_logo(identity_logo: str | None) -> Path | None:
    candidates = [Path(identity_logo)] if identity_logo else []
    if config.DEFAULT_REPORT_LOGO_PATH:
        candidates.append(Path(config.DEFAULT_REPORT_LOGO_PATH))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    logging.warning("No usable organization logo is available; leaving the PSSHI header logo cell empty")
    return None


def _add_header_logo(folder: Path, logo_path: Path | None) -> None:
    if logo_path is None:
        return
    header_path = folder / "word" / "header1.xml"
    if not header_path.is_file():
        raise FileNotFoundError("PSSHI template is missing word/header1.xml")
    parser = etree.XMLParser(remove_blank_text=False)
    header_tree = etree.parse(str(header_path), parser)
    root = header_tree.getroot()
    cells = root.xpath(".//w:tbl/w:tr[1]/w:tc", namespaces=NS)
    if len(cells) != 3:
        raise ValueError(f"PSSHI header logo target changed: expected 3 cells, found {len(cells)}")
    cell = cells[2]
    if "".join(cell.xpath(".//w:t/text()", namespaces=NS)).strip() or cell.xpath(".//w:drawing", namespaces=NS):
        raise ValueError("PSSHI header logo cell is no longer empty; refusing to overwrite its content")
    paragraphs = cell.xpath("./w:p", namespaces=NS)
    if not paragraphs:
        raise ValueError("PSSHI header logo cell has no paragraph anchor")

    rels_path = folder / "word" / "_rels" / "header1.xml.rels"
    rels_path.parent.mkdir(parents=True, exist_ok=True)
    if rels_path.is_file():
        rels_tree = etree.parse(str(rels_path), parser)
        rels_root = rels_tree.getroot()
    else:
        rels_root = etree.Element(f"{{{PKG_REL_NS}}}Relationships", nsmap={None: PKG_REL_NS})
        rels_tree = etree.ElementTree(rels_root)
    relation_ids = [int(value[3:]) for value in rels_root.xpath("./*[starts-with(@Id, 'rId')]/@Id") if value[3:].isdigit()]
    relation_id = f"rId{max(relation_ids, default=0) + 1}"

    media_dir = folder / "word" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    media_name = "psshi_organization_logo.png"
    media_path = media_dir / media_name
    with Image.open(logo_path) as opened:
        logo = ImageOps.exif_transpose(opened).convert("RGBA")
        logo.save(media_path, format="PNG")
        logo_width, logo_height = logo.size

    etree.SubElement(
        rels_root,
        f"{{{PKG_REL_NS}}}Relationship",
        Id=relation_id,
        Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
        Target=f"media/{media_name}",
    )
    rels_tree.write(str(rels_path), xml_declaration=True, encoding="UTF-8", standalone=True)

    content_types_path = folder / "[Content_Types].xml"
    content_tree = etree.parse(str(content_types_path), parser)
    content_root = content_tree.getroot()
    has_png_type = content_root.xpath("./*[local-name()='Default' and @Extension='png']")
    if not has_png_type:
        etree.SubElement(
            content_root,
            f"{{{CONTENT_NS}}}Default",
            Extension="png",
            ContentType="image/png",
        )
    content_tree.write(str(content_types_path), xml_declaration=True, encoding="UTF-8", standalone=True)

    cell_width_twips = cell.xpath("./w:tcPr/w:tcW/@w:w", namespaces=NS)
    max_width = min(int(cell_width_twips[0]) * 635, 0.52 * 914400) if cell_width_twips else 0.52 * 914400
    max_height = 0.5 * 914400
    scale = min(max_width / logo_width, max_height / logo_height)
    cx, cy = int(logo_width * scale), int(logo_height * scale)

    q = lambda namespace, local: f"{{{namespace}}}{local}"
    inline = etree.Element(q(WP_NS, "inline"), distT="0", distB="0", distL="0", distR="0")
    etree.SubElement(inline, q(WP_NS, "extent"), cx=str(cx), cy=str(cy))
    etree.SubElement(inline, q(WP_NS, "effectExtent"), l="0", t="0", r="0", b="0")
    doc_ids = [int(value) for value in root.xpath(".//wp:docPr/@id", namespaces={**NS, "wp": WP_NS}) if value.isdigit()]
    etree.SubElement(inline, q(WP_NS, "docPr"), id=str(max(doc_ids, default=0) + 1), name="Study Skills Organization Logo")
    frame = etree.SubElement(inline, q(WP_NS, "cNvGraphicFramePr"))
    etree.SubElement(frame, q(DRAWING_NS, "graphicFrameLocks"), noChangeAspect="1")
    graphic = etree.SubElement(inline, q(DRAWING_NS, "graphic"))
    graphic_data = etree.SubElement(graphic, q(DRAWING_NS, "graphicData"), uri=PIC_NS)
    pic = etree.SubElement(graphic_data, q(PIC_NS, "pic"))
    non_visual = etree.SubElement(pic, q(PIC_NS, "nvPicPr"))
    etree.SubElement(non_visual, q(PIC_NS, "cNvPr"), id="0", name=media_name)
    etree.SubElement(non_visual, q(PIC_NS, "cNvPicPr"))
    fill = etree.SubElement(pic, q(PIC_NS, "blipFill"))
    etree.SubElement(fill, q(DRAWING_NS, "blip"), {q(REL_NS, "embed"): relation_id})
    stretch = etree.SubElement(fill, q(DRAWING_NS, "stretch"))
    etree.SubElement(stretch, q(DRAWING_NS, "fillRect"))
    shape = etree.SubElement(pic, q(PIC_NS, "spPr"))
    transform = etree.SubElement(shape, q(DRAWING_NS, "xfrm"))
    etree.SubElement(transform, q(DRAWING_NS, "off"), x="0", y="0")
    etree.SubElement(transform, q(DRAWING_NS, "ext"), cx=str(cx), cy=str(cy))
    geometry = etree.SubElement(shape, q(DRAWING_NS, "prstGeom"), prst="rect")
    etree.SubElement(geometry, q(DRAWING_NS, "avLst"))
    run = etree.SubElement(paragraphs[0], q(WORD_NS, "r"))
    drawing = etree.SubElement(run, q(WORD_NS, "drawing"))
    drawing.append(inline)
    header_tree.write(str(header_path), xml_declaration=True, encoding="UTF-8", standalone=True)


def _render_radar(levels: Mapping[str, int], template_folder: Path, output_path: Path) -> None:
    document_rels_path = template_folder / "word" / "_rels" / "document.xml.rels"
    document_tree = etree.parse(str(document_rels_path))
    rels = document_tree.getroot()
    matching = []
    for rel in rels:
        target = rel.get("Target", "")
        resolved = posixpath.normpath(posixpath.join("word", target))
        if resolved == f"word/{PSSHI_RADAR_RELATIONSHIP_TARGET}":
            matching.append(rel.get("Id"))
    if len(matching) != 1:
        raise ValueError(
            f"PSSHI radar relationship target must resolve exactly once to {PSSHI_RADAR_RELATIONSHIP_TARGET}; "
            f"found {matching}"
        )
    document_path = template_folder / "word" / "document.xml"
    document_tree = etree.parse(str(document_path))
    referenced = document_tree.xpath(
        ".//a:blip[@r:embed=$rid]",
        namespaces={
            "a": DRAWING_NS,
            "r": REL_NS,
        },
        rid=matching[0],
    )
    if not referenced:
        raise ValueError(f"PSSHI radar media {PSSHI_RADAR_TARGET} is not referenced by document.xml")

    target = template_folder / "word" / "media" / PSSHI_RADAR_TARGET
    if not target.is_file():
        raise FileNotFoundError(f"PSSHI radar media target is missing: {target}")
    with Image.open(target) as background:
        target_width, target_height = background.size
    _register_bundled_iran_font()
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError("CairoSVG is required to render the PSSHI radar") from exc
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(
        bytestring=_shape_svg_text(chart_radar.radar(dict(levels))),
        write_to=str(output_path),
        output_width=target_width,
        output_height=target_height,
    )
    with Image.open(output_path) as rendered:
        if rendered.size != (target_width, target_height):
            raise RuntimeError("Rendered PSSHI radar dimensions do not match the DOCX image target")
        if max(rendered.convert("RGB").getextrema()[index][1] - rendered.convert("RGB").getextrema()[index][0] for index in range(3)) < 2:
            raise RuntimeError("Rendered PSSHI radar appears blank")
    shutil.copyfile(output_path, target)


def generate_study_skills_report_documents(
    *,
    template_path: Path | str,
    user_directory: Path | str,
    student_name: str,
    consultant_name: str,
    institute_name: str,
    phone: str,
    logo_path: str | None,
    labels: Mapping[str, object],
    psychological_order,
    psychological_scores: Mapping[str, object],
    output_docx_name: str,
    output_pdf_name: str,
) -> Path:
    """Build the PSSHI-backed official Report4 from one SCL context snapshot."""
    template_path = Path(template_path)
    if not template_path.is_file():
        raise FileNotFoundError(f"SCL PSSHI template is missing: {template_path}")
    output_dir = Path(user_directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    levels = build_psshi_levels(labels)
    selected_challenge = select_psshi_challenge(psychological_order, psychological_scores)
    resolved_logo = _resolve_logo(logo_path)

    folder = output_dir / "StudySkillsTree"
    unzip_word_file(template_path, folder)
    document_path = folder / "word" / "document.xml"
    document_tree = etree.parse(str(document_path), etree.XMLParser(remove_blank_text=False))
    _filter_psshi_blocks(document_tree, levels, selected_challenge)
    _relax_orphan_skill_page_breaks(document_tree)
    replacements = {
        "#name": student_name,
        "#con_name": consultant_name,
        "#inst_name": institute_name,
        "studentname": student_name,
        "conname": consultant_name,
        "instname": institute_name,
    }
    document_tree = _replace_scl_report3_text_tokens(document_tree, replacements)
    document_tree.write(str(document_path), xml_declaration=True, encoding="UTF-8", standalone=True)

    headers = sorted((folder / "word").glob("header*.xml"))
    if not headers:
        raise FileNotFoundError("PSSHI template has no Word header part")
    for header_path in headers:
        header_tree = etree.parse(str(header_path), etree.XMLParser(remove_blank_text=False))
        header_tree = _replace_scl_report3_text_tokens(header_tree, replacements)
        header_tree.write(str(header_path), xml_declaration=True, encoding="UTF-8", standalone=True)
    _add_header_logo(folder, resolved_logo)

    # The template's existing drawing relationship, not a guessed image ID, is the target.
    radar_media = output_dir / "psshi_radar.png"
    _render_radar(levels, folder, radar_media)
    radar_media.unlink(missing_ok=True)

    for part in [document_path, *headers]:
        tree = etree.parse(str(part))
        content = "".join(tree.getroot().itertext())
        unresolved = sorted(set(_MARKER_PATTERN.findall(content)))
        identity_tokens = [token for token in replacements if token in content]
        if unresolved:
            raise ValueError(f"Unresolved PSSHI conditional markers in {part.name}: {unresolved[:8]}")
        if identity_tokens:
            raise ValueError(f"Unresolved PSSHI identity placeholders in {part.name}: {identity_tokens}")

    destination_docx = output_dir / output_docx_name
    destination_pdf = output_dir / output_pdf_name
    zip_word_folder(folder, destination_docx, remove_folder=False)
    convert_docx_to_pdf(destination_docx, destination_pdf)
    return destination_pdf
