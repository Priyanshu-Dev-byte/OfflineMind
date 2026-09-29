"""
OfflineMind - Unit Tests: Storage and Database Indexing
"""

import tempfile
import pytest
from pathlib import Path
from storage.db import NotesDatabase
from storage.notes_manager import NotesManager


import gc

@pytest.fixture
def temp_env():
    """Provides temporary directory and initialized NotesManager."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        db = NotesDatabase(tmp_path / "test.db")
        manager = NotesManager(notes_dir=tmp_path / "notes", db=db)
        yield manager, db
        del manager
        del db
        gc.collect()


def test_create_and_retrieve_note(temp_env):
    manager, db = temp_env

    note = manager.create_note(
        title="Snapdragon AI Standup",
        summary="Engineering sync discussing Hexagon NPU optimizations.",
        key_points=["Quantize models to w8a16", "Validate on Windows on ARM"],
        action_items=["Push benchmark script", "Update README"],
        transcript="Today we are syncing on Snapdragon AI integrations and benchmarking.",
        tags=["Snapdragon", "Meeting"],
        duration_seconds=45.2,
        backend="NPU (Snapdragon Hexagon)",
        rtf=0.12
    )

    assert note["id"].startswith("note_")
    assert note["title"] == "Snapdragon AI Standup"
    assert Path(note["file_path"]).exists()

    # Verify retrieval from DB
    indexed = db.get_note(note["id"])
    assert indexed is not None
    assert indexed["title"] == "Snapdragon AI Standup"
    assert "Snapdragon" in indexed["tags"]


def test_markdown_frontmatter_and_sections(temp_env):
    manager, _ = temp_env

    note = manager.create_note(
        title="Lecture: Neural Architectures",
        summary="A review of transformer and attention mechanics.",
        key_points=["Self-attention complexity", "KV caching"],
        action_items=["Complete assignment 2"],
        transcript="Welcome everyone. Today we cover attention mechanics.",
        tags=["Lecture", "AI"]
    )

    loaded = manager.load_note_file(note["file_path"])
    assert loaded is not None
    assert loaded["title"] == "Lecture: Neural Architectures"
    assert "transformer" in loaded["summary"]
    assert "KV caching" in loaded["key_points"]
    assert "Complete assignment 2" in loaded["action_items"]


def test_search_notes(temp_env):
    manager, db = temp_env

    manager.create_note(
        title="Project OfflineMind Architecture",
        summary="Discussion on local LLMs and Whisper pipelines.",
        key_points=["Zero cloud reliance"],
        action_items=[],
        transcript="Offline mind allows local note taking without cloud.",
        tags=["Architecture", "Snapdragon"]
    )

    manager.create_note(
        title="Grocery Shopping List",
        summary="Weekly personal chores.",
        key_points=["Apples", "Milk"],
        action_items=["Buy groceries"],
        transcript="Remember to get milk and apples.",
        tags=["Personal"]
    )

    # Search keyword
    res_arch = db.search_notes("OfflineMind")
    assert len(res_arch) == 1
    assert res_arch[0]["title"] == "Project OfflineMind Architecture"

    # Search with tag filter
    res_snap = db.search_notes("local", tag="Snapdragon")
    assert len(res_snap) == 1

    # Search non-matching
    res_none = db.search_notes("QuantumComputing123")
    assert len(res_none) == 0


def test_update_and_delete_note(temp_env):
    manager, db = temp_env

    note = manager.create_note(
        title="Initial Draft",
        summary="Initial summary.",
        key_points=["Point 1"],
        action_items=["Task 1"],
        transcript="Audio draft.",
        tags=["Draft"]
    )

    # Update
    note["title"] = "Updated Title Final"
    note["summary"] = "Refined executive summary."
    manager.save_existing_note(note)

    updated_db = db.get_note(note["id"])
    assert updated_db["title"] == "Updated Title Final"
    assert updated_db["summary"] == "Refined executive summary."

    # Delete
    deleted = manager.delete_note(note["id"])
    assert deleted is True
    assert db.get_note(note["id"]) is None
    assert not Path(note["file_path"]).exists()
