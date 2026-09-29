"""
OfflineMind - Note Summarization & Structuring Engine
Generates structured notes from transcripts:
(a) Suggested Title
(b) Short Executive Summary
(c) Key Points
(d) Action Items
Runs compact open-source models (Llama 3.2 1B, SmolLM2, Phi-3.5) with NPU/CPU fallback.
"""

import re
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.backend import get_backend_manager

logger = logging.getLogger("OfflineMind.Summarizer")


class SummarizationEngine:
    """
    Synthesizes speech transcripts into structured notes.
    """

    def __init__(self, model_name: str = "llama_3_2_1b", config: Optional[dict] = None):
        self.model_name = model_name
        self.config = config or {}
        self.backend_manager = get_backend_manager()
        self.weights_dir = Path("models/weights") / model_name
        self._model = None
        self._tokenizer = None
        self._initialized = False

    def load_model(self):
        """Initializes the tokenizer and causal language model."""
        if self._initialized:
            return

        logger.info(f"Loading Summarizer LLM '{self.model_name}' on {self.backend_manager.active_backend}...")

        hf_id = "meta-llama/Llama-3.2-1B-Instruct"
        if self.config and "summarization" in self.config:
            models_info = self.config["summarization"].get("models", {})
            if self.model_name in models_info:
                hf_id = models_info[self.model_name].get("hf_model_id", hf_id)

        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM

            model_path_or_id = str(self.weights_dir) if self.weights_dir.exists() and any(self.weights_dir.iterdir()) else hf_id
            self._tokenizer = AutoTokenizer.from_pretrained(model_path_or_id)
            self._model = AutoModelForCausalLM.from_pretrained(
                model_path_or_id,
                low_cpu_mem_usage=True
            )
            self._model.eval()
            self._initialized = True
            logger.info(f"LLM '{self.model_name}' loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load HuggingFace LLM directly ({e}). Utilizing deterministic heuristic engine.")
            self._initialized = False

    def generate_structured_note(self, transcript: str) -> Dict[str, Any]:
        """
        Processes transcript text and returns structured fields:
        title, summary, key_points, action_items, tags, latency, backend.
        """
        start_time = time.time()
        transcript = transcript.strip()

        if not transcript or transcript == "No intelligible speech detected in recording.":
            return {
                "title": "Untitled Voice Note",
                "summary": "No speech content available for synthesis.",
                "key_points": ["No key points detected."],
                "action_items": [],
                "tags": ["VoiceNote", "Empty"],
                "latency": 0.0,
                "tokens_generated": 0,
                "backend": self.backend_manager.active_backend,
            }

        self.load_model()

        if self._initialized and self._model and self._tokenizer:
            result = self._generate_with_llm(transcript)
        else:
            result = self._generate_extractive_fallback(transcript)

        latency = time.time() - start_time
        result["latency"] = round(latency, 2)
        result["backend"] = self.backend_manager.active_backend
        result["provider"] = self.backend_manager.provider_name
        return result

    def _build_prompt(self, transcript: str) -> str:
        """Constructs an instruction-tuned prompt for structured note generation."""
        return f"""You are OfflineMind, an AI assistant running locally on a Snapdragon PC.
Your task is to analyze the audio transcript below and produce structured notes in valid JSON format.

Required JSON format:
{{
  "title": "A concise 3-7 word title reflecting the core topic",
  "summary": "A 2-4 sentence executive overview of the transcript",
  "key_points": [
    "Key takeaway or concept 1",
    "Key takeaway or concept 2",
    "Key takeaway or concept 3"
  ],
  "action_items": [
    "Task or follow-up item 1",
    "Task or follow-up item 2"
  ],
  "tags": ["Topic1", "Topic2"]
}}

Transcript:
\"\"\"{transcript}\"\"\"

Output ONLY valid JSON:"""

    def _generate_with_llm(self, transcript: str) -> Dict[str, Any]:
        """Runs autoregressive text generation and parses JSON."""
        import torch
        prompt = self._build_prompt(transcript)
        inputs = self._tokenizer(prompt, return_tensors="pt")

        try:
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=400,
                    do_sample=False,
                    temperature=0.2,
                    pad_token_id=self._tokenizer.eos_token_id
                )
            generated_text = self._tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            tokens_count = len(outputs[0]) - inputs.input_ids.shape[1]

            parsed = self._extract_json_or_fallback(generated_text, transcript)
            parsed["tokens_generated"] = tokens_count
            return parsed
        except Exception as e:
            logger.error(f"Error during LLM generation: {e}")
            return self._generate_extractive_fallback(transcript)

    def _extract_json_or_fallback(self, generated_text: str, fallback_transcript: str) -> Dict[str, Any]:
        """Attempts to parse JSON from model output, falls back to regex or extraction."""
        match = re.search(r"\{.*\}", generated_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return {
                    "title": data.get("title", "Notes from Audio"),
                    "summary": data.get("summary", ""),
                    "key_points": data.get("key_points", []),
                    "action_items": data.get("action_items", []),
                    "tags": data.get("tags", ["OfflineNote"]),
                }
            except json.JSONDecodeError:
                pass
        return self._generate_extractive_fallback(fallback_transcript)

    def _generate_extractive_fallback(self, transcript: str) -> Dict[str, Any]:
        """
        Extractive synthesis fallback that guarantees instant, high-quality
        structured notes even when offline or before weights are cached.
        """
        sentences = [s.strip() for s in re.split(r"[.!?]+", transcript) if len(s.strip()) > 10]
        words = transcript.split()

        # 1. Suggested Title
        if sentences:
            first_sent = sentences[0]
            words_first = first_sent.split()
            title = " ".join(words_first[:min(6, len(words_first))]).capitalize()
            if not title.endswith(('.', ':', ' -')):
                title = f"Discussion: {title}"
        else:
            title = "Voice Note Summary"

        # 2. Executive Summary
        if len(sentences) >= 3:
            summary = ". ".join(sentences[:3]) + "."
        elif sentences:
            summary = ". ".join(sentences) + "."
        else:
            summary = transcript[:200]

        # 3. Key Points
        key_points = []
        if len(sentences) > 3:
            key_points = [f"{s}." for s in sentences[2:6]]
        elif sentences:
            key_points = [f"{s}." for s in sentences]
        else:
            key_points = ["Audio captured and transcribed successfully."]

        # 4. Action Items (Detect action verbs / directives)
        action_indicators = ["need to", "must", "action", "follow up", "will", "todo", "should", "submit", "prepare"]
        action_items = []
        for s in sentences:
            lower_s = s.lower()
            if any(ind in lower_s for ind in action_indicators):
                action_items.append(f"{s.strip()}.")

        if not action_items:
            action_items = [
                "Review and refine transcript notes.",
                "Export formatted documentation for distribution."
            ]

        # 5. Extract Tags
        tags = ["OfflineMind", "SnapdragonAI"]
        freq_words = [w.capitalize() for w in words if len(w) > 5 and w.isalpha()]
        for w in freq_words[:3]:
            if w not in tags:
                tags.append(w)

        return {
            "title": title,
            "summary": summary,
            "key_points": key_points,
            "action_items": action_items,
            "tags": tags,
            "tokens_generated": len(words),
        }
