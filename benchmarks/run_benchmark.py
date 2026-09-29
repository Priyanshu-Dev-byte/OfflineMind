"""
OfflineMind - Benchmark Suite (CPU vs Snapdragon Hexagon NPU)
Measures Speech-to-Text latency, Real-Time Factor (RTF), and LLM generation throughput.
Outputs formatted Markdown comparison tables ready for documentation and reports.
"""

import sys
import time
import argparse
import platform
import numpy as np
from pathlib import Path
from tabulate import tabulate

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.backend import get_backend_manager
from core.audio import TARGET_SAMPLE_RATE
from core.transcription import SpeechToTextEngine
from core.summarization import SummarizationEngine


def generate_synthetic_audio(duration_sec: float = 10.0) -> np.ndarray:
    """Generates standard test audio signal for repeatable benchmarking."""
    t = np.linspace(0, duration_sec, int(TARGET_SAMPLE_RATE * duration_sec), endpoint=False)
    # Sine wave mix simulating fundamental speech frequencies (150Hz + 300Hz)
    audio = 0.5 * np.sin(2 * np.pi * 150 * t) + 0.3 * np.sin(2 * np.pi * 300 * t)
    return audio.astype(np.float32)


SAMPLE_BENCHMARK_TRANSCRIPT = (
    "In today's lecture on artificial intelligence systems, we analyzed edge computing architectures. "
    "Deploying neural networks directly onto Qualcomm Snapdragon X Series hardware enables zero-latency "
    "local inference while maintaining strict user data privacy. Key components include the Hexagon NPU, "
    "ONNX Runtime QNN Execution Provider, and INT8 INT4 quantization pipelines. "
    "Action items for the engineering team: benchmark Whisper model latency and compile Llama 3.2 binaries."
)


def run_stt_benchmark(engine: SpeechToTextEngine, duration_sec: float = 10.0, runs: int = 3):
    """Measures STT latency and Real-Time Factor (RTF)."""
    test_audio = generate_synthetic_audio(duration_sec)
    latencies = []

    print(f"Running STT benchmark ({runs} iterations, {duration_sec}s audio)...")
    for r in range(runs):
        start = time.perf_counter()
        _ = engine.transcribe(test_audio)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)
        print(f"  Run {r + 1}/{runs}: {elapsed:.3f}s (RTF: {elapsed / duration_sec:.3f})")

    avg_latency = float(np.mean(latencies))
    avg_rtf = avg_latency / duration_sec
    return {
        "model": engine.model_name,
        "audio_duration_s": duration_sec,
        "avg_latency_s": round(avg_latency, 3),
        "avg_rtf": round(avg_rtf, 3),
    }


def run_llm_benchmark(engine: SummarizationEngine, runs: int = 3):
    """Measures LLM note synthesis latency and generation throughput."""
    latencies = []
    tokens = []

    print(f"Running LLM benchmark ({runs} iterations)...")
    for r in range(runs):
        start = time.perf_counter()
        res = engine.generate_structured_note(SAMPLE_BENCHMARK_TRANSCRIPT)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)
        tokens.append(res.get("tokens_generated", 50))
        print(f"  Run {r + 1}/{runs}: {elapsed:.3f}s")

    avg_latency = float(np.mean(latencies))
    avg_tokens = float(np.mean(tokens))
    tokens_per_sec = avg_tokens / max(avg_latency, 0.001)

    return {
        "model": engine.model_name,
        "avg_latency_s": round(avg_latency, 3),
        "tokens_per_sec": round(tokens_per_sec, 2),
    }


def format_markdown_table(benchmark_data: dict, output_file: Path):
    """Generates formatted Markdown tables comparing CPU vs Snapdragon NPU."""
    headers = [
        "Workload / Model",
        "Hardware Target",
        "Execution Provider",
        "Latency (s)",
        "Throughput / RTF",
        "Speedup"
    ]

    rows = []
    if benchmark_data:
        b = benchmark_data
        rows.append([
            f"STT: {b['stt']['model']} ({b['stt']['audio_duration_s']}s audio)",
            b["backend_label"],
            b["provider"],
            f"{b['stt']['avg_latency_s']}s",
            f"RTF {b['stt']['avg_rtf']}x",
            "Baseline (Active)"
        ])
        rows.append([
            f"LLM: {b['llm']['model']} (Note Synthesis)",
            b["backend_label"],
            b["provider"],
            f"{b['llm']['avg_latency_s']}s",
            f"{b['llm']['tokens_per_sec']} tok/s",
            "Baseline (Active)"
        ])

    table_md = tabulate(rows, headers=headers, tablefmt="github")

    report = f"""# OfflineMind Benchmark Results

**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Machine:** {platform.machine()} ({platform.system()})  
**Processor:** {platform.processor()}  

### Measured Performance Table

{table_md}

---

### Hardware Comparison Template (Snapdragon NPU vs CPU)

| Workload / Model | Metric | CPU Baseline (x86 / Oryon) | Snapdragon Hexagon NPU (QNN) | NPU Efficiency Gain |
| :--- | :--- | :--- | :--- | :--- |
| **Whisper Base (10s audio)** | Latency | *[Pending Hardware Run]* | *[Pending Hardware Run]* | *[Pending Hardware Run]* |
| **Whisper Base (10s audio)** | Real-Time Factor (RTF) | *[Pending Hardware Run]* | *[Pending Hardware Run]* | *[Pending Hardware Run]* |
| **Llama 3.2 1B (w4a16)** | Synthesis Latency | *[Pending Hardware Run]* | *[Pending Hardware Run]* | *[Pending Hardware Run]* |
| **Llama 3.2 1B (w4a16)** | Generation Speed | *[Pending Hardware Run]* | *[Pending Hardware Run]* | *[Pending Hardware Run]* |
| **Full Pipeline Energy** | Power Draw | *[Pending Hardware Run]* | *[Pending Hardware Run]* | *[Pending Hardware Run]* |

> **Note:** As required by the Snapdragon AI Lab Build & Present Challenge, results are left unpopulated until measured on genuine Snapdragon hardware.
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nSaved benchmark report to: {output_file}")
    print("\n" + report)


def main():
    parser = argparse.ArgumentParser(description="OfflineMind Performance Benchmark")
    parser.add_argument("--runs", type=int, default=3, help="Number of benchmark iterations")
    parser.add_argument("--duration", type=float, default=10.0, help="Audio duration for STT test in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Generate template without executing models")
    args = parser.parse_args()

    output_file = Path(__file__).resolve().parent / "benchmark_results.md"
    backend = get_backend_manager()

    print("=" * 65)
    print("OfflineMind Performance Benchmark")
    print(f"Target Hardware: {backend.system_info['processor']} ({backend.system_info['machine']})")
    print(f"Active Provider: {backend.provider_name} ({backend.active_backend})")
    print("=" * 65)

    if args.dry_run:
        print("Dry run requested. Generating benchmark template markdown...")
        format_markdown_table({}, output_file)
        return

    stt_engine = SpeechToTextEngine()
    stt_res = run_stt_benchmark(stt_engine, duration_sec=args.duration, runs=args.runs)

    llm_engine = SummarizationEngine()
    llm_res = run_llm_benchmark(llm_engine, runs=args.runs)

    benchmark_data = {
        "backend_label": backend.active_backend,
        "provider": backend.provider_name,
        "stt": stt_res,
        "llm": llm_res,
    }

    format_markdown_table(benchmark_data, output_file)


if __name__ == "__main__":
    main()
