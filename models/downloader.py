"""
OfflineMind - Model Downloader and Setup Utility
Downloads speech-to-text (Whisper) and summarization (LLM) models from Qualcomm AI Hub
or Hugging Face into the local models/weights directory.
"""

import os
import sys
import yaml
import argparse
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "models" / "config.yaml"
WEIGHTS_DIR = BASE_DIR / "models" / "weights"


def load_config():
    """Loads configuration from config.yaml."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_models_status(config):
    """Checks which models are currently downloaded."""
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    stt_active = config["speech_to_text"]["active_model"]
    llm_active = config["summarization"]["active_model"]

    print("=" * 60)
    print("OfflineMind: Local Model Weights Status")
    print("=" * 60)
    print(f"Target Directory: {WEIGHTS_DIR}")
    print(f"Active STT Model: {stt_active}")
    print(f"Active LLM Model: {llm_active}")
    print("-" * 60)

    stt_path = WEIGHTS_DIR / stt_active
    llm_path = WEIGHTS_DIR / llm_active

    stt_ready = stt_path.exists() and any(stt_path.iterdir()) if stt_path.exists() else False
    llm_ready = llm_path.exists() and any(llm_path.iterdir()) if llm_path.exists() else False

    print(f"  [{'READY' if stt_ready else 'PENDING'}] STT Model ({stt_active}): {'Installed' if stt_ready else 'Not downloaded'}")
    print(f"  [{'READY' if llm_ready else 'PENDING'}] LLM Model ({llm_active}): {'Installed' if llm_ready else 'Not downloaded'}")
    print("-" * 60)
    return stt_ready, llm_ready


def download_stt_model(model_key: str, config: dict):
    """
    Downloads speech-to-text model.
    Supports Qualcomm AI Hub models or Hugging Face Whisper ONNX.
    """
    models_dict = config["speech_to_text"]["models"]
    if model_key not in models_dict:
        print(f"Error: Unknown STT model key '{model_key}'. Available: {list(models_dict.keys())}")
        return False

    info = models_dict[model_key]
    target_dir = WEIGHTS_DIR / model_key
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[STT] Preparing {model_key}...")
    print(f"  Source: {info.get('source')}")
    print(f"  Qualcomm AI Hub ID: {info.get('qai_hub_id')}")
    print(f"  Quantization: {info.get('quantization')}")

    # Guide user on Qualcomm AI Hub export or Hugging Face retrieval
    hf_id = info.get("hf_model_id", "openai/whisper-tiny.en")
    print(f"  Downloading/Exporting base weights from '{hf_id}'...")

    try:
        from transformers import WhisperProcessor, WhisperForConditionalGeneration
        print("  Downloading Whisper processor and tokenizer for offline use...")
        processor = WhisperProcessor.from_pretrained(hf_id)
        processor.save_pretrained(target_dir)

        print("  Downloading model weights for offline inference...")
        model = WhisperForConditionalGeneration.from_pretrained(hf_id)
        model.save_pretrained(target_dir)

        # Mark ready
        with open(target_dir / "model_info.txt", "w", encoding="utf-8") as f:
            f.write(f"Model: {model_key}\nSource: {info.get('source')}\nQuantization: {info.get('quantization')}\n")

        print(f"[+] STT Model successfully prepared at: {target_dir}")
        return True
    except Exception as e:
        print(f"Notice: Automated download encountered an issue ({e}).")
        print(f"You can also export via Qualcomm AI Hub CLI:")
        print(f"  python -m qai_hub_models.models.{info.get('qai_hub_id')}.export --target-runtime qnn_lib_direct")
        return False


def download_llm_model(model_key: str, config: dict):
    """
    Downloads compact LLM for offline summarization.
    """
    models_dict = config["summarization"]["models"]
    if model_key not in models_dict:
        print(f"Error: Unknown LLM model key '{model_key}'. Available: {list(models_dict.keys())}")
        return False

    info = models_dict[model_key]
    target_dir = WEIGHTS_DIR / model_key
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[LLM] Preparing {model_key}...")
    print(f"  Source: {info.get('source')}")
    print(f"  Qualcomm AI Hub ID: {info.get('qai_hub_id')}")
    print(f"  Quantization: {info.get('quantization')}")

    hf_id = info.get("hf_model_id")
    print(f"  Fetching tokenizer and model configs for '{hf_id}'...")

    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        print("  Downloading tokenizer and offline vocabulary...")
        tokenizer = AutoTokenizer.from_pretrained(hf_id)
        tokenizer.save_pretrained(target_dir)

        print(f"  Saving configuration for offline execution...")
        model = AutoModelForCausalLM.from_pretrained(hf_id, low_cpu_mem_usage=True)
        model.save_pretrained(target_dir)

        with open(target_dir / "model_info.txt", "w", encoding="utf-8") as f:
            f.write(f"Model: {model_key}\nSource: {info.get('source')}\nQuantization: {info.get('quantization')}\n")

        print(f"[+] LLM Model successfully prepared at: {target_dir}")
        return True
    except Exception as e:
        print(f"Notice: Automated download: {e}")
        print(f"To export Snapdragon NPU optimized binary via Qualcomm AI Hub:")
        print(f"  python -m qai_hub_models.models.{info.get('qai_hub_id')}.export --target-runtime qnn_lib_direct")
        return False


def main():
    parser = argparse.ArgumentParser(description="OfflineMind Model Downloader")
    parser.add_argument("--status", action="store_true", help="Check status of downloaded models")
    parser.add_argument("--all", action="store_true", help="Download all configured active models")
    parser.add_argument("--stt", type=str, help="Specific STT model key to download")
    parser.add_argument("--llm", type=str, help="Specific LLM model key to download")
    args = parser.parse_args()

    config = load_config()

    if args.status:
        check_models_status(config)
        return

    if args.all or (not args.stt and not args.llm):
        stt_active = config["speech_to_text"]["active_model"]
        llm_active = config["summarization"]["active_model"]
        print(f"Downloading default active models: STT='{stt_active}', LLM='{llm_active}'")
        download_stt_model(stt_active, config)
        download_llm_model(llm_active, config)
        check_models_status(config)
    else:
        if args.stt:
            download_stt_model(args.stt, config)
        if args.llm:
            download_llm_model(args.llm, config)
        check_models_status(config)


if __name__ == "__main__":
    main()
