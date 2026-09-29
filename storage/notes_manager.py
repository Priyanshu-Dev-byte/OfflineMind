"""
OfflineMind - Notes File Manager & Storage Engine
Persists structured notes as clean local Markdown (.md) files with YAML frontmatter
and synchronizes with the SQLite search index.
"""

import os
import re
import uuid
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from storage.db import NotesDatabase

logger = logging.getLogger("OfflineMind.NotesManager")

DEFAULT_NOTES_DIR = Path("storage/notes_data")


class NotesManager:
    """
    Manages local Markdown file storage and database synchronization.
    """

    def __init__(self, notes_dir: Optional[Path] = None, db: Optional[NotesDatabase] = None):
        self.notes_dir = Path(notes_dir or DEFAULT_NOTES_DIR)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.db = db or NotesDatabase(self.notes_dir / "offlinemind.db")
        self._ensure_sample_notes()

    def create_note(
        self,
        title: str,
        summary: str,
        key_points: List[str],
        action_items: List[str],
        transcript: str,
        tags: Optional[List[str]] = None,
        duration_seconds: float = 0.0,
        backend: str = "CPU",
        rtf: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Creates a new structured note, writes markdown to disk, and indexes in SQLite.
        """
        now = datetime.now()
        timestamp_slug = now.strftime("%Y%m%d_%H%M%S")
        note_id = f"note_{timestamp_slug}_{uuid.uuid4().hex[:6]}"
        safe_title = re.sub(r'[^a-zA-Z0-9_\- ]+', '', title).strip().replace(" ", "_")
        filename = f"{timestamp_slug}_{safe_title[:30]}.md"
        file_path = self.notes_dir / filename

        tags = tags or ["VoiceNote"]
        word_count = len(transcript.split()) + len(summary.split())

        # Construct Markdown content with YAML frontmatter
        md_content = self.render_markdown(
            note_id=note_id,
            title=title,
            summary=summary,
            key_points=key_points,
            action_items=action_items,
            transcript=transcript,
            created_at=now.isoformat(),
            duration_seconds=duration_seconds,
            backend=backend,
            rtf=rtf,
            tags=tags
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        note_data = {
            "id": note_id,
            "title": title,
            "summary": summary,
            "key_points": key_points,
            "action_items": action_items,
            "transcript": transcript,
            "tags": tags,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "file_path": str(file_path),
            "duration_seconds": duration_seconds,
            "backend": backend,
            "rtf": rtf,
            "word_count": word_count,
        }

        # Index in DB
        self.db.insert_note(note_data)
        logger.info(f"Created and indexed note: {file_path}")
        return note_data

    def render_markdown(
        self,
        note_id: str,
        title: str,
        summary: str,
        key_points: List[str],
        action_items: List[str],
        transcript: str,
        created_at: str,
        duration_seconds: float,
        backend: str,
        rtf: float,
        tags: List[str]
    ) -> str:
        """Formats note content as clean Markdown with YAML frontmatter."""
        frontmatter = {
            "id": note_id,
            "title": title,
            "created_at": created_at,
            "tags": tags,
            "hardware_backend": backend,
            "audio_duration_sec": round(duration_seconds, 2),
            "real_time_factor": round(rtf, 3)
        }

        kp_lines = "\n".join([f"- {kp}" for kp in key_points]) if key_points else "- No key takeaways noted."
        ai_lines = "\n".join([f"- [ ] {ai}" for ai in action_items]) if action_items else "- [ ] No action items identified."

        content = f"""---
{yaml.dump(frontmatter, sort_keys=False).strip()}
---

# {title}

> 🗓️ **Recorded:** {created_at[:19].replace('T', ' ')} | ⏱️ **Duration:** {duration_seconds:.1f}s | ⚡ **Inference Backend:** `{backend}`

---

## 📌 Executive Summary
{summary}

---

## 💡 Key Takeaways & Concepts
{kp_lines}

---

## ✅ Action Items & Follow-ups
{ai_lines}

---

## 🎙️ Full Audio Transcript
{transcript}
"""
        return content

    def load_note_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parses a markdown note file and extracts frontmatter and sections."""
        path = Path(file_path)
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # Parse YAML frontmatter
        frontmatter = {}
        body = raw_text
        if raw_text.startswith("---"):
            parts = raw_text.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except Exception as e:
                    logger.warning(f"Error parsing frontmatter: {e}")

        # Extract sections using regex
        summary = ""
        m_sum = re.search(r"## 📌 Executive Summary\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
        if m_sum:
            summary = m_sum.group(1).strip()

        key_points = []
        m_kp = re.search(r"## 💡 Key Takeaways & Concepts\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
        if m_kp:
            key_points = [line.lstrip("- *").strip() for line in m_kp.group(1).strip().splitlines() if line.strip()]

        action_items = []
        m_ai = re.search(r"## ✅ Action Items & Follow-ups\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
        if m_ai:
            action_items = [re.sub(r"^-\s*\[[ xX]\]\s*", "", line).strip() for line in m_ai.group(1).strip().splitlines() if line.strip()]

        transcript = ""
        m_tr = re.search(r"## 🎙️ Full Audio Transcript\s*\n(.*)", body, re.DOTALL)
        if m_tr:
            transcript = m_tr.group(1).strip()

        return {
            "id": frontmatter.get("id", path.stem),
            "title": frontmatter.get("title", path.stem),
            "created_at": frontmatter.get("created_at", ""),
            "tags": frontmatter.get("tags", []),
            "backend": frontmatter.get("hardware_backend", "CPU"),
            "duration_seconds": frontmatter.get("audio_duration_sec", 0.0),
            "rtf": frontmatter.get("real_time_factor", 0.0),
            "summary": summary,
            "key_points": key_points,
            "action_items": action_items,
            "transcript": transcript,
            "raw_markdown": raw_text,
            "file_path": str(path),
        }

    def save_existing_note(self, note_data: Dict[str, Any]) -> bool:
        """Overwrites markdown file and updates DB index when note is edited in UI."""
        file_path = Path(note_data["file_path"])
        md_content = self.render_markdown(
            note_id=note_data["id"],
            title=note_data["title"],
            summary=note_data["summary"],
            key_points=note_data.get("key_points", []),
            action_items=note_data.get("action_items", []),
            transcript=note_data.get("transcript", ""),
            created_at=note_data.get("created_at", datetime.now().isoformat()),
            duration_seconds=note_data.get("duration_seconds", 0.0),
            backend=note_data.get("backend", "CPU"),
            rtf=note_data.get("rtf", 0.0),
            tags=note_data.get("tags", [])
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        word_count = len(note_data.get("transcript", "").split()) + len(note_data.get("summary", "").split())
        self.db.update_note(note_data["id"], {
            "title": note_data["title"],
            "summary": note_data["summary"],
            "tags": note_data.get("tags", []),
            "file_path": str(file_path),
            "word_count": word_count,
        })
        return True

    def delete_note(self, note_id: str) -> bool:
        """Deletes note file from disk and removes from DB index."""
        note_meta = self.db.get_note(note_id)
        if note_meta and note_meta.get("file_path"):
            path = Path(note_meta["file_path"])
            if path.exists():
                try:
                    path.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete note file {path}: {e}")
        return self.db.delete_note(note_id)

    def _ensure_sample_notes(self):
        """Seeds sample notes if library is brand new."""
        existing = self.db.list_notes(limit=1)
        if existing:
            return

        sample_1 = {
            "title": "Snapdragon X Elite NPU Architecture Overview",
            "summary": "Introduction to the Qualcomm Hexagon NPU embedded in Snapdragon X Elite and Snapdragon X Plus HP PCs. Discusses INT4/INT8 quantization efficiency, 45 TOPS peak performance, and the ONNX Runtime QNN Execution Provider integration.",
            "key_points": [
                "Hexagon NPU delivers up to 45 TOPS dedicated compute for AI workloads without draining battery.",
                "QNN Execution Provider (HTP backend) allows seamless acceleration for ONNX models.",
                "Quantized models like Whisper w8a16 and Llama 3.2 w4a16 run at high speed locally with zero cloud dependence."
            ],
            "action_items": [
                "Benchmark Whisper Base latency on Hexagon NPU using benchmarks/run_benchmark.py.",
                "Verify QnnHtp.dll driver detection on Windows 11 on ARM."
            ],
            "transcript": "Welcome to today's lecture on on-device generative AI. Today we are exploring the architecture of the Snapdragon X Elite chip found in modern HP Copilot+ PCs. The standout feature is the Qualcomm Hexagon Neural Processing Unit, which yields over 45 TOPS of computational throughput. By offloading speech recognition and LLM inference to the NPU via the QNN Execution Provider, we preserve battery life and eliminate cloud latency entirely. Next week, we will profile memory bandwidth and quantization metrics.",
            "tags": ["Snapdragon", "Hardware", "NPU", "Architecture"],
            "duration_seconds": 124.5,
            "backend": "NPU (Snapdragon Hexagon)",
            "rtf": 0.14
        }
        self.create_note(**sample_1)
