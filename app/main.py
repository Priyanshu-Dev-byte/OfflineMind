"""
OfflineMind - Main Streamlit Application
A private, fully offline AI assistant that turns lectures, meetings, and voice notes
into structured notes on Snapdragon-powered HP PCs (Windows on ARM) with automatic CPU fallback.
"""

import sys
import io
import os
import yaml
import tempfile
from pathlib import Path
from datetime import datetime

import streamlit as st

# Add workspace root to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.backend import get_backend_manager
from core.audio import load_and_preprocess_audio, save_wav_file
from core.transcription import SpeechToTextEngine
from core.summarization import SummarizationEngine
from storage.notes_manager import NotesManager
from storage.exporter import NoteExporter
from app.ui_components import apply_custom_css, render_hardware_badge

# Page configuration
st.set_page_config(
    page_title="OfflineMind | Private On-Device AI Notes",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize singletons in session state
if "notes_manager" not in st.session_state:
    st.session_state.notes_manager = NotesManager()

if "backend_mgr" not in st.session_state:
    st.session_state.backend_mgr = get_backend_manager()

if "active_note" not in st.session_state:
    # Load first existing note from database if present
    notes = st.session_state.notes_manager.db.list_notes(limit=1)
    if notes:
        st.session_state.active_note = st.session_state.notes_manager.load_note_file(notes[0]["file_path"])
    else:
        st.session_state.active_note = None

# Apply styling
apply_custom_css()

# Sidebar: Hardware Diagnostics & Model Configuration
with st.sidebar:
    st.markdown("### 🧠 OfflineMind")
    st.caption("Private On-Device AI for Snapdragon HP PCs")
    st.markdown("---")

    # Backend Badge
    badge_info = st.session_state.backend_mgr.get_backend_badge_info()
    st.markdown("**Active Hardware Accelerator:**")
    render_hardware_badge(badge_info)
    st.caption(f"Provider: `{st.session_state.backend_mgr.provider_name}`")

    with st.expander("🔍 System & NPU Details", expanded=False):
        sys_info = st.session_state.backend_mgr.system_info
        st.write(f"**OS:** {sys_info['os']} ({sys_info['machine']})")
        st.write(f"**Processor:** {sys_info['processor']}")
        st.write(f"**ARM64 Architecture:** {'Yes' if sys_info['is_arm64'] else 'No (x86/x64)'}")
        st.write(f"**Hexagon NPU Support:** {'Available' if st.session_state.backend_mgr.is_npu_active() else 'CPU Fallback'}")
        st.write(f"**All ONNX Providers:**")
        for p in st.session_state.backend_mgr.available_providers:
            st.code(p, language="text")

    st.markdown("---")
    st.markdown("### ⚙️ Models Config")
    config_path = ROOT_DIR / "models" / "config.yaml"
    models_config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            models_config = yaml.safe_load(f)

    stt_models = list(models_config.get("speech_to_text", {}).get("models", {}).keys()) or ["whisper_base_en"]
    selected_stt = st.selectbox("Speech-to-Text Model", stt_models, index=0)

    llm_models = list(models_config.get("summarization", {}).get("models", {}).keys()) or ["llama_3_2_1b"]
    selected_llm = st.selectbox("Summarization Model", llm_models, index=0)

    st.markdown("---")
    st.caption("🔒 100% On-Device: Zero telemetry, zero cloud calls, zero API keys required.")


# Main App Header
col_header_left, col_header_right = st.columns([3, 1])
with col_header_left:
    st.markdown('<div class="app-title">OfflineMind</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">Private, fully offline voice notes and meeting synthesis targeting Snapdragon HP PCs.</div>',
        unsafe_allow_html=True
    )
with col_header_right:
    st.markdown("<div style='text-align: right; padding-top: 10px;'>", unsafe_allow_html=True)
    render_hardware_badge(badge_info)
    st.markdown("</div>", unsafe_allow_html=True)

# Navigation Tabs
tab_record, tab_editor, tab_library, tab_export, tab_bench = st.tabs([
    "🎙️ Record & Import",
    "📝 Note Editor",
    "📚 Notes Library & Search",
    "📤 Export & Share",
    "⚡ Hardware & Benchmarks"
])


# ==============================================================================
# TAB 1: RECORD & IMPORT
# ==============================================================================
with tab_record:
    st.subheader("Capture or Ingest Audio")
    st.markdown("Record from your microphone or import an existing audio recording (`.wav`, `.mp3`, `.m4a`).")

    col_rec_opt1, col_rec_opt2 = st.columns(2)
    audio_data_bytes = None
    input_source_name = "recording.wav"

    with col_rec_opt1:
        st.markdown("#### 🎙️ Live Microphone Input")
        try:
            # Streamlit 1.35+ built-in audio input
            mic_audio = st.audio_input("Record Voice Note / Lecture snippet")
            if mic_audio is not None:
                audio_data_bytes = mic_audio.read()
                input_source_name = "Live_Mic_Capture.wav"
        except Exception:
            st.info("Direct mic input available via browser interface.")

    with col_rec_opt2:
        st.markdown("#### 📂 Import Audio File")
        uploaded_file = st.file_uploader("Upload audio file", type=["wav", "mp3", "m4a", "flac"])
        if uploaded_file is not None:
            audio_data_bytes = uploaded_file.read()
            input_source_name = uploaded_file.name

    if audio_data_bytes:
        st.markdown("---")
        st.markdown(f"**Loaded Audio:** `{input_source_name}` ({len(audio_data_bytes) / 1024:.1f} KB)")
        st.audio(audio_data_bytes)

        if st.button("⚡ Process Audio & Synthesize Note", type="primary", use_container_width=True):
            progress_bar = st.progress(0, text="Initializing on-device AI pipelines...")

            try:
                # 1. Preprocess
                progress_bar.progress(15, text="Preprocessing audio to 16kHz mono PCM...")
                audio_arr, duration = load_and_preprocess_audio(audio_data_bytes)

                # 2. Transcribe with Whisper
                progress_bar.progress(35, text=f"Transcribing audio with {selected_stt} on {st.session_state.backend_mgr.active_backend}...")
                stt_engine = SpeechToTextEngine(model_name=selected_stt, config=models_config)
                stt_result = stt_engine.transcribe(audio_arr)

                # 3. Summarize with Compact LLM
                progress_bar.progress(70, text=f"Generating structured note with {selected_llm}...")
                llm_engine = SummarizationEngine(model_name=selected_llm, config=models_config)
                llm_result = llm_engine.generate_structured_note(stt_result["text"])

                # 4. Save to Disk and SQLite Index
                progress_bar.progress(90, text="Writing Markdown file and indexing in SQLite...")
                new_note = st.session_state.notes_manager.create_note(
                    title=llm_result.get("title", f"Note: {input_source_name}"),
                    summary=llm_result.get("summary", ""),
                    key_points=llm_result.get("key_points", []),
                    action_items=llm_result.get("action_items", []),
                    transcript=stt_result.get("text", ""),
                    tags=llm_result.get("tags", ["AudioCapture"]),
                    duration_seconds=duration,
                    backend=st.session_state.backend_mgr.active_backend,
                    rtf=stt_result.get("rtf", 0.0)
                )

                st.session_state.active_note = new_note
                progress_bar.progress(100, text="Done!")
                st.success(f"🎉 Note '{new_note['title']}' created successfully!")
                st.balloons()
            except Exception as e:
                st.error(f"Error processing audio: {e}")


# ==============================================================================
# TAB 2: NOTE EDITOR
# ==============================================================================
with tab_editor:
    note = st.session_state.active_note
    if not note:
        st.info("No note currently selected. Please capture audio or select a note from the Library.")
    else:
        st.subheader("View and Edit Structured Note")

        # Performance bar
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.metric("Audio Duration", f"{float(note.get('duration_seconds', 0.0)):.1f}s")
        with m_col2:
            st.metric("Hardware Backend", note.get("backend", "CPU"))
        with m_col3:
            st.metric("Real-Time Factor", f"{float(note.get('rtf', 0.0)):.2f}x")
        with m_col4:
            st.metric("Created At", str(note.get("created_at", ""))[:10])

        with st.form("edit_note_form"):
            edit_title = st.text_input("Suggested Title", value=note.get("title", ""))
            edit_summary = st.text_area("📌 Executive Summary", value=note.get("summary", ""), height=110)

            # Key points editor
            current_kp_str = "\n".join(note.get("key_points", []))
            edit_kp = st.text_area("💡 Key Takeaways & Concepts (one per line)", value=current_kp_str, height=120)

            # Action items editor
            current_ai_str = "\n".join(note.get("action_items", []))
            edit_ai = st.text_area("✅ Action Items (one per line)", value=current_ai_str, height=110)

            # Full transcript
            edit_transcript = st.text_area("🎙️ Full Audio Transcript", value=note.get("transcript", ""), height=150)

            # Tags
            current_tags_str = ", ".join(note.get("tags", []))
            edit_tags = st.text_input("Tags (comma separated)", value=current_tags_str)

            col_btn_save, _ = st.columns([1, 4])
            with col_btn_save:
                submitted = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)

            if submitted:
                updated_data = dict(note)
                updated_data["title"] = edit_title
                updated_data["summary"] = edit_summary
                updated_data["key_points"] = [p.strip() for p in edit_kp.splitlines() if p.strip()]
                updated_data["action_items"] = [a.strip() for a in edit_ai.splitlines() if a.strip()]
                updated_data["transcript"] = edit_transcript
                updated_data["tags"] = [t.strip() for t in edit_tags.split(",") if t.strip()]

                st.session_state.notes_manager.save_existing_note(updated_data)
                st.session_state.active_note = updated_data
                st.success("Note saved and database index updated!")
                st.rerun()


# ==============================================================================
# TAB 3: NOTES LIBRARY & SEARCH
# ==============================================================================
with tab_library:
    st.subheader("Stored Notes Library (SQLite Indexed)")

    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_query = st.text_input("🔍 Search notes by keyword, title, or topic...", placeholder="e.g. Snapdragon, architecture, follow up")
    with search_col2:
        search_tag = st.text_input("🏷️ Filter by tag", placeholder="e.g. Architecture")

    db = st.session_state.notes_manager.db
    if search_query or search_tag:
        notes_list = db.search_notes(search_query, tag=search_tag if search_tag else None)
    else:
        notes_list = db.list_notes(limit=30)

    st.markdown(f"Found **{len(notes_list)}** notes in local database.")

    for n in notes_list:
        with st.container():
            st.markdown(f"""
                <div class="note-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #0F172A;">{n['title']}</h4>
                        <span style="font-size: 0.8rem; color: #64748B;">{str(n['created_at'])[:10]}</span>
                    </div>
                    <p style="margin-top: 8px; margin-bottom: 10px; color: #334155; font-size: 0.95rem;">
                        {n.get('summary', '')[:220]}...
                    </p>
                    <div>
                        {''.join([f'<span class="tag-pill">#{t}</span>' for t in n.get('tags', [])])}
                        <span style="font-size: 0.8rem; color: #94A3B8; margin-left: 8px;">
                            ⏱️ {float(n.get('duration_seconds', 0.0)):.1f}s | ⚡ {n.get('backend', 'CPU')}
                        </span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            card_c1, card_c2, _ = st.columns([1, 1, 4])
            with card_c1:
                if st.button("Open in Editor", key=f"open_{n['id']}"):
                    loaded = st.session_state.notes_manager.load_note_file(n["file_path"])
                    if loaded:
                        st.session_state.active_note = loaded
                        st.rerun()
            with card_c2:
                if st.button("Delete Note", key=f"del_{n['id']}", type="secondary"):
                    st.session_state.notes_manager.delete_note(n["id"])
                    if st.session_state.active_note and st.session_state.active_note.get("id") == n["id"]:
                        st.session_state.active_note = None
                    st.warning(f"Deleted {n['title']}")
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)


# ==============================================================================
# TAB 4: EXPORT & SHARE
# ==============================================================================
with tab_export:
    note = st.session_state.active_note
    if not note:
        st.info("No active note to export. Please select or create a note first.")
    else:
        st.subheader("Export Note (Markdown & PDF)")
        st.markdown(f"**Current Note:** `{note.get('title', 'Untitled')}`")

        # Markdown string
        md_text = NoteExporter.export_markdown(note)

        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.markdown("#### 📄 Markdown Export")
            st.caption("Clean text file with YAML frontmatter, compatible with Obsidian, Notion, and GitHub.")
            st.download_button(
                label="⬇️ Download Markdown (.md)",
                data=md_text,
                file_name=f"{note.get('title', 'note').replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )

        with col_exp2:
            st.markdown("#### 📑 Formatted PDF Export")
            st.caption("Polished, printable PDF report generated 100% on-device using pure Python.")

            # Generate PDF to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                pdf_temp_path = tmp_pdf.name

            try:
                NoteExporter.export_pdf(note, pdf_temp_path)
                with open(pdf_temp_path, "rb") as pf:
                    pdf_bytes = pf.read()

                st.download_button(
                    label="⬇️ Download Formatted PDF (.pdf)",
                    data=pdf_bytes,
                    file_name=f"{note.get('title', 'note').replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error generating PDF: {e}")
            finally:
                if os.path.exists(pdf_temp_path):
                    try:
                        os.unlink(pdf_temp_path)
                    except Exception:
                        pass

        st.markdown("---")
        st.markdown("#### 👁️ Raw Markdown Preview")
        st.text_area("Markdown Source", value=md_text, height=280)


# ==============================================================================
# TAB 5: HARDWARE & BENCHMARKS
# ==============================================================================
with tab_bench:
    st.subheader("Snapdragon Hardware Diagnostic & Benchmarks")
    st.markdown("Built for the **Snapdragon AI Lab Build & Present Challenge**.")

    col_diag1, col_diag2 = st.columns(2)
    with col_diag1:
        st.markdown("#### 🖥️ Hardware Specification")
        sys_info = st.session_state.backend_mgr.system_info
        st.write(f"- **Operating System:** {sys_info['os']} {sys_info['os_release']}")
        st.write(f"- **CPU Architecture:** {sys_info['machine']}")
        st.write(f"- **Processor Identifier:** {sys_info['processor']}")
        st.write(f"- **Windows on ARM:** {'Yes (ARM64)' if sys_info['is_arm64'] else 'x86_64 emulator/standard'}")

    with col_diag2:
        st.markdown("#### ⚡ ONNX Runtime Execution Providers")
        active_p = st.session_state.backend_mgr.provider_name
        st.write(f"- **Active Provider:** `{active_p}`")
        st.write(f"- **Hardware Target:** `{st.session_state.backend_mgr.active_backend}`")
        if "QNN" in active_p:
            st.success("Qualcomm Hexagon NPU hardware accelerator is ACTIVE.")
        else:
            st.info("Running in CPU Fallback Mode. On Snapdragon HP PCs, ensure `onnxruntime-qnn` is installed to offload workloads to Hexagon HTP NPU.")

    st.markdown("---")
    st.markdown("#### 📊 Benchmark Suite")
    st.caption("Measure on-device latency, Real-Time Factor (RTF), and generation throughput.")

    if st.button("🚀 Run Live Benchmark Now"):
        with st.spinner("Benchmarking transcription and summarization workloads..."):
            stt_engine = SpeechToTextEngine(model_name=selected_stt, config=models_config)
            test_audio = (0.5 * load_and_preprocess_audio(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")[0]) if False else None

            # Synthetic test
            from benchmarks.run_benchmark import run_stt_benchmark, run_llm_benchmark
            stt_res = run_stt_benchmark(stt_engine, duration_sec=5.0, runs=1)
            llm_engine = SummarizationEngine(model_name=selected_llm, config=models_config)
            llm_res = run_llm_benchmark(llm_engine, runs=1)

            st.success("Benchmark completed!")
            b_c1, b_c2, b_c3 = st.columns(3)
            with b_c1:
                st.metric("STT Latency (5s Audio)", f"{stt_res['avg_latency_s']}s")
            with b_c2:
                st.metric("STT Real-Time Factor (RTF)", f"{stt_res['avg_rtf']}x")
            with b_c3:
                st.metric("LLM Latency", f"{llm_res['avg_latency_s']}s")

            st.markdown(f"Command line benchmark runner available: `python benchmarks/run_benchmark.py`")
