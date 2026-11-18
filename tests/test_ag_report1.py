from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from lxml import etree
from PIL import Image

from helper.diagram.ag_report1.report import (
    CLIFTON_DOMAINS,
    MEDIA_TARGETS,
    build_chart_data,
    render_report_media,
)
from helper.office import word_helper


def representative_labels() -> dict[str, float]:
    labels = {"IQ_Number": 112, "SES": 150}
    for key, value in zip(
        (
            "Visual_spatial", "Linguistic_verbal", "Logical_mathematical", "Body_kinesthetic",
            "Musical", "Interpersonal", "Intrapersonal", "Naturalistic",
        ),
        (32, 38, 29, 35, 24, 41, 30, 20),
    ):
        labels[key] = value
    for key, value in zip(
        ("Extraversion", "Agreeableness", "Neuroticism", "Openness", "Conscientiousness"),
        (29, 31, 15, 36, 39),
    ):
        labels[key] = value
    for key, value in zip(
        ("Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"),
        (16, 32, 15, 26, 11, 19),
    ):
        labels[key] = value
    for _, scales in CLIFTON_DOMAINS:
        for key, maximum in scales.items():
            labels[key] = round(maximum * 0.65)
    return labels


def test_chart_data_uses_explicit_template_order_and_normalization():
    chart_data = build_chart_data(representative_labels())

    assert [item["key"] for item in chart_data.gardner] == [
        "Visual_spatial", "Linguistic_verbal", "Logical_mathematical", "Body_kinesthetic",
        "Musical", "Interpersonal", "Intrapersonal", "Naturalistic",
    ]
    assert [item["key"] for item in chart_data.neo] == [
        "Extraversion", "Agreeableness", "Neuroticism", "Openness", "Conscientiousness",
    ]
    assert chart_data.gardner[0]["score"] == 64
    assert chart_data.neo[0]["score"] == pytest.approx(60.42)
    assert chart_data.commitment["score"] == pytest.approx(66.96)
    assert chart_data.commitment["label"] == "زیاد"


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("Visual_spatial", 51, "Visual_spatial"),
        ("Extraversion", -1, "Extraversion"),
        ("SES", 225, "SES"),
    ],
)
def test_chart_data_rejects_invalid_boundaries(key, value, message):
    labels = representative_labels()
    labels[key] = value
    with pytest.raises(ValueError, match=message):
        build_chart_data(labels)


def test_chart_data_reports_missing_label():
    labels = representative_labels()
    labels.pop("Realistic")
    with pytest.raises(ValueError, match="Realistic"):
        build_chart_data(labels)


def test_all_report_media_are_nonempty_correctly_sized_and_distinct(tmp_path):
    rendered = render_report_media(build_chart_data(representative_labels()), tmp_path)
    expected_sizes = {
        "image13.png": (1600, 1760),
        "image16.png": (1500, 960),
        "image18.png": (2400, 1350),
        "image69.png": (1600, 900),
        "image71.png": (1600, 820),
        "image81.png": (1600, 640),
    }

    assert tuple(rendered) == MEDIA_TARGETS
    for name, path in rendered.items():
        assert path.stat().st_size > 1_000
        with Image.open(path) as image:
            if name in expected_sizes:
                assert image.size == expected_sizes[name]
            elif name in {"image23.png", "image26.png", "image29.png", "image32.png", "image35.png", "image38.png", "image41.png", "image44.png"}:
                assert image.size == (360, 1050)
            else:
                assert image.size == (3000, 225)

    tube_hashes = {
        hashlib.sha256(rendered[name].read_bytes()).hexdigest()
        for name in ("image23.png", "image26.png", "image29.png", "image32.png", "image35.png", "image38.png", "image41.png", "image44.png")
    }
    neo_hashes = {
        hashlib.sha256(rendered[name].read_bytes()).hexdigest()
        for name in ("image53.png", "image55.png", "image57.png", "image59.png", "image61.png")
    }
    assert len(tube_hashes) == 8
    assert len(neo_hashes) == 5


def test_split_run_replacement_preserves_runs():
    xml = etree.ElementTree(etree.fromstring(
        b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        b'<w:body><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>#</w:t></w:r>'
        b'<w:r><w:t>name</w:t></w:r><w:r><w:t> suffix</w:t></w:r></w:p></w:body></w:document>'
    ))

    word_helper.replace_texts_across_runs(xml, {"#name": "دانش آموز"})
    texts = xml.xpath("//w:t/text()", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"})

    assert "".join(texts) == "دانش آموز suffix"
    assert xml.xpath("count(//w:r)", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}) == 3


def test_repository_template_contains_exact_report1_media_and_shared_logo():
    template = Path(word_helper.REPORT1_TEMPLATE)
    with zipfile.ZipFile(template) as archive:
        names = set(archive.namelist())
        assert {f"word/media/{name}" for name in MEDIA_TARGETS} <= names
        assert "word/media/image14.jpeg" in names
        header_relationships = [
            name for name in names if name.startswith("word/_rels/header") and name.endswith(".rels")
        ]
        logo_relationship_count = sum(
            b'Target="media/image14.jpeg"' in archive.read(name)
            for name in header_relationships
        )
        assert logo_relationship_count > 1


def test_png_logo_is_converted_to_jpeg_without_changing_docx_target(tmp_path):
    source = tmp_path / "logo.png"
    Image.new("RGBA", (20, 20), (20, 40, 60, 100)).save(source)
    media = tmp_path / "word" / "media"
    media.mkdir(parents=True)
    target = media / "image14.jpeg"
    target.write_bytes(b"old")

    word_helper.replace_image_in_word_folder(tmp_path, "image14.jpeg", source)

    with Image.open(target) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"


def test_first_report_generation_keeps_docx_and_requires_nonempty_pdf(tmp_path, monkeypatch):
    chart_dir = tmp_path / "charts"
    rendered = render_report_media(build_chart_data(representative_labels()), chart_dir)
    replacements = {
        "#name": "دانش آموز نمونه",
        "#con_name": "مشاور نمونه",
        "#inst_name": "آموزشگاه نمونه",
        "#right_cattel": "40",
        "#wrong_cattel": "10",
        "#non_cattel": "0",
        "#توضیحات_کتل": "توضیح نمونه",
        "#desire_first_title": "اول",
        "#desire_second_title": "دوم",
        "#desire_third_title": "سوم",
        "#work_first_title": "اول",
        "#work_second_title": "دوم",
        "#work_third_title": "سوم",
        "#تعهد": "سطح تعهد زیاد است.",
        "#سختی": "متوسط",
        "#مهاجرت": "متوسط",
        "#شغل": "متوسط",
        "#درآمد": "متوسط",
        "#جایگاه": "متوسط",
        "#زمان": "متوسط",
    }
    for length in range(2, 27):
        replacements["سل" + "ا" * length + "م"] = f"توضیح نمونه {length}"

    def fake_convert(_source, destination):
        Path(destination).write_bytes(b"%PDF-1.4 sample")

    monkeypatch.setattr(word_helper, "convert_docx_to_pdf", fake_convert)
    word_helper.generate_first_report_documents(
        list(replacements),
        list(replacements.values()),
        list(rendered),
        list(rendered.values()),
        tmp_path,
        [],
        [],
        [],
        "09120000000",
    )

    docx = tmp_path / "Report109120000000.docx"
    assert docx.stat().st_size > 0
    assert (tmp_path / "Report1.pdf").stat().st_size > 0
    with zipfile.ZipFile(docx) as archive:
        assert archive.testzip() is None
        document = archive.read("word/document.xml").decode("utf-8")
        assert "#" not in document
        assert "سلا" not in document
