import copy
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import pythoncom
import win32com.client as client
from docx2pdf import convert
from lxml import etree
from config import REPORT1_TEMPLATE_PATH, REPORT2_TEMPLATE_PATH, REPORT3_TEMPLATE_PATH, REPORT5_TEMPLATE_PATH, \
    OCD_TEMPLATE_PATH, ANX_TEMPLATE_PATH, DEP_TEMPLATE_PATH

# Template locations (config-driven)
REPORT1_TEMPLATE = Path(REPORT1_TEMPLATE_PATH)
REPORT2_TEMPLATE = Path(REPORT2_TEMPLATE_PATH)
REPORT3_TEMPLATE = Path(REPORT3_TEMPLATE_PATH)
REPORT5_TEMPLATE = Path(REPORT5_TEMPLATE_PATH)
OCD_TEMPLATE = Path(OCD_TEMPLATE_PATH)
ANX_TEMPLATE = Path(ANX_TEMPLATE_PATH)
DEP_TEMPLATE = Path(DEP_TEMPLATE_PATH)
DONT_REMOVE = ["Report1.pdf", "Report2.pdf", "Report3.pdf", "Report4.pdf", "Report5.pdf", "labels.json",
               "user_info.json", "report_text_replacements.json", "scl_calc_data.json"]


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
    """Convert a DOCX file to PDF, overwriting the destination when needed."""
    src = Path(source_file)
    dst = Path(destination_file)
    dst.unlink(missing_ok=True)
    convert(str(src), str(dst))


def convert_word_to_pdf(source_file: Path | str, destination_file: Path | str) -> None:
    """Convert a Word document to PDF via COM (Windows only)."""
    src = Path(source_file)
    dst = Path(destination_file)
    dst.unlink(missing_ok=True)

    pythoncom.CoInitialize()
    word = client.DispatchEx("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(src))
        # https://learn.microsoft.com/en-us/office/vba/api/word.wdsaveformat
        doc.SaveAs(str(dst), FileFormat=17)  # wdFormatPDF
        doc.Close()
    finally:
        word.Quit()


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
    with open(new_image_file, "rb") as file:
        data = file.read()
    with open(old_file, "rb+") as file:
        file.seek(0)
        file.write(data)
        file.truncate()


def replace_images_in_word_folder(
        source_folder: Path | str, old_image_files: Sequence[str], new_image_files: Sequence[Path | str]
) -> None:
    """Replace multiple images inside the docx media folder."""
    for old, new in zip(old_image_files, new_image_files):
        replace_image_in_word_folder(source_folder, old, new)


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
        folder_word = Path(user_directory) / "Tree"
        unzip_word_file(REPORT1_TEMPLATE, folder_word)
        tree_path = folder_word / "word"
        tree = load_xml_file(tree_path / "document.xml")

        replace_texts_in_headers(
            folder_word, ["#name", "#inst_name", "#con_name"], user_report_info[:3]
        )
        replace_images_in_word_folder(folder_word, image_names, user_report_pictures)
        tree = replace_texts(tree, tag_names, user_report_info)

        # for tag, color in zip(color_handle_tags, color_handle_colors):
        #     tree = change_graphic_background_color(tree, color, tag, None)
        for effect in effects:
            tree = change_graphic_effect(
                tree,
                ["effectLst", "scene3d", "sp3d"],
                [
                    '<effectLst><outerShdw blurRad="107950" dist="12700" dir="5400000" algn="ctr"><srgbClr val="000000"/></outerShdw></effectLst>',
                    '<scene3d><camera prst="orthographicFront"><rot lat="0" lon="0" rev="0"/></camera><lightRig rig="soft" dir="t"><rot lat="0" lon="0" rev="0"/></lightRig></scene3d>',
                    '<sp3d contourW="44450" prstMaterial="matte"><bevelT w="63500" h="63500" prst="artDeco"/><contourClr><srgbClr val="FFFFFF"/></srgbClr></contourClr></sp3d>',
                ],
                effect,
            )

        save_xml_to_file(tree, tree_path / "document.xml")

        destination_docx = Path(user_directory) / f"Report1{phone}.docx"
        destination_pdf = Path(user_directory) / "Report1.pdf"
        zip_word_folder(folder_word, destination_docx)
        convert_docx_to_pdf(destination_docx, destination_pdf)
        remove_unneeded_files(user_directory, DONT_REMOVE)
    except Exception as exc:
        raise RuntimeError("Failed to generate first report documents") from exc


def generate_second_report_documents(
        user_directory: Path | str,
        fields_matched: Sequence,
        fields_benchmark_name: Sequence,
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
        folder_word = Path(user_directory) / "Tree2"
        unzip_word_file(REPORT2_TEMPLATE, folder_word)

        tree_path = folder_word / "word"
        tree = load_xml_file(tree_path / "document.xml")

        replace_texts_in_headers(
            folder_word, ["#name", "#inst_name", "#con_name"], user_report_info[:3]
        )
        replace_images_in_word_folder(folder_word, image_names, user_report_pictures)
        #
        # for tag, color in zip(colors_tag, colors_color):
        #     tree = change_graphic_background_color(tree, color, tag, None)

        tree = replace_texts(tree, tag_names, user_report_info)

        for index, _ in enumerate(fields_matched):
            tree = insert_values_into_table(
                tree,
                fields_benchmark_name[index][0][1],
                fields_matched[index][0],
                fields_benchmark_name[index][0][0],
            )
            tree = insert_values_into_table(
                tree,
                fields_benchmark_name[index][1][1],
                fields_matched[index][1],
                fields_benchmark_name[index][1][0],
            )

        save_xml_to_file(tree, tree_path / "document.xml")

        destination_docx = Path(user_directory) / f"Report2{phone}.docx"
        destination_pdf = Path(user_directory) / "Report2.pdf"
        zip_word_folder(folder_word, destination_docx)
        convert_docx_to_pdf(destination_docx, destination_pdf)
        remove_unneeded_files(user_directory, DONT_REMOVE)
    except Exception as exc:
        raise RuntimeError("Failed to generate second report documents") from exc


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
) -> None:
    """Generate third report docx/pdf with provided data and assets."""
    try:
        folder_word = Path(user_directory) / "Tree3"
        unzip_word_file(REPORT3_TEMPLATE, folder_word)

        tree_path = folder_word / "word"
        tree = load_xml_file(tree_path / "document.xml")

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

        # Replace images if provided
        if image_replacements:
            old_image_files = [old_img for old_img, _ in image_replacements]
            new_image_files = [new_img for _, new_img in image_replacements]
            replace_images_in_word_folder(folder_word, old_image_files, new_image_files)

        # Apply color changes for COLOR_TAGS (if value < 2.0, set to gray)
        # COLOR_TAGS are bookmarks, so we pass tag as bookmark parameter (not field)
        for tag, color in zip(colors_tag, colors_color):
            tree = change_graphic_background_color(tree, color, tag, None)

        tree = remove_labeled_texts(tree, unneeded, needed)

        # Prepare tag names and values for text replacement
        # Merge user_report_info and report_text_replacements
        all_replacements = {**user_report_info, **report_text_replacements}

        # Separate tags for document.xml and diagram XML files
        # Diagram tags: skill_tag (data2.xml), psycho_tag (data4.xml), real_tag (data6.xml)
        diagram_tags_skill = ["vav", "vaav", "vaaav", "vaaaav", "vaaaaav", "vaaaaaav"]
        diagram_tags_psycho = ["waw", "waaw", "waaaw", "waaaaw", "waaaaaw"]
        diagram_tags_real = ["zaz", "zaaz", "zaaaz", "zaaaaz", "zaaaaaz"]
        all_diagram_tags = set(diagram_tags_skill + diagram_tags_psycho + diagram_tags_real)

        # Filter replacements for document.xml (exclude diagram tags)
        document_replacements = {k: v for k, v in all_replacements.items() if k not in all_diagram_tags}
        tag_names = [f"{key}" for key in document_replacements.keys()]
        tag_values = [str(value) for value in document_replacements.values()]

        # Replace texts in document body
        tree = replace_texts(tree, tag_names, tag_values)
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
    except Exception as exc:
        raise RuntimeError(f"Failed to generate third report documents: {exc}") from exc


def generate_forth_report_documents(
        user_directory: Path | str,
        user_report_info: dict,
        report_name: str,
        phone: str,
        image_replacements: list[Tuple[str, Path | str]] = (),
) -> None:
    """Generate fourth report docx/pdf (anxiety/ocd/depression) with provided data."""
    try:
        # Select template based on report_name
        if report_name == "anxiety":
            template = ANX_TEMPLATE
        elif report_name == "ocd":
            template = OCD_TEMPLATE
        elif report_name == "depression":
            template = DEP_TEMPLATE
        else:
            raise ValueError(f"Unknown report_name: {report_name}. Expected 'anxiety', 'ocd', or 'depression'")

        folder_word = Path(user_directory) / "Tree4"
        unzip_word_file(template, folder_word)

        tree_path = folder_word / "word"
        tree = load_xml_file(tree_path / "document.xml")

        # Replace images if provided
        if image_replacements:
            old_image_files = [old_img for old_img, _ in image_replacements]
            new_image_files = [new_img for _, new_img in image_replacements]
            replace_images_in_word_folder(folder_word, old_image_files, new_image_files)

        # Prepare tag names and values for text replacement
        # Convert user_report_info dict to tag_names (with # prefix) and values lists
        # tag_names = [f"#{key}" for key in user_report_info.keys()]
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

        # Replace texts in document body
        tree = replace_texts(tree, tag_names, tag_values)

        save_xml_to_file(tree, tree_path / "document.xml")

        destination_docx = Path(user_directory) / f"Report4{phone}.docx"
        destination_pdf = Path(user_directory) / "Report4.pdf"
        zip_word_folder(folder_word, destination_docx)
        convert_docx_to_pdf(destination_docx, destination_pdf)
        remove_unneeded_files(user_directory, DONT_REMOVE)
    except Exception as exc:
        raise RuntimeError(f"Failed to generate fourth report documents: {exc}") from exc


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
