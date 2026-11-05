import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from lxml import etree

from helper.office import word_helper


def test_first_report_graphic_effects_are_valid_xml():
    for effect_xml in word_helper.FIRST_REPORT_GRAPHIC_EFFECTS:
        etree.fromstring(effect_xml.encode("utf-8"))


def test_missing_libreoffice_has_actionable_configuration_error():
    with patch.object(word_helper.config, "LIBREOFFICE_PATH", "missing-soffice.exe"):
        with patch.object(word_helper.shutil, "which", return_value=None):
            with pytest.raises(FileNotFoundError, match="AG_LIBREOFFICE_PATH"):
                word_helper.require_libreoffice()


def test_conversion_uses_unique_libreoffice_profile(tmp_path):
    source = tmp_path / "Report123.docx"
    destination = tmp_path / "Report.pdf"
    source.write_bytes(b"docx placeholder")
    captured_commands = []

    def fake_run(command, **kwargs):
        captured_commands.append(command)
        generated_pdf = Path(command[command.index("--outdir") + 1]) / "Report123.pdf"
        generated_pdf.write_bytes(b"pdf placeholder")
        return subprocess.CompletedProcess(command, 0, "converted", "")

    with patch.object(word_helper, "_resolve_libreoffice_command", return_value="soffice"):
        with patch.object(word_helper.subprocess, "run", side_effect=fake_run):
            ok, message = word_helper._convert_to_pdf_once(source, destination)

    assert ok, message
    assert destination.exists()
    assert len(captured_commands) == 1
    assert captured_commands[0][1].startswith("-env:UserInstallation=file:///")


def test_failed_conversion_is_retried():
    with patch.object(word_helper.config, "LIBREOFFICE_CONVERSION_ATTEMPTS", 2):
        with patch.object(word_helper.config, "LIBREOFFICE_RETRY_DELAY_SECONDS", 1):
            with patch.object(
                word_helper,
                "_convert_to_pdf_once",
                side_effect=[(False, "profile busy"), (True, "Report.pdf")],
            ) as convert_once:
                with patch.object(word_helper.time, "sleep") as sleep:
                    ok, message = word_helper.convert_to_pdf("Report.docx", "Report.pdf")

    assert ok, message
    assert convert_once.call_count == 2
    sleep.assert_called_once_with(1)


def test_timeout_returns_actionable_error(tmp_path):
    source = tmp_path / "Report123.docx"
    destination = tmp_path / "Report.pdf"
    source.write_bytes(b"docx placeholder")

    timeout = subprocess.TimeoutExpired("soffice", 180)
    with patch.object(word_helper, "_resolve_libreoffice_command", return_value="soffice"):
        with patch.object(word_helper.subprocess, "run", side_effect=timeout):
            ok, message = word_helper._convert_to_pdf_once(source, destination)

    assert not ok
    assert "timed out after" in message
