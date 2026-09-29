"""
OfflineMind - Note Exporter (Markdown & PDF)
Generates clean, beautifully styled PDF and Markdown documents for offline sharing.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("OfflineMind.Exporter")


class NoteExporter:
    """
    Handles exporting notes into Markdown (.md) and formatted PDF (.pdf) formats.
    """

    @staticmethod
    def export_markdown(note_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Returns Markdown string or writes to disk if output_path is provided.
        """
        from storage.notes_manager import NotesManager
        nm = NotesManager()
        md_text = nm.render_markdown(
            note_id=note_data.get("id", "note"),
            title=note_data.get("title", "Untitled Note"),
            summary=note_data.get("summary", ""),
            key_points=note_data.get("key_points", []),
            action_items=note_data.get("action_items", []),
            transcript=note_data.get("transcript", ""),
            created_at=note_data.get("created_at", ""),
            duration_seconds=float(note_data.get("duration_seconds", 0.0)),
            backend=note_data.get("backend", "CPU"),
            rtf=float(note_data.get("rtf", 0.0)),
            tags=note_data.get("tags", [])
        )
        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", encoding="utf-8") as f:
                f.write(md_text)
            logger.info(f"Exported Markdown to {out}")
        return md_text

    @staticmethod
    def export_pdf(note_data: Dict[str, Any], output_path: str) -> str:
        """
        Builds a styled PDF document from note data using fpdf2.
        Returns the output path of the generated PDF.
        """
        try:
            from fpdf import FPDF
        except ImportError:
            raise RuntimeError("fpdf2 is required for PDF export. Run: pip install fpdf2")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        class StyledPDF(FPDF):
            def header(self):
                self.set_font("Helvetica", "B", 10)
                self.set_text_color(100, 116, 139) # slate gray
                half_w = self.epw / 2
                self.cell(half_w, 8, "OfflineMind - Private On-Device AI Notes", border=0, align="L")
                self.cell(half_w, 8, "Snapdragon AI Lab Challenge", border=0, align="R", new_x="LMARGIN", new_y="NEXT")
                self.set_draw_color(226, 232, 240)
                self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
                self.ln(5)

            def footer(self):
                self.set_y(-15)
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(148, 163, 184)
                self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | Fully processed offline on Snapdragon PC", align="C")

        pdf = StyledPDF(orientation="P", unit="mm", format="A4")
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_page()

        # Helper for sanitizing text to Latin-1 compatible for standard PDF fonts
        def sanitize(text: str) -> str:
            # Replace common unicode chars
            replacements = {
                "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
                "\u2014": "--", "\u2013": "-", "\u2026": "...",
                "⚡": "[NPU]", "📌": "[Summary]", "💡": "[Key]",
                "✅": "[Action]", "🎙️": "[Transcript]", "🗓️": "[Date]",
                "⏱️": "[Duration]"
            }
            for k, v in replacements.items():
                text = text.replace(k, v)
            return text.encode("latin-1", "replace").decode("latin-1")

        # Title
        title = sanitize(note_data.get("title", "Untitled Note"))
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(15, 23, 42) # dark slate
        pdf.multi_cell(pdf.epw, 9, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Metadata banner
        date_str = note_data.get("created_at", "")[:19].replace("T", " ")
        dur_str = f"{float(note_data.get('duration_seconds', 0.0)):.1f}s"
        backend = note_data.get("backend", "CPU")
        tags = ", ".join(note_data.get("tags", []))

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)
        meta_line = f"Date: {date_str}  |  Audio Duration: {dur_str}  |  Backend: {backend}  |  Tags: {tags}"
        pdf.multi_cell(pdf.epw, 6, sanitize(meta_line), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # Section 1: Executive Summary
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(14, 116, 144) # teal/cyan
        pdf.cell(pdf.epw, 8, "Executive Summary", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 41, 59)
        # Background box for summary
        pdf.set_fill_color(241, 245, 249) # light gray background
        summary_text = sanitize(note_data.get("summary", "No summary provided."))
        pdf.multi_cell(pdf.epw, 6, summary_text, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # Section 2: Key Takeaways
        key_points = note_data.get("key_points", [])
        if key_points:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(14, 116, 144)
            pdf.cell(pdf.epw, 8, "Key Takeaways & Concepts", new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 41, 59)
            for kp in key_points:
                clean_kp = sanitize(kp)
                pdf.multi_cell(pdf.epw, 6, f"- {clean_kp}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

        # Section 3: Action Items
        action_items = note_data.get("action_items", [])
        if action_items:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(14, 116, 144)
            pdf.cell(pdf.epw, 8, "Action Items & Follow-ups", new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 41, 59)
            for ai in action_items:
                clean_ai = sanitize(ai)
                pdf.multi_cell(pdf.epw, 6, f"[ ] {clean_ai}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

        # Section 4: Full Transcript
        transcript = note_data.get("transcript", "")
        if transcript:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(14, 116, 144)
            pdf.cell(pdf.epw, 8, "Transcript", new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(pdf.epw, 5, sanitize(transcript), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

        pdf.output(str(out))
        logger.info(f"Successfully generated PDF at {out}")
        return str(out)
