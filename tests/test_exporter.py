"""
OfflineMind - Unit Tests: Markdown and PDF Exporters
"""

import tempfile
import pytest
from pathlib import Path
from storage.exporter import NoteExporter


@pytest.fixture
def sample_note_data():
    return {
        "id": "note_test_123",
        "title": "Quantum Physics & NPU Acceleration",
        "summary": "Exploration of quantum simulation using Snapdragon NPU processors.",
        "key_points": [
            "Qubit states simulation in edge tensor processors",
            "Energy consumption reduced by 4x over traditional CPU",
        ],
        "action_items": [
            "Implement benchmarking script",
            "Prepare slides for presentation challenge",
        ],
        "transcript": "In this symposium we discuss quantum hardware acceleration and low-power inference.",
        "tags": ["Quantum", "Snapdragon", "Physics"],
        "created_at": "2025-09-30T10:00:00",
        "duration_seconds": 180.5,
        "backend": "NPU (Snapdragon Hexagon)",
        "rtf": 0.08,
    }


def test_markdown_export(sample_note_data):
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = Path(tmp_dir) / "exported_note.md"
        result_str = NoteExporter.export_markdown(sample_note_data, output_path=str(out_file))

        assert out_file.exists()
        assert "# Quantum Physics & NPU Acceleration" in result_str
        assert "## 📌 Executive Summary" in result_str
        assert "## ✅ Action Items & Follow-ups" in result_str
        assert "Qubit states simulation" in result_str


def test_pdf_export(sample_note_data):
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_pdf = Path(tmp_dir) / "exported_note.pdf"
        pdf_path = NoteExporter.export_pdf(sample_note_data, output_path=str(out_pdf))

        assert Path(pdf_path).exists()
        file_size = Path(pdf_path).stat().st_size
        assert file_size > 500  # PDF should contain binary content

        # Check PDF Magic Header
        with open(pdf_path, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"
