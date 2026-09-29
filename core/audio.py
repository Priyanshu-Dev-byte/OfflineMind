"""
OfflineMind - Audio Processing and Normalization
Handles audio ingestion (wav, mp3, m4a), resampling to 16kHz mono PCM for Whisper models,
and waveform extraction for UI visualization.
"""

import io
import os
import wave
import logging
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Union

logger = logging.getLogger("OfflineMind.Audio")

TARGET_SAMPLE_RATE = 16000


def load_and_preprocess_audio(
    file_or_bytes: Union[str, Path, bytes, io.BytesIO],
    target_sr: int = TARGET_SAMPLE_RATE
) -> Tuple[np.ndarray, float]:
    """
    Loads audio from a file path or raw bytes, converts to mono, and resamples to target_sr.
    Returns:
        audio_array (np.ndarray): 1D float32 numpy array normalized to [-1.0, 1.0].
        duration (float): Audio duration in seconds.
    """
    try:
        import soundfile as sf
    except ImportError:
        raise RuntimeError("soundfile package is required for audio processing.")

    # 1. Read audio stream or file
    if isinstance(file_or_bytes, (str, Path)):
        audio_path = str(file_or_bytes)
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        data, sr = sf.read(audio_path, dtype="float32")
    else:
        # Byte buffer
        if isinstance(file_or_bytes, bytes):
            bio = io.BytesIO(file_or_bytes)
        else:
            bio = file_or_bytes
        data, sr = sf.read(bio, dtype="float32")

    # 2. Convert to mono if multi-channel
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    # 3. Resample if necessary
    if sr != target_sr:
        data = resample_audio(data, orig_sr=sr, target_sr=target_sr)

    # 4. Normalize peak amplitude
    max_val = np.max(np.abs(data))
    if max_val > 0:
        data = data / max_val

    duration = float(len(data)) / float(target_sr)
    return data.astype(np.float32), duration


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resamples 1D audio array using scipy.signal.resample or linear interpolation.
    """
    if orig_sr == target_sr:
        return audio

    try:
        from scipy import signal
        num_samples = int(round(len(audio) * float(target_sr) / float(orig_sr)))
        resampled = signal.resample(audio, num_samples)
        return resampled.astype(np.float32)
    except Exception as e:
        logger.warning(f"SciPy resample failed ({e}), using linear interpolation fallback.")
        # Fast linear interpolation fallback
        orig_indices = np.linspace(0, len(audio) - 1, len(audio))
        num_samples = int(round(len(audio) * float(target_sr) / float(orig_sr)))
        target_indices = np.linspace(0, len(audio) - 1, num_samples)
        return np.interp(target_indices, orig_indices, audio).astype(np.float32)


def chunk_audio(audio: np.ndarray, sample_rate: int = TARGET_SAMPLE_RATE, chunk_duration_sec: int = 30) -> list:
    """
    Splits long audio into standard 30-second windows for Whisper processing.
    Each chunk is padded to 30s if shorter.
    """
    chunk_size = sample_rate * chunk_duration_sec
    chunks = []
    total_len = len(audio)

    for start in range(0, total_len, chunk_size):
        end = min(start + chunk_size, total_len)
        chunk = audio[start:end]
        # Pad with zeros to exactly 30s if needed
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode="constant")
        chunks.append(chunk)

    return chunks


def save_wav_file(audio: np.ndarray, output_path: Union[str, Path], sample_rate: int = TARGET_SAMPLE_RATE):
    """Saves a float32 or int16 numpy array as a standard 16kHz mono WAV file."""
    import soundfile as sf
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), audio, sample_rate, subtype="PCM_16")
    logger.info(f"Saved audio to {output_path}")


def get_waveform_points(audio: np.ndarray, num_points: int = 100) -> list:
    """
    Downsamples audio to a list of amplitude heights (0.0 to 1.0) for visual UI waveform preview.
    """
    if len(audio) == 0:
        return [0.0] * num_points
    step = max(1, len(audio) // num_points)
    points = []
    for i in range(0, min(len(audio), step * num_points), step):
        chunk = audio[i : i + step]
        points.append(float(np.max(np.abs(chunk))))
    while len(points) < num_points:
        points.append(0.0)
    return points[:num_points]
