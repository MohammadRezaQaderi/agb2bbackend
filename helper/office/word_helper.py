import copy
import os
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
import uuid
import zipfile
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence, Tuple

import config
from lxml import etree
from PIL import Image, ImageOps
from config import REPORT1_TEMPLATE_PATH, REPORT2_TEMPLATE_PATH, REPORT3_TEMPLATE_PATH, REPORT5_TEMPLATE_PATH

# Template locations (config-driven)
REPORT1_TEMPLATE = Path(REPORT1_TEMPLATE_PATH)
REPORT2_TEMPLATE = Path(REPORT2_TEMPLATE_PATH)
REPORT3_TEMPLATE = Path(REPORT3_TEMPLATE_PATH)
REPORT5_TEMPLATE = Path(REPORT5_TEMPLATE_PATH)
DONT_REMOVE = ["Report1.pdf", "Report2.pdf", "Report3.pdf", "Report4.pdf", "Report5.pdf", "labels.json",
               "user_info.json", "report_text_replacements.json", "scl_calc_data.json"]
FIRST_REPORT_GRAPHIC_EFFECTS = (
    '<effectLst><outerShdw blurRad="107950" dist="12700" dir="5400000" algn="ctr"><srgbClr val="000000"/></outerShdw></effectLst>',
    '<scene3d><camera prst="orthographicFront"><rot lat="0" lon="0" rev="0"/></camera><lightRig rig="soft" dir="t"><rot lat="0" lon="0" rev="0"/></lightRig></scene3d>',
    '<sp3d contourW="44450" prstMaterial="matte"><bevelT w="63500" h="63500" prst="artDeco"/><contourClr><srgbClr val="FFFFFF"/></contourClr></sp3d>',
)


def get_xml_tag_without_ns(XMLTag: str) -> str:
    """فضای نام یک تگ XML را حذف می‌کند.
        ورودی:
            Tag: تگ
        خروجی:
            تگ بدون فضای نام
    """
    i = len(XMLTag) - 1
    while i >= 0 and XMLTag[i] not in (':', '}'):
        i -= 1
    if i == -1:
        return XMLTag
    else:
        return XMLTag[i + 1:]


def convert_docx_to_pdf(source_file: Path | str, destination_file: Path | str) -> None:
    """Convert a DOCX file to PDF through LibreOffice."""
    ok, message = convert_to_pdf(source_file, destination_file)
    if not ok:
        raise RuntimeError(f"Failed to convert Word report to PDF: {message}")


def convert_word_to_pdf(source_file: Path | str, destination_file: Path | str) -> None:
    """Backward-compatible alias for LibreOffice document conversion."""
    convert_docx_to_pdf(source_file, destination_file)


def _resolve_libreoffice_command() -> str:
    candidates = [config.LIBREOFFICE_PATH]
    if os.name == "nt":
        candidates.extend(
            [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                "soffice.exe",
            ]
        )
    else:
        candidates.extend(["soffice", "libreoffice"])

    for candidate in candidates:
        path = Path(candidate)
        if path.is_absolute() and path.exists():
            return str(path)
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError(
        "LibreOffice executable was not found. Install LibreOffice or set "
        "AG_LIBREOFFICE_PATH to the full path of soffice.exe "
        f"(configured value: {config.LIBREOFFICE_PATH!r})."
    )


def require_libreoffice() -> str:
    """Resolve LibreOffice or fail before the scheduler consumes queue jobs."""
    return _resolve_libreoffice_command()


def _convert_to_pdf_once(input_file: Path, output_file: Path) -> tuple[bool, str]:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    expected_output = output_file.parent / f"{input_file.stem}.pdf"
    output_file.unlink(missing_ok=True)
    if expected_output != output_file:
        expected_output.unlink(missing_ok=True)

    profile_dir = Path(tempfile.mkdtemp(prefix="agb2b-libreoffice-"))
    command = [
        _resolve_libreoffice_command(),
        f"-env:UserInstallation={profile_dir.resolve().as_uri()}",
        "--headless",
        "--nologo",
        "--nofirststartwizard",
        "--norestore",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_file.parent),
        str(input_file),
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=max(1, config.LIBREOFFICE_TIMEOUT_SECONDS),
        )
    except subprocess.TimeoutExpired as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        message = f"timed out after {config.LIBREOFFICE_TIMEOUT_SECONDS}s"
        if details:
            message += f": {details}"
        return False, message
    except OSError as exc:
        return False, str(exc)
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)

    if result.returncode != 0:
        error = (result.stderr or result.stdout or "LibreOffice conversion failed").strip()
        return False, f"exit code {result.returncode}: {error}"
    if not expected_output.exists():
        return False, "Output PDF not generated"
    if expected_output != output_file:
        expected_output.replace(output_file)
    return True, str(output_file)


def convert_to_pdf(input_file: str | Path, output_file: str | Path) -> tuple[bool, str]:
    """Convert a Word-compatible document to PDF with bounded retries."""
    source = Path(input_file)
    destination = Path(output_file)
    attempts = max(1, config.LIBREOFFICE_CONVERSION_ATTEMPTS)
    errors = []

    for attempt in range(1, attempts + 1):
        try:
            ok, message = _convert_to_pdf_once(source, destination)
        except Exception as exc:
            ok, message = False, str(exc)
        if ok:
            return True, message
        errors.append(f"attempt {attempt}/{attempts}: {message}")
        if attempt < attempts:
            delay = max(0, config.LIBREOFFICE_RETRY_DELAY_SECONDS) * attempt
            print(f"LibreOffice conversion failed ({errors[-1]}); retrying in {delay:.1f}s")
            time.sleep(delay)
    return False, "; ".join(errors)


def get_xml_tag_without_namespace(xml_tag: str) -> str:
    """Remove namespace from an XML tag name."""
    idx = len(xml_tag) - 1
    while idx >= 0 and xml_tag[idx] not in (":", "}"):
        idx -= 1
    return xml_tag if idx == -1 else xml_tag[idx + 1:]


def get_xml_tag_namespace(xml_tag: str) -> str:
    """Return the namespace portion of an XML tag name."""
    idx = len(xml_tag) - 1
    while idx >= 0 and xml_tag[idx] not in (":", "}"):
        idx -= 1
    return xml_tag[0: idx + 1]


def unzip_word_file(source_file: Path | str, output_folder: Path | str) -> None:
    """Unzip a docx file into a working folder."""
    with zipfile.ZipFile(str(source_file), "r") as zip_ref:
        zip_ref.extractall(str(output_folder))


def zip_word_folder(source_folder: Path | str, destination_file: Path | str, remove_folder: bool = True) -> None:
    """Zip a working folder back to a docx file."""
    src = Path(source_folder)
    dst = Path(destination_file)

    # `make_archive` appends .zip to the base name; the base name currently includes .docx
    archive_path = shutil.make_archive(str(dst), "zip", str(src))
    if remove_folder:
        shutil.rmtree(src)

    dst.unlink(missing_ok=True)
    Path(archive_path).rename(dst)


def load_xml_file(source_file: Path | str) -> etree.ElementTree:
    """Load an XML file into an ElementTree."""
    parser = etree.XMLParser(ns_clean=True, recover=True)
    return etree.parse(str(source_file), parser)


def save_xml_to_file(xml_tree: etree.ElementTree, destination_file: Path | str) -> None:
    """Persist an XML tree to disk."""
    xml_tree.write(str(destination_file), xml_declaration=True, encoding="UTF-8")


def replace_text_simple(xml_tree: etree.ElementTree, old_text: str, new_text: str) -> None:
    """Replace text within all XML nodes."""
    for item in xml_tree.iter():
        if item.text is not None:
            item.text = item.text.replace(old_text, new_text)


def replace_text(xml_tree: etree.ElementTree, old_text: str, new_text: str) -> etree.ElementTree:
    replace_text_simple(xml_tree, old_text, new_text.replace('\t', ' ').replace('\n', '|||-|||'))
    xml_str = etree.tostring(xml_tree, encoding='unicode', pretty_print=True)
    xml_str = xml_str.replace('|||-|||', '</w:t><w:br/><w:t>')
    xml_tree = etree.ElementTree(etree.fromstring(xml_str.encode('utf-8')))
    return xml_tree


def replace_texts(xml_tree: etree.ElementTree, old_texts: Sequence[str], new_texts: Sequence[str]) -> etree.ElementTree:
    """Replace a list of strings in an XML tree."""
    if xml_tree is None:
        return xml_tree

    replacements = zip(old_texts, new_texts)
    for item in xml_tree.iter():
        if item.text is not None:
            for old, new in replacements:
                #if new:
                item.text = item.text.replace(old, new.replace('\t', ' ').replace('\n', '|||-|||'))
            replacements = zip(old_texts, new_texts)  # restart iterator for the next node

    xml_str = etree.tostring(xml_tree, encoding='unicode', pretty_print=True)
    xml_str = xml_str.replace('|||-|||', '</w:t><w:br/><w:t>')
    xml_tree = etree.ElementTree(etree.fromstring(xml_str.encode('utf-8')))
    return xml_tree


def replace_texts_across_runs(
        xml_tree: etree.ElementTree,
        replacements: dict[str, str],
) -> etree.ElementTree:
    """Replace original paragraph tokens, including tokens split across Word runs."""
    if xml_tree is None:
        return xml_tree

    ordered = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
    for paragraph in (node for node in xml_tree.iter() if get_xml_tag_without_ns(node.tag) == "p"):
        text_nodes = [node for node in paragraph.iter() if get_xml_tag_without_ns(node.tag) == "t"]
        original = "".join(node.text or "" for node in text_nodes)
        matches = _find_report1_text_token_spans(original, ordered)
        for start, end, _, replacement in reversed(matches):
            _replace_text_range(text_nodes, start, end, replacement)
    return xml_tree


def _is_report1_word_char(char: str) -> bool:
    return char == "_" or char.isalnum() or unicodedata.category(char).startswith("M")


def _is_ascii_report1_placeholder(token: str) -> bool:
    return (
        token.startswith("#")
        and len(token) > 1
        and token[1].isascii()
        and (token[1].isalpha() or token[1] == "_")
    )


def _find_report1_text_token_spans(
        text: str,
        ordered_replacements: Sequence[Tuple[str, str]],
) -> list[Tuple[int, int, str, str]]:
    """Find non-overlapping token occurrences in original text using word boundaries."""
    matches = []
    index = 0
    while index < len(text):
        match = None
        for token, replacement in ordered_replacements:
            if not token or not text.startswith(token, index):
                continue
            end = index + len(token)
            if _is_report1_word_char(token[0]) and index and _is_report1_word_char(text[index - 1]):
                continue
            if end < len(text):
                if _is_ascii_report1_placeholder(token):
                    # ASCII-named placeholders can directly precede Persian prose
                    # (e.g. #inst_nameنام); only ASCII identifier chars extend them.
                    if text[end].isascii() and (text[end].isalnum() or text[end] == "_"):
                        continue
                elif _is_report1_word_char(token[-1]) and _is_report1_word_char(text[end]):
                    continue
            value = str(replacement).replace("\t", " ").replace("\r", " ").replace("\n", " ")
            match = (index, end, token, value)
            break
        if match is None:
            index += 1
        else:
            matches.append(match)
            index = match[1]
    return matches


def _replace_text_range(text_nodes: Sequence[etree._Element], start: int, end: int, replacement: str) -> None:
    """Apply one original-text span while retaining existing Word run placement."""
    cursor = 0
    start_index = end_index = None
    start_offset = end_offset = 0
    for index, node in enumerate(text_nodes):
        node_text = node.text or ""
        node_end = cursor + len(node_text)
        if start_index is None and (cursor <= start < node_end or (start == cursor and not node_text)):
            start_index = index
            start_offset = start - cursor
        if cursor < end <= node_end:
            end_index = index
            end_offset = end - cursor
            break
        cursor = node_end

    if start_index is None or end_index is None:
        return
    first_text = text_nodes[start_index].text or ""
    if start_index == end_index:
        text_nodes[start_index].text = first_text[:start_offset] + replacement + first_text[end_offset:]
        return

    last_text = text_nodes[end_index].text or ""
    text_nodes[start_index].text = first_text[:start_offset] + replacement
    for index in range(start_index + 1, end_index):
        text_nodes[index].text = ""
    text_nodes[end_index].text = last_text[end_offset:]


def _polish_report1_question_mark_size(xml_tree: etree.ElementTree) -> None:
    """Reduce oversized standalone Persian question marks in Report 1 callouts."""
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    for paragraph in (node for node in xml_tree.iter() if node.tag == f"{{{word_ns}}}p"):
        text = "".join(
            node.text or ""
            for node in paragraph.iter()
            if node.tag == f"{{{word_ns}}}t"
        ).strip()
        if text != "؟":
            continue
        for size_tag in (f"{{{word_ns}}}sz", f"{{{word_ns}}}szCs"):
            for size in paragraph.iter(size_tag):
                size.set(f"{{{word_ns}}}val", "30")


def _find_unresolved_report1_tokens(text: str, replacement_keys: Iterable[str]) -> list[str]:
    """Find unresolved original template markers, respecting Persian word boundaries."""
    replacement_keys = {key for key in replacement_keys if key}
    candidates = set(replacement_keys)
    candidates.add("سلام")
    candidates.update(re.findall(r"#[A-Za-z_][A-Za-z0-9_]*", text))
    candidates.update(re.findall(r"#[\u0600-\u06FF][\w\u0600-\u06FF]*", text))
    candidates.update(re.findall(r"سلا{2,}م", text))
    ordered = [(token, "") for token in sorted(candidates, key=len, reverse=True)]
    return sorted({token for _, _, token, _ in _find_report1_text_token_spans(text, ordered)
                   if token not in replacement_keys})


def remove_labeled_texts(xml_tree: etree.ElementTree, labels: list[str], excepts: list[str]):
    if xml_tree is None:
        return xml_tree

    to_remove = set()
    open_tag = False

    # عناصر xml ورد رو بررسی کن
    for item in xml_tree.iter():
        tag = get_xml_tag_without_ns(item.tag)
        # اگر عنصر متن بود
        if tag == 't' and item.text:
            # حذف نشانه و پاراگراف‌های داخل آن مرتبط با فهرست labels
            for l in labels:
                # اگر در فهرست تگ‌ها موجود بود
                if item.text and (item.text == l or open_tag):
                    if item.text == l:
                        open_tag = not open_tag
                    p = item.getparent()
                    while p is not None and get_xml_tag_without_ns(p.tag) != 'p':
                        p = p.getparent()
                    if p is not None:
                        to_remove.add(p)
            # حذف نشانه و نگهداشتن پاراگراف‌های داخل آن مرتبط با فهرست excepts
            for e in excepts:
                # اگر در فهرست تگ‌ها موجود بود
                if item.text and item.text == e:
                    p2 = item.getparent()
                    while p2 is not None and get_xml_tag_without_ns(p2.tag) != 'p':
                        p2 = p2.getparent()
                    if p2 is not None:
                        to_remove.add(p2)

    # حذف پاراگراف‌های نشان‌دار شده
    for r in to_remove:
        # for i in r.iter():
        #     if get_xml_tag_without_ns(i.tag) == 't':
        #         print(i.text)
        parent = r.getparent()
        if parent is not None:
            parent.remove(r)

    return xml_tree
    # result = etree.tostring(xml, encoding='unicode', pretty_print=True)
    # print(result)


def replace_image_in_word_folder(source_folder: Path | str, old_image_file: str, new_image_file: Path | str) -> None:
    """Replace a single image inside the docx media folder."""
    old_file = Path(source_folder) / "word" / "media" / old_image_file
    if not old_file.is_file():
        raise FileNotFoundError(f"DOCX media target does not exist: {old_image_file}")
    source = Path(new_image_file)
    if old_file.suffix.lower() in {".jpg", ".jpeg"} and source.suffix.lower() not in {".jpg", ".jpeg"}:
        with Image.open(source) as image:
            image.convert("RGB").save(old_file, format="JPEG", quality=95)
        return
    shutil.copyfile(source, old_file)


def replace_images_in_word_folder(
        source_folder: Path | str, old_image_files: Sequence[str], new_image_files: Sequence[Path | str]
) -> None:
    """Replace multiple images inside the docx media folder."""
    for old, new in zip(old_image_files, new_image_files):
        replace_image_in_word_folder(source_folder, old, new)


def _replace_report2_logo(source_folder: Path | str, source_file: Path | str) -> None:
    """Replace Report2's shared header logo while preserving its media aspect ratio."""
    target = Path(source_folder) / "word" / "media" / "image15.jpeg"
    if not target.is_file():
        raise FileNotFoundError("DOCX media target does not exist: image15.jpeg")
    with Image.open(target) as original:
        target_size = original.size
    with Image.open(source_file) as opened:
        logo = ImageOps.exif_transpose(opened).convert("RGBA")
    logo.thumbnail(target_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", target_size, "white")
    x = (target_size[0] - logo.width) // 2
    y = (target_size[1] - logo.height) // 2
    canvas.paste(logo, (x, y), logo.getchannel("A"))
    canvas.save(target, format="JPEG", quality=95)


def _replace_scl_report3_image(source_folder: Path | str, target_name: str, source_file: Path | str) -> None:
    """Replace Report3 media without distorting the source image's aspect ratio."""
    target = Path(source_folder) / "word" / "media" / target_name
    source = Path(source_file)
    if not target.is_file():
        raise FileNotFoundError(f"SCL Report3 template media target is missing: {target_name}")
    if not source.is_file():
        raise FileNotFoundError(f"SCL Report3 replacement asset is missing: {source}")
    with Image.open(target) as target_image:
        target_size = target_image.size
        target_format = target_image.format or target.suffix.lstrip(".").upper()
        target_mode = target_image.mode
    with Image.open(source) as opened:
        replacement = ImageOps.exif_transpose(opened).convert("RGBA")
    replacement.thumbnail(target_size, Image.Resampling.LANCZOS)
    if target_mode == "RGBA":
        canvas = Image.new("RGBA", target_size, (255, 255, 255, 0))
        canvas.alpha_composite(replacement, ((target_size[0] - replacement.width) // 2,
                                             (target_size[1] - replacement.height) // 2))
    else:
        canvas = Image.new("RGB", target_size, "white")
        canvas.paste(replacement, ((target_size[0] - replacement.width) // 2,
                                   (target_size[1] - replacement.height) // 2), replacement.getchannel("A"))
    canvas.save(target, format=target_format)


def _refresh_ids(row: etree._Element) -> None:
    """Refresh various ids in a table row to keep the document valid."""
    for element in row.iter():
        for att in list(element.attrib):
            if get_xml_tag_without_namespace(att) in ("paraId", "editId"):
                element.set(att, uuid.uuid4().hex[:8].upper())

        if get_xml_tag_without_namespace(element.tag) == "AlternateContent":
            anchor_id = uuid.uuid4().hex[:8].upper()
            for child in element.iter():
                for att in child.attrib:
                    if get_xml_tag_without_namespace(att) == "anchorId":
                        child.set(att, anchor_id)

        elif get_xml_tag_without_namespace(element.tag) == "docPr":
            for att in element.attrib:
                if get_xml_tag_without_namespace(att) == "id":
                    new_id = str(int(uuid.uuid4().hex[:8], base=16))
                    while len(new_id) < 9:
                        new_id = "1" + new_id
                    while len(new_id) > 9:
                        new_id = new_id[:-1]
                    element.set(att, new_id)

        elif get_xml_tag_without_namespace(element.tag) == "roundrect":
            for att in list(element.attrib):
                if get_xml_tag_without_namespace(att) == "id":
                    new_id = str(int(uuid.uuid4().hex[:3], base=16))
                    while len(new_id) < 4:
                        new_id = "0" + new_id
                    while len(new_id) > 4:
                        new_id = new_id[:-1]
                    element.set(att, f"_x0000_s{new_id}")
                elif get_xml_tag_without_namespace(att) == "gfxdata":
                    element.attrib.pop(att)


def insert_values_into_table(
        xml_tree: etree.ElementTree, fields: List[str], values: List[List[str]], bookmark: str | None = None
) -> etree.ElementTree:
    """Insert records into a Word table template using provided fields."""
    for item in xml_tree.iter():
        if get_xml_tag_without_namespace(item.tag) != "tbl":
            continue

        bookmark_matches = bookmark is None
        if bookmark is not None:
            for element in item.iter():
                if get_xml_tag_without_namespace(element.tag) == "bookmarkStart":
                    for key in element.attrib:
                        if get_xml_tag_without_namespace(key) == "name" and element.attrib.get(key) == bookmark:
                            bookmark_matches = True

        if not bookmark_matches:
            continue

        template_row = None
        row_number = 0
        ns = None
        ns_map_key = None
        for element in list(item):
            if get_xml_tag_without_namespace(element.tag) == "tr":
                row_number += 1
                if row_number == 2:
                    template_row = copy.deepcopy(element)
                    ns = get_xml_tag_namespace(element.tag)
                    ns_value = ns[1: len(ns) - 1]
                    ns_map_key = list(item.nsmap.keys())[list(item.nsmap.values()).index(ns_value)]
                if row_number > 1:
                    item.remove(element)

        if template_row is None:
            continue

        current_row_index = len(list(item)) - 1
        for record in values:
            # Work on a copy of the template row
            replaced_row = copy.deepcopy(template_row)

            # `replace_texts` expects an ElementTree and returns an ElementTree.
            # Wrap the row in a temporary ElementTree, run replacements, then
            # take the root element back so we can insert it into the table.
            row_tree = etree.ElementTree(replaced_row)
            row_tree = replace_texts(row_tree, fields, record)
            replaced_row = row_tree.getroot()

            _refresh_ids(replaced_row)
            current_row_index += 1
            item.insert(current_row_index, replaced_row)
    return xml_tree


def change_graphic_background_color(
        xml_tree: etree.ElementTree, back_color: str, field: str | None = None, bookmark: str | None = None
) -> etree.ElementTree:
    """Change the background color of a graphic element when bookmark/field matches."""
    for item in xml_tree.iter():
        if get_xml_tag_without_namespace(item.tag) != "graphic":
            continue
        bookmark_matches = bookmark is None
        if bookmark is not None:
            for element in item.iter():
                if get_xml_tag_without_namespace(element.tag) == "bookmarkStart":
                    for key in element.attrib:
                        if get_xml_tag_without_namespace(key) == "name" and element.attrib.get(key) == bookmark:
                            bookmark_matches = True

        field_matches = field is None
        if field is not None:
            for element in item.iter():
                if get_xml_tag_without_namespace(element.tag) == "t":
                    if element.text is not None and element.text.find(field) > -1:
                        field_matches = True

        if not (bookmark_matches and field_matches):
            continue

        for element in item.iter():
            if get_xml_tag_without_namespace(element.tag) != "spPr":
                continue

            ln = None
            ns = None
            for t in list(element):
                ns = get_xml_tag_namespace(t.tag)
                if get_xml_tag_without_namespace(t.tag) == "ln":
                    ln = copy.deepcopy(t)
                if get_xml_tag_without_namespace(t.tag) in ("solidFill", "noFill", "ln"):
                    element.remove(t)

            if ns is None:
                continue

            ns_value = ns[1: len(ns) - 1]
            ns_map_key = list(item.nsmap.keys())[list(item.nsmap.values()).index(ns_value)]

            solid_xml = (
                f'<solidFill xmlns:{ns_map_key}="{ns_value}"><srgbClr val="{back_color}"/></solidFill>'
            )
            solid_xml = solid_xml.replace("<", f"<{ns_map_key}:").replace(f"<{ns_map_key}:/", f"</{ns_map_key}:")
            solid_fill = etree.fromstring(solid_xml)
            element.append(solid_fill)
            if ln is not None:
                element.append(ln)

            inline = item.getparent()
            for att in list(inline.attrib):
                if get_xml_tag_without_namespace(att) == "anchorId":
                    anchor_id = inline.attrib.get(att)
                    for r in xml_tree.iter():
                        if get_xml_tag_without_namespace(r.tag) in ("roundrect", "shape"):
                            for attr in list(r.attrib):
                                if get_xml_tag_without_namespace(attr) == "anchorId" and r.attrib.get(
                                        attr) == anchor_id:
                                    r.set("fillcolor", f"#{back_color.lower()}")
                elif get_xml_tag_without_namespace(att) == "gfxdata":
                    inline.attrib.pop(att)
    return xml_tree
    # for item in xml_tree.iter():
    #     # یافتن شیء گرافیکی
    #     if get_xml_tag_without_ns(item.tag) == 'graphic':
    #         # یافتن بوک‌مارک مرتبط
    #         BookmarkCheck = False
    #         if bookmark == None:
    #             BookmarkCheck = True
    #         else:
    #             for element in item.iter():
    #                 if get_xml_tag_without_ns(element.tag) == 'bookmarkStart':
    #                     for k in element.attrib:
    #                         if get_xml_tag_without_ns(k) == 'name' and element.attrib.get(k) == bookmark:
    #                             BookmarkCheck = True
    #
    #         # یافتن فیلد مرتبط
    #         FieldCheck = False
    #         if field == None:
    #             FieldCheck = True
    #         else:
    #             for element in item.iter():
    #                 if get_xml_tag_without_ns(element.tag) == 't':
    #                     if element.text != None and element.text.find(field) > -1:
    #                         FieldCheck = True
    #
    #         # اگر بوک‌مارک و فیلد یافت شد
    #         if BookmarkCheck and FieldCheck:
    #             for element in item.iter():
    #                 # یافتن مشخصات شیء
    #                 if get_xml_tag_without_ns(element.tag) == 'spPr':
    #                     # پیدا کردن فضای نام تگ‌های زیرمجموعه
    #                     for t in element:
    #                         ns = get_xml_tag_namespace(t.tag)
    #                         # پیدا کردن تگ ln برای جابجایی بعد از تگ solidFill
    #                         # در صورت عدم جابجایی، رنگ جدید اعمال نمی‌شود !!!!
    #                         if get_xml_tag_without_ns(t.tag) == 'ln':
    #                             ln = copy.deepcopy(t)
    #                         # حذف تگ‌های موجود رنگ پس‌زمینه یا تعریف بدون رنگ پس‌زمینه
    #                         if get_xml_tag_without_ns(t.tag) in ('solidFill', 'noFill', 'ln'):
    #                             element.remove(t)
    #                         # افزودن تگ‌های جدید
    #
    #                     # حذف کروشه از فضای نام
    #                     elns = ns[1:len(ns) - 1]
    #                     # تعیین مخفف فضای نام تگ زیرمجموعه
    #                     map = list(item.nsmap.keys())[list(item.nsmap.values()).index(elns)]
    #                     # افزودن رنگ جدید
    #                     s = '<solidFill xmlns:' + map + '=' + '"' + elns + '"><srgbClr val="' + back_color + '"/></solidFill>'
    #                     s = s.replace('<', '<' + map + ':')
    #                     s = s.replace('<' + map + ':/', '</' + map + ':')
    #                     solidFill = etree.fromstring(s)
    #                     element.append(solidFill)
    #                     # جابجایی ln بعد از تعریف رنگ جدید
    #                     if ln != None:
    #                         element.append(ln)
    #
    #                         # تغییر رنگ پس‌زمینه در شیء جایگزین-تگ AlternateContent
    #                     inline = item.getparent()
    #                     for att in inline.attrib:
    #                         if get_xml_tag_without_ns(att) == 'anchorId':
    #                             anchorId = inline.attrib.get(att)
    #
    #                             for r in xml_tree.iter():
    #                                 if get_xml_tag_without_ns(r.tag) in (
    #                                         'roundrect', 'shape'):  # می‌تواند انواع دیگر هم تعریف شود
    #                                     for att in r.attrib:
    #                                         # دریافت شناسه منحصر به فرد شیء
    #                                         if get_xml_tag_without_ns(att) == 'anchorId':
    #                                             if r.attrib.get(att) == anchorId:
    #                                                 # تغییر رنگ در تعریف شیء
    #                                                 r.set('fillcolor', '#' + back_color.lower())
    #                                                 # for shapeSubelement in r.iter():
    #                                                 #     if get_xml_tag_without_ns(shapeSubelement.tag) == 'fill':
    #                                                 #         r.remove(shapeSubelement)
    #
    #                         # حذف تگ اطلاعات اضافه‌تر شیء
    #                         elif get_xml_tag_without_ns(att) == 'gfxdata':
    #                             inline.attrib.pop(att)
    #
    #                             # ساختار درخت XML شیء
    #                     # AlternateControl
    #                     #   Choice
    #                     #     drawing
    #                     #       inline
    #                     #         docPr
    #                     #           graphic
    #                     #             graphicData
    #                     #               wsp
    #                     #                 style
    #                     #                 txbx
    #                     #                 spPr
    #                     #   Fallback
    #                     #     pict
    #                     #       roundrect
    #                     #         textbox
    #                     #           txbxContent
    #
    # return xml_tree


def change_graphic_effect(
        xml_tree: etree.ElementTree,
        style_tags: Sequence[str],
        replaced_styles: Sequence[str],
        field: str | None = None,
        bookmark: str | None = None,
) -> etree.ElementTree:
    """Replace style nodes of a graphic element when bookmark/field matches."""
    for item in xml_tree.iter():
        if get_xml_tag_without_namespace(item.tag) != "graphic":
            continue

        # Check Bookmark
        bookmark_matches = bookmark is None
        if bookmark is not None:
            for element in item.iter():
                if get_xml_tag_without_namespace(element.tag) == "bookmarkStart":
                    for key in element.attrib:
                        if get_xml_tag_without_namespace(key) == "name" and element.attrib.get(key) == bookmark:
                            bookmark_matches = True

        # Check Field (Text content)
        field_matches = field is None
        if field is not None:
            for element in item.iter():
                if get_xml_tag_without_namespace(element.tag) == "t":
                    # Check if the field text exists within the element text
                    if element.text is not None and field in element.text:
                        field_matches = True

        if not (bookmark_matches and field_matches):
            continue

        # Apply changes to spPr (Shape Properties)
        for element in item.iter():
            if get_xml_tag_without_namespace(element.tag) != "spPr":
                continue

            # 1. Determine the namespace URI from existing children or the document map
            ns_uri = None
            if len(element) > 0:
                # Try to grab namespace from the first child (usually 'a' namespace)
                tag_ns = get_xml_tag_namespace(element[0].tag)
                if tag_ns.startswith("{") and tag_ns.endswith("}"):
                    ns_uri = tag_ns[1:-1]

            # Fallback: look for 'main' drawingml namespace in the map
            if ns_uri is None:
                for uri in item.nsmap.values():
                    if "drawingml" in uri and "main" in uri:
                        ns_uri = uri
                        break

            if ns_uri is None:
                continue

            # 2. Remove existing tags that match the style_tags list
            for t in list(element):
                if get_xml_tag_without_namespace(t.tag) in style_tags:
                    element.remove(t)

            # 3. Parse and append the new style XML safely
            for style_xml in replaced_styles:
                try:
                    # Parse the raw XML string
                    new_node = etree.fromstring(style_xml)

                    # Recursively apply the correct namespace to the new node and its children
                    def apply_namespace(node, uri):
                        # Only apply if the tag doesn't already have a namespace
                        if '}' not in node.tag:
                            node.tag = f"{{{uri}}}{node.tag}"
                        for child in node:
                            apply_namespace(child, uri)

                    apply_namespace(new_node, ns_uri)
                    element.append(new_node)

                except etree.XMLSyntaxError as e:
                    print(f"Error parsing style XML: {e}")
                    continue

    return xml_tree


def replace_texts_in_headers(source_folder: Path | str, old_texts: Sequence[str], new_texts: Sequence[str]) -> None:
    """Replace text inside all header XML parts."""
    for header in Path(source_folder).glob(r"word/header*.xml"):
        xml = load_xml_file(header)
        xml = replace_texts(xml, old_texts, new_texts)
        save_xml_to_file(xml, header)


def replace_texts_in_footers(source_folder: Path | str, old_texts: Sequence[str], new_texts: Sequence[str]) -> None:
    """Replace text inside all footer XML parts."""
    for footer in Path(source_folder).glob(r"word/footer*.xml"):
        xml = load_xml_file(footer)
        xml = replace_texts(xml, old_texts, new_texts)
        save_xml_to_file(xml, footer)


def remove_unneeded_files(user_directory: Path | str, files_to_keep: Iterable[str]) -> None:
    """Remove every file in the directory except the ones we need to keep."""
    base_dir = Path(user_directory)
    for file_path in base_dir.iterdir():
        if file_path.is_file() and file_path.name not in files_to_keep:
            file_path.unlink()
        else:
            continue


def generate_first_report_documents(
        tag_names: Sequence[str],
        user_report_info: Sequence[str],
        image_names: Sequence[str],
        user_report_pictures: Sequence[Path | str],
        user_directory: Path | str,
        effects: Sequence[Sequence[str]],
        color_handle_tags: Sequence[str],
        color_handle_colors: Sequence[str],
        phone: str,
) -> None:
    """Generate first report docx/pdf with provided data and assets."""
    try:
        del effects, color_handle_tags, color_handle_colors
        replacements = dict(zip(tag_names, user_report_info))
        with tempfile.TemporaryDirectory(prefix="ag-report1-", dir=user_directory) as temporary:
            folder_word = Path(temporary) / "docx"
            unzip_word_file(REPORT1_TEMPLATE, folder_word)
            replace_images_in_word_folder(folder_word, image_names, user_report_pictures)

            xml_parts = [folder_word / "word" / "document.xml"]
            xml_parts.extend((folder_word / "word").glob("header*.xml"))
            xml_parts.extend((folder_word / "word").glob("footer*.xml"))
            for xml_part in xml_parts:
                tree = load_xml_file(xml_part)
                unresolved = []
                for paragraph in (node for node in tree.iter() if get_xml_tag_without_ns(node.tag) == "p"):
                    text = "".join(
                        node.text or "" for node in paragraph.iter() if get_xml_tag_without_ns(node.tag) == "t"
                    )
                    unresolved.extend(_find_unresolved_report1_tokens(text, replacements))
                if unresolved:
                    raise ValueError(f"Unresolved AG Report 1 template tokens in {xml_part.name}: {unresolved[:3]}")
                tree = replace_texts_across_runs(tree, replacements)
                _polish_report1_question_mark_size(tree)
                save_xml_to_file(tree, xml_part)

            destination_docx = Path(user_directory) / f"Report1{phone}.docx"
            destination_pdf = Path(user_directory) / "Report1.pdf"
            zip_word_folder(folder_word, destination_docx, remove_folder=False)
            convert_docx_to_pdf(destination_docx, destination_pdf)
            if not destination_pdf.is_file() or destination_pdf.stat().st_size == 0:
                raise RuntimeError("AG Report 1 PDF was not created or is empty")
        remove_unneeded_files(user_directory, [*DONT_REMOVE, destination_docx.name])
    except Exception as exc:
        raise RuntimeError("Failed to generate first report documents") from exc


def generate_second_report_documents(
        user_directory: Path | str,
        fields_matched: Mapping[int, Sequence],
        fields_benchmark_name: Mapping[int, Sequence],
        image_names: Sequence[str],
        user_report_pictures: Sequence[Path | str],
        tag_names: Sequence[str],
        user_report_info: Sequence[str],
        colors_tag: Sequence[str],
        colors_color: Sequence[str],
        phone: str,
) -> None:
    """Generate second report docx/pdf with provided data and assets."""
    try:
        destination_docx = Path(user_directory) / f"Report2{phone}.docx"
        destination_pdf = Path(user_directory) / "Report2.pdf"
        with tempfile.TemporaryDirectory(prefix="ag-report2-", dir=user_directory) as temporary:
            folder_word = Path(temporary) / "docx"
            unzip_word_file(REPORT2_TEMPLATE, folder_word)
            tree_path = folder_word / "word"
            for image_name, image_path in zip(image_names, user_report_pictures):
                if image_name == "image15.jpeg":
                    _replace_report2_logo(folder_word, image_path)
                else:
                    replace_image_in_word_folder(folder_word, image_name, image_path)

            replacements = {
                key: _persianize_user_visible_numbers(value)
                for key, value in zip(tag_names, user_report_info)
            }
            tree = replace_texts_across_runs(load_xml_file(tree_path / "document.xml"), replacements)

            if set(fields_matched) != set(fields_benchmark_name):
                raise ValueError(
                    "Report2 branch data/template mapping differs: "
                    f"data={sorted(fields_matched)}, template={sorted(fields_benchmark_name)}"
                )
            for branch_id in sorted(fields_benchmark_name):
                benchmark = fields_benchmark_name[branch_id]
                recommended_fields = benchmark[0][1]
                recommended_placeholder = recommended_fields[0]
                if not _insert_report2_table_values(
                    tree,
                    recommended_fields,
                    _persianize_table_values(fields_matched[branch_id][0]),
                    recommended_placeholder,
                ):
                    raise ValueError(
                        f"Report2 recommended-field table not found for BranchId {branch_id}: "
                        f"{recommended_placeholder}"
                    )
                other_fields = benchmark[1][1]
                if not _insert_report2_other_values(
                    tree,
                    other_fields,
                    _persianize_table_values(fields_matched[branch_id][1]),
                    other_fields[0],
                    other_fields[1],
                ):
                    raise ValueError(
                        f"Report2 other-fields table not found for BranchId {branch_id}: {other_fields[0]}"
                    )

            save_xml_to_file(tree, tree_path / "document.xml")
            header_replacements = {
                key: replacements[key]
                for key in ("#name", "#inst_name", "#con_name")
                if key in replacements
            }
            for xml_part in [*tree_path.glob("header*.xml"), *tree_path.glob("footer*.xml")]:
                header_tree = replace_texts_across_runs(load_xml_file(xml_part), header_replacements)
                save_xml_to_file(header_tree, xml_part)

            zip_word_folder(folder_word, destination_docx, remove_folder=False)
            convert_docx_to_pdf(destination_docx, destination_pdf)
        remove_unneeded_files(user_directory, DONT_REMOVE)
    except Exception as exc:
        raise RuntimeError(f"Failed to generate second report documents: {exc}") from exc


def _persianize_user_visible_numbers(value: object) -> str:
    """Convert Western digits in Report2 presentation strings only."""
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _persianize_table_values(rows: Sequence[Sequence[object]]) -> list[list[str]]:
    return [[_persianize_user_visible_numbers(value) for value in row] for row in rows]


def _insert_report2_table_values(
        xml_tree: etree._ElementTree,
        fields: Sequence[str],
        values: Sequence[Sequence[str]],
        placeholder: str,
) -> bool:
    """Fill the unique row template identified by its visible Persian token."""
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    matches = []
    for table in (node for node in xml_tree.iter() if node.tag == f"{{{word_ns}}}tbl"):
        rows = [node for node in table if node.tag == f"{{{word_ns}}}tr"]
        if len(rows) < 2:
            continue
        row_text = "".join(
            node.text or ""
            for node in rows[1].iter()
            if node.tag == f"{{{word_ns}}}t"
        )
        if placeholder not in row_text:
            continue
        matches.append((table, rows))

    if len(matches) > 1:
        raise ValueError(f"Report2 placeholder is ambiguous in the template: {placeholder}")
    if not matches:
        return False

    table, rows = matches[0]
    _set_report2_row_property(rows[0], "tblHeader")
    template_row = copy.deepcopy(rows[1])
    for row in rows[1:]:
        _set_report2_row_property(row, "cantSplit")
    for row in rows[1:]:
        table.remove(row)
    position = list(table).index(rows[0]) + 1
    for record in values:
        row = copy.deepcopy(template_row)
        _set_report2_row_property(row, "cantSplit")
        replaced = replace_texts_across_runs(
            etree.ElementTree(row),
            {str(old): _persianize_user_visible_numbers(new) for old, new in zip(fields, record)},
        ).getroot()
        _refresh_ids(replaced)
        table.insert(position, replaced)
        position += 1
    return True


def _set_report2_row_property(row: etree._Element, property_name: str) -> None:
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    tr_pr = row.find(f"{{{word_ns}}}trPr")
    if tr_pr is None:
        tr_pr = etree.Element(f"{{{word_ns}}}trPr")
        row.insert(0, tr_pr)
    if tr_pr.find(f"{{{word_ns}}}{property_name}") is None:
        etree.SubElement(tr_pr, f"{{{word_ns}}}{property_name}")


def _insert_report2_other_values(
        xml_tree: etree._ElementTree,
        fields: Sequence[str],
        values: Sequence[Sequence[str]],
        row_placeholder: str,
        value_placeholder: str,
) -> bool:
    """Fill an other-fields table selected by its branch-specific first cell."""
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    for table in (node for node in xml_tree.iter() if node.tag == f"{{{word_ns}}}tbl"):
        rows = [node for node in table if node.tag == f"{{{word_ns}}}tr"]
        if len(rows) < 2:
            continue
        first_text = "".join(
            node.text or ""
            for node in rows[1].findall(".//w:tc[1]//w:t", {"w": word_ns})
        )
        if row_placeholder not in first_text or value_placeholder not in "".join(
            node.text or "" for node in rows[1].iter() if node.tag == f"{{{word_ns}}}t"
        ):
            continue
        row_texts = [
            "".join(node.text or "" for node in row.iter() if node.tag == f"{{{word_ns}}}t")
            for row in rows[1:]
        ]
        if any("T1" in text or "T2" in text for text in row_texts):
            continue
        return _insert_report2_table_values(xml_tree, fields, values, row_placeholder)
    return False


_SCL_REPORT3_MARKER_RE = re.compile(
    r"#[A-Za-z_][A-Za-z0-9_]*|(?<![A-Za-z0-9_])(?:"
    r"[A-Za-z][A-Za-z0-9_]*(?:statefast|interfast|scorefast|fast|advice[1-4]|_sh|_so)"
    r"|vav|vaav|vaaav|vaaaav|vaaaaav|vaaaaaav|waw|waaw|waaaw|waaaaw|waaaaaw"
    r"|zaz|zaaz|zaaaz|zaaaaz|zaaaaaz|studentname|Studentname|instname|conname)"
    r"(?![A-Za-z0-9_])"
)


def _report3_template_markers(xml_tree: etree.ElementTree) -> set[str]:
    markers = set()
    for paragraph in (node for node in xml_tree.iter() if get_xml_tag_without_ns(node.tag) == "p"):
        text = "".join(
            node.text or "" for node in paragraph.iter() if get_xml_tag_without_ns(node.tag) == "t"
        )
        markers.update(_SCL_REPORT3_MARKER_RE.findall(text))
    return markers


def _replace_scl_report3_text_tokens(
        xml_tree: etree.ElementTree,
        replacements: Mapping[str, str],
) -> etree.ElementTree:
    """Replace Report3 tokens across runs, allowing Persian text adjacency."""
    if xml_tree is None:
        return xml_tree
    ordered = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
    for paragraph in (node for node in xml_tree.iter() if get_xml_tag_without_ns(node.tag) == "p"):
        text_nodes = [node for node in paragraph.iter() if get_xml_tag_without_ns(node.tag) == "t"]
        original = "".join(node.text or "" for node in text_nodes)
        matches = []
        index = 0
        while index < len(original):
            found = None
            for token, replacement in ordered:
                if not token or not original.startswith(token, index):
                    continue
                end = index + len(token)
                if token.startswith("#"):
                    if end < len(original) and original[end].isascii() and (
                        original[end].isalnum() or original[end] == "_"
                    ):
                        continue
                elif token.isascii():
                    if index and original[index - 1].isascii() and _is_report1_word_char(original[index - 1]):
                        continue
                    if end < len(original) and original[end].isascii() and _is_report1_word_char(original[end]):
                        continue
                elif _is_report1_word_char(token[0]) and index and _is_report1_word_char(original[index - 1]):
                    continue
                elif end < len(original) and _is_report1_word_char(token[-1]) and _is_report1_word_char(original[end]):
                    continue
                value = str(replacement).replace("\t", " ").replace("\r", " ").replace("\n", " ")
                found = (index, end, token, value)
                break
            if found is None:
                index += 1
            else:
                matches.append(found)
                index = found[1]
        for start, end, _, replacement in reversed(matches):
            _replace_text_range(text_nodes, start, end, replacement)
    return xml_tree


def _insert_scl_report3_roadmap_images(
        xml_tree: etree.ElementTree,
        word_folder: Path,
        roadmap_images: Mapping[str, Path | str],
) -> None:
    """Replace each floating native roadmap group with one flowing inline image."""
    expected_markers = {
        "surface": ("addictstatefast", "bodystatefast", "sleepstatefast", "gamestatefast", "futurestatefast", "studystatefast"),
        "psych": ("anxstatefast", "depstatefast", "ocdstatefast", "motivestatefast", "confstatefast"),
        "root": ("adhdstatefast", "familystatefast", "interpstatefast", "idealstatefast", "ptsdstatefast"),
    }
    if set(roadmap_images) != set(expected_markers):
        raise ValueError("Report3 requires surface, psych, and root roadmap images")

    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    wp_ns = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    a_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
    pic_ns = "http://schemas.openxmlformats.org/drawingml/2006/picture"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package_rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    root = xml_tree.getroot()
    paragraphs = [node for node in root.iter() if get_xml_tag_without_ns(node.tag) == "p"]
    selected = {}
    for layer, markers in expected_markers.items():
        found = []
        for paragraph in paragraphs:
            text = "".join(node.text or "" for node in paragraph.iter() if get_xml_tag_without_ns(node.tag) == "t")
            if all(marker in text for marker in markers) and paragraph.xpath(".//*[local-name()='anchor']"):
                found.append((paragraph, text))
        if len(found) != 1:
            raise ValueError(f"Expected one Report3 {layer} roadmap paragraph; found {len(found)}")
        paragraph, text = found[0]
        missing = [marker for marker in markers if marker not in text]
        if missing or not paragraph.xpath(".//*[local-name()='anchor']"):
            raise ValueError(f"Report3 {layer} roadmap structure is incomplete: {missing}")
        if paragraph.xpath(".//*[local-name()='bookmarkStart' or local-name()='bookmarkEnd' or local-name()='hyperlink']"):
            raise ValueError(f"Report3 {layer} roadmap contains non-chart bookmarks or links")
        selected[layer] = paragraph

    # In the supplied template the psychological page's large light-purple
    # backing is a separate floating shape in the paragraph immediately before
    # the roadmap group. Its relativeHeight is greater than the roadmap anchors,
    # so LibreOffice paints it over the inserted inline image. Keep its original
    # geometry and position, but place this verified backing behind document
    # content in the isolated DOCX copy.
    psych_paragraph = selected["psych"]
    background_paragraph = psych_paragraph.getprevious()
    backgrounds = []
    if background_paragraph is not None:
        for anchor in background_paragraph.xpath(".//*[local-name()='anchor']"):
            fills = {
                value.upper()
                for value in anchor.xpath(".//*[local-name()='srgbClr']/@val")
            }
            extents = anchor.xpath("./*[local-name()='extent']")
            if not extents:
                continue
            width = int(extents[0].get("cx", "0"))
            height = int(extents[0].get("cy", "0"))
            if "F3EEFC" in fills and width >= 5_000_000 and height >= 5_000_000:
                backgrounds.append(anchor)
    if len(backgrounds) != 1:
        raise ValueError(
            "Expected the single light-purple SCL Report3 psychological roadmap "
            f"backing immediately before its anchor paragraph; found {len(backgrounds)}"
        )
    backgrounds[0].set("behindDoc", "1")

    rels_path = word_folder / "word" / "_rels" / "document.xml.rels"
    content_types_path = word_folder / "[Content_Types].xml"
    rels_tree = load_xml_file(rels_path)
    rels_root = rels_tree.getroot()
    existing_ids = {item.get("Id") for item in rels_root}
    existing_targets = {item.get("Target") for item in rels_root}
    content_tree = load_xml_file(content_types_path)
    content_root = content_tree.getroot()
    if not any(item.get("Extension", "").lower() == "png" for item in content_root):
        etree.SubElement(content_root, f"{{{ct_ns}}}Default", Extension="png", ContentType="image/png")

    docpr_ids = [int(value) for value in root.xpath(".//*[local-name()='docPr']/@id") if str(value).isdigit()]
    next_docpr = max(docpr_ids, default=0) + 1
    media_dir = word_folder / "word" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    max_width_mm, max_height_mm = 168.0, 183.0

    inserted_layers = set()
    inserted_relationships = {}
    for offset, (layer, paragraph) in enumerate(selected.items()):
        source = Path(roadmap_images[layer])
        if not source.is_file():
            raise FileNotFoundError(f"Report3 {layer} roadmap image is missing: {source}")
        with Image.open(source) as image:
            width_px, height_px = image.size
        if width_px <= 0 or height_px <= 0:
            raise ValueError(f"Report3 {layer} roadmap image has invalid dimensions")
        scale = min(max_width_mm / width_px, max_height_mm / height_px)
        width_emu = round(width_px * scale * 36000)
        height_emu = round(height_px * scale * 36000)

        filename = f"scl_r3_roadmap_{layer}.png"
        target = f"media/{filename}"
        shutil.copyfile(source, media_dir / filename)
        embedded_media = media_dir / filename
        if not embedded_media.is_file() or embedded_media.stat().st_size == 0:
            raise RuntimeError(f"Report3 {layer} roadmap media was not copied into the DOCX")
        relation_id = f"rIdSclR3Roadmap{layer.title()}"
        while relation_id in existing_ids:
            relation_id += "X"
        if target in existing_targets:
            raise ValueError(f"Duplicate Report3 roadmap media relationship: {target}")
        existing_ids.add(relation_id)
        existing_targets.add(target)
        etree.SubElement(
            rels_root,
            f"{{{package_rel_ns}}}Relationship",
            Id=relation_id,
            Type=f"{rel_ns}/image",
            Target=target,
        )
        inserted_relationships[layer] = (relation_id, target)

        for child in list(paragraph):
            if child.tag != f"{{{word_ns}}}pPr":
                paragraph.remove(child)
        ppr = paragraph.find(f"{{{word_ns}}}pPr")
        if ppr is None:
            ppr = etree.Element(f"{{{word_ns}}}pPr")
            paragraph.insert(0, ppr)
        justification = ppr.find(f"{{{word_ns}}}jc")
        if justification is None:
            justification = etree.SubElement(ppr, f"{{{word_ns}}}jc")
        justification.set(f"{{{word_ns}}}val", "center")

        run = etree.SubElement(paragraph, f"{{{word_ns}}}r")
        drawing = etree.SubElement(run, f"{{{word_ns}}}drawing")
        inline = etree.SubElement(drawing, f"{{{wp_ns}}}inline", distT="0", distB="0", distL="0", distR="0")
        etree.SubElement(inline, f"{{{wp_ns}}}extent", cx=str(width_emu), cy=str(height_emu))
        etree.SubElement(inline, f"{{{wp_ns}}}effectExtent", l="0", t="0", r="0", b="0")
        etree.SubElement(
            inline,
            f"{{{wp_ns}}}docPr",
            id=str(next_docpr + offset),
            name=f"SCL R3 {layer} roadmap",
            descr=f"R3 {layer} roadmap with student scores",
        )
        frame = etree.SubElement(inline, f"{{{wp_ns}}}cNvGraphicFramePr")
        etree.SubElement(frame, f"{{{a_ns}}}graphicFrameLocks", noChangeAspect="1")
        graphic = etree.SubElement(inline, f"{{{a_ns}}}graphic")
        graphic_data = etree.SubElement(graphic, f"{{{a_ns}}}graphicData", uri=pic_ns)
        picture = etree.SubElement(graphic_data, f"{{{pic_ns}}}pic")
        nv = etree.SubElement(picture, f"{{{pic_ns}}}nvPicPr")
        etree.SubElement(nv, f"{{{pic_ns}}}cNvPr", id=str(next_docpr + offset), name=filename)
        locks = etree.SubElement(etree.SubElement(nv, f"{{{pic_ns}}}cNvPicPr"), f"{{{a_ns}}}picLocks")
        locks.set("noChangeAspect", "1")
        fill = etree.SubElement(picture, f"{{{pic_ns}}}blipFill")
        blip = etree.SubElement(fill, f"{{{a_ns}}}blip", {f"{{{rel_ns}}}embed": relation_id})
        etree.SubElement(etree.SubElement(fill, f"{{{a_ns}}}stretch"), f"{{{a_ns}}}fillRect")
        shape = etree.SubElement(picture, f"{{{pic_ns}}}spPr")
        transform = etree.SubElement(shape, f"{{{a_ns}}}xfrm")
        etree.SubElement(transform, f"{{{a_ns}}}off", x="0", y="0")
        etree.SubElement(transform, f"{{{a_ns}}}ext", cx=str(width_emu), cy=str(height_emu))
        geometry = etree.SubElement(shape, f"{{{a_ns}}}prstGeom", prst="rect")
        etree.SubElement(geometry, f"{{{a_ns}}}avLst")
        if (
            blip.get(f"{{{rel_ns}}}embed") != relation_id
            or paragraph.find(f"{{{word_ns}}}r") is None
            or not paragraph.xpath(
                ".//*[local-name()='docPr' and @name=$name]",
                name=f"SCL R3 {layer} roadmap",
            )
        ):
            raise RuntimeError(f"Report3 {layer} roadmap image was not inserted into its DOCX paragraph")
        inserted_layers.add(layer)

    if inserted_layers != set(expected_markers) or "psych" not in inserted_layers:
        raise RuntimeError("The mandatory Report3 psychological roadmap was not inserted")
    for layer, (relation_id, target) in inserted_relationships.items():
        relationship = next((item for item in rels_root if item.get("Id") == relation_id), None)
        if relationship is None or relationship.get("Target") != target:
            raise RuntimeError(f"Report3 {layer} roadmap relationship is missing or incorrect")
    _, psych_target = inserted_relationships["psych"]
    if not (media_dir / Path(psych_target).name).is_file():
        raise RuntimeError("The mandatory Report3 psychological roadmap media target is missing")

    save_xml_to_file(rels_tree, rels_path)
    save_xml_to_file(content_tree, content_types_path)


def generate_third_report_documents(
        user_directory: Path | str,
        user_report_info: dict,
        phone: str,
        colors_tag: Sequence[str],
        colors_color: Sequence[str],
        report_text_replacements: dict,
        needed: list[str],
        unneeded: list[str],
        image_replacements: list[Tuple[str, Path | str]] = (),
        roadmap_images: Mapping[str, Path | str] | None = None,
) -> Path:
    """Generate third report docx/pdf with provided data and assets."""
    try:
        if not REPORT3_TEMPLATE.is_file():
            raise FileNotFoundError(f"SCL Report3 template is missing: {REPORT3_TEMPLATE}")
        folder_word = Path(user_directory) / "Tree3"
        unzip_word_file(REPORT3_TEMPLATE, folder_word)

        tree_path = folder_word / "word"
        tree = load_xml_file(tree_path / "document.xml")

        # Validate the media map before editing the isolated DOCX workspace.
        for target_name, image_path in image_replacements:
            _replace_scl_report3_image(folder_word, target_name, image_path)

        headers = [*tree_path.glob("header*.xml"), *tree_path.glob("footer*.xml")]
        all_replacements = {**user_report_info, **report_text_replacements}
        conditional_tokens = set(needed) | set(unneeded)
        for xml_part in [tree_path / "document.xml", *headers]:
            check_tree = tree if xml_part.name == "document.xml" else load_xml_file(xml_part)
            unknown = _report3_template_markers(check_tree) - set(all_replacements) - conditional_tokens
            if unknown:
                raise ValueError(f"Unregistered SCL Report3 placeholders in {xml_part.name}: {sorted(unknown)[:8]}")

        header_replacements = {
            key: value for key, value in all_replacements.items()
            if key in {"studentname", "Studentname", "instname", "conname", "#name", "#con_name", "#inst_name"}
        }
        for xml_part in headers:
            header_tree = _replace_scl_report3_text_tokens(load_xml_file(xml_part), header_replacements)
            save_xml_to_file(header_tree, xml_part)

        # Apply color changes for COLOR_TAGS (if value < 2.0, set to gray)
        # COLOR_TAGS are bookmarks, so we pass tag as bookmark parameter (not field)
        for tag, color in zip(colors_tag, colors_color):
            tree = change_graphic_background_color(tree, color, tag, None)

        tree = remove_labeled_texts(tree, unneeded, needed)

        if roadmap_images is None:
            raise ValueError("SCL Report3 requires generated surface, psych, and root roadmaps")
        _insert_scl_report3_roadmap_images(tree, folder_word, roadmap_images)

        # The supplied revision stores layer ranking tokens in document.xml.
        # Replace the full registry there, while retaining legacy embedded-diagram support.
        diagram_tags_skill = ["vav", "vaav", "vaaav", "vaaaav", "vaaaaav", "vaaaaaav"]
        diagram_tags_psycho = ["waw", "waaw", "waaaw", "waaaaw", "waaaaaw"]
        diagram_tags_real = ["zaz", "zaaz", "zaaaz", "zaaaaz", "zaaaaaz"]
        tree = _replace_scl_report3_text_tokens(tree, {key: str(value) for key, value in all_replacements.items()})
        save_xml_to_file(tree, tree_path / "document.xml")

        # Replace texts in diagram XML files
        # Diagram files are typically in word/embeddings/*/diagrams/ or word/diagrams/
        def find_diagram_file(folder: Path, filename: str) -> Path | None:
            """Find a diagram XML file by searching common locations."""
            # Try word/diagrams/ first
            diagrams_path = folder / "word" / "diagrams" / filename
            if diagrams_path.exists():
                return diagrams_path

            # Try word/embeddings/*/diagrams/
            embeddings_path = folder / "word" / "embeddings"
            if embeddings_path.exists():
                for item in embeddings_path.iterdir():
                    if item.is_dir():
                        diagram_path = item / "diagrams" / filename
                        if diagram_path.exists():
                            return diagram_path
                        # Also try direct subdirectory
                        direct_path = item / filename
                        if direct_path.exists():
                            return direct_path

            # Try word/embeddings/diagrams/ directly
            direct_diagrams = folder / "word" / "embeddings" / "diagrams" / filename
            if direct_diagrams.exists():
                return direct_diagrams

            return None

        # Handle data2.xml (skill tags)
        diagram_skill_replacements = {k: v for k, v in all_replacements.items() if k in diagram_tags_skill}
        if diagram_skill_replacements:
            data2_path = find_diagram_file(folder_word, "data1.xml")
            if data2_path:
                diagram_tree = load_xml_file(data2_path)
                skill_tag_names = [f"{key}" for key in diagram_skill_replacements.keys()]
                skill_tag_values = [str(value) for value in diagram_skill_replacements.values()]
                diagram_tree = replace_texts(diagram_tree, skill_tag_names, skill_tag_values)
                save_xml_to_file(diagram_tree, data2_path)

        # Handle data4.xml (psycho tags)
        diagram_psycho_replacements = {k: v for k, v in all_replacements.items() if k in diagram_tags_psycho}
        if diagram_psycho_replacements:
            data4_path = find_diagram_file(folder_word, "data2.xml")
            if data4_path:
                diagram_tree = load_xml_file(data4_path)
                psycho_tag_names = [f"{key}" for key in diagram_psycho_replacements.keys()]
                psycho_tag_values = [str(value) for value in diagram_psycho_replacements.values()]
                diagram_tree = replace_texts(diagram_tree, psycho_tag_names, psycho_tag_values)
                save_xml_to_file(diagram_tree, data4_path)

        # Handle data6.xml (real tags)
        diagram_real_replacements = {k: v for k, v in all_replacements.items() if k in diagram_tags_real}
        if diagram_real_replacements:
            data6_path = find_diagram_file(folder_word, "data3.xml")
            if data6_path:
                diagram_tree = load_xml_file(data6_path)
                real_tag_names = [f"{key}" for key in diagram_real_replacements.keys()]
                real_tag_values = [str(value) for value in diagram_real_replacements.values()]
                diagram_tree = replace_texts(diagram_tree, real_tag_names, real_tag_values)
                save_xml_to_file(diagram_tree, data6_path)

        destination_docx = Path(user_directory) / f"Report3{phone}.docx"
        destination_pdf = Path(user_directory) / "Report3.pdf"
        zip_word_folder(folder_word, destination_docx)
        convert_docx_to_pdf(destination_docx, destination_pdf)
        remove_unneeded_files(user_directory, DONT_REMOVE)
        return destination_pdf
    except Exception as exc:
        raise RuntimeError(f"Failed to generate third report documents: {exc}") from exc


def generate_forth_report_documents(
        user_directory: Path | str,
        user_report_info: dict,
        phone: str,
        *,
        psshi_labels: Mapping[str, object],
        psychological_order: Sequence[str],
        psychological_scores: Mapping[str, object],
        logo_path: str | None = None,
        template_path: Path | str | None = None,
) -> Path:
    """Generate official SCL Report4: the PSSHI study-skills DOCX and PDF."""
    try:
        # Import locally because the focused PSSHI adapter reuses these Word helpers.
        from helper.office.scl_psshi import generate_study_skills_report_documents

        import config

        identity = {
            "#name": user_report_info.get("#name", user_report_info.get("studentname", "")),
            "#con_name": user_report_info.get("#con_name", user_report_info.get("conname", "")),
            "#inst_name": user_report_info.get("#inst_name", user_report_info.get("instname", "")),
        }
        return generate_study_skills_report_documents(
            template_path=template_path or config.SCL_PSSHI_TEMPLATE_PATH,
            user_directory=user_directory,
            student_name=str(identity["#name"]),
            consultant_name=str(identity["#con_name"]),
            institute_name=str(identity["#inst_name"]),
            phone=str(phone),
            logo_path=logo_path,
            labels=psshi_labels,
            psychological_order=psychological_order,
            psychological_scores=psychological_scores,
            output_docx_name=f"Report4{phone}.docx",
            output_pdf_name="Report4.pdf",
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to generate SCL Report4 study-skills documents: {exc}") from exc


def generate_fifth_report_documents(
        user_directory: Path | str,
        user_report_info: dict,
        image_names: Sequence[str],
        user_report_pictures: Sequence[Path | str],
        phone: str,
        needed: list[str],
        unneeded: list[str],
        image_replacements: Sequence[Tuple[str, Path | str]] = (),
) -> None:
    """Generate fifth report docx/pdf with bar chart and provided data."""
    try:
        folder_word = Path(user_directory) / "Tree5"
        unzip_word_file(REPORT5_TEMPLATE, folder_word)

        tree_path = folder_word / "word"
        tree = load_xml_file(tree_path / "document.xml")

        # Replace images in word folder
        replace_images_in_word_folder(folder_word, image_names, user_report_pictures)

        # Replace additional images if provided (e.g., logo)
        if image_replacements:
            old_image_files = [old_img for old_img, _ in image_replacements]
            new_image_files = [new_img for _, new_img in image_replacements]
            replace_images_in_word_folder(folder_word, old_image_files, new_image_files)

        # Prepare tag names and values for text replacement
        tag_names = [f"{key}" for key in user_report_info.keys()]
        tag_values = [str(value) for value in user_report_info.values()]

        # Handle header replacements (studentname, instname, conname)
        header_tags = ["studentname", "instname", "conname"]
        header_values = [
            user_report_info.get("studentname", ""),
            user_report_info.get("instname", ""),
            user_report_info.get("conname", "")
        ]

        # Replace in headers
        replace_texts_in_headers(
            folder_word, header_tags, header_values
        )
        tree = remove_labeled_texts(tree, unneeded, needed)

        # Replace texts in document body
        tree = replace_texts(tree, tag_names, tag_values)

        save_xml_to_file(tree, tree_path / "document.xml")

        destination_docx = Path(user_directory) / f"Report5{phone}.docx"
        destination_pdf = Path(user_directory) / "Report5.pdf"
        zip_word_folder(folder_word, destination_docx)
        convert_docx_to_pdf(destination_docx, destination_pdf)
        remove_unneeded_files(user_directory, DONT_REMOVE)
    except Exception as exc:
        raise RuntimeError(f"Failed to generate fifth report documents: {exc}") from exc


# Backwards compatibility aliases
CovertDocxToPDF = convert_docx_to_pdf
CovertWordToPDF = convert_word_to_pdf
GetXMLTagWithoutNS = get_xml_tag_without_namespace
GetXMLTagNamespace = get_xml_tag_namespace
UnzipWordFile = unzip_word_file
ZipWordFolder = zip_word_folder
LoadXMLFile = load_xml_file
SaveXMLToFile = save_xml_to_file
ReplaceText = replace_text
ReplaceTexts = replace_texts
ReplaceImageInWordFolder = replace_image_in_word_folder
ReplaceImagesInWordFolder = replace_images_in_word_folder
InsertValuesIntoTable = insert_values_into_table
ChangeGraphicBackColor = change_graphic_background_color
ChangeGraphicEffect = change_graphic_effect
ReplaceTextsInHeaders = replace_texts_in_headers
ReplaceTextsInFooters = replace_texts_in_footers
remove_all_files = remove_unneeded_files
generate_word_with_info = generate_first_report_documents
generate_word_second_info = generate_second_report_documents
