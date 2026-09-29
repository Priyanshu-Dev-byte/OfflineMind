"""
OfflineMind - Hardware Backend & Execution Provider Detection
Detects Qualcomm Hexagon NPU (via QNNExecutionProvider in ONNX Runtime)
and automatically falls back to CPUExecutionProvider on non-Snapdragon machines.
"""

import os
import platform
import logging
from typing import Dict, Any, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OfflineMind.Backend")


class BackendManager:
    """
    Manages ONNX Runtime execution provider selection and hardware acceleration.
    Prefers Snapdragon Hexagon NPU via QNNExecutionProvider.
    """

    def __init__(self):
        self.system_info = self._detect_system_info()
        self.available_providers = self._get_available_providers()
        self.active_backend, self.provider_name, self.provider_options = self._select_best_provider()
        self._log_status()

    def _detect_system_info(self) -> Dict[str, Any]:
        """Collects operating system and architecture information."""
        machine = platform.machine().lower()
        system = platform.system()
        processor = platform.processor()

        is_arm = "arm" in machine or "aarch64" in machine
        is_windows = system == "Windows"
        is_snapdragon_likely = is_arm and (is_windows or "snapdragon" in processor.lower() or "qualcomm" in processor.lower())

        return {
            "os": system,
            "os_release": platform.release(),
            "machine": platform.machine(),
            "processor": processor,
            "is_arm64": is_arm,
            "is_windows": is_windows,
            "is_snapdragon_hardware": is_snapdragon_likely,
        }

    def _get_available_providers(self) -> List[str]:
        """Retrieves list of installed ONNX Runtime execution providers."""
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            logger.info(f"Available ONNX Execution Providers: {providers}")
            return providers
        except ImportError:
            logger.warning("onnxruntime is not installed. Defaulting to CPU fallback.")
            return ["CPUExecutionProvider"]
        except Exception as e:
            logger.warning(f"Error querying ONNX Runtime providers: {e}")
            return ["CPUExecutionProvider"]

    def _select_best_provider(self) -> Tuple[str, str, Dict[str, Any]]:
        """
        Selects the best available execution provider:
        1. QNNExecutionProvider (Qualcomm Hexagon NPU on Snapdragon)
        2. DmlExecutionProvider (DirectML GPU fallback on Windows)
        3. CPUExecutionProvider (Universal CPU fallback)
        """
        # 1. Check for Qualcomm Hexagon NPU via QNN
        if "QNNExecutionProvider" in self.available_providers:
            qnn_options = {
                "backend_path": "QnnHtp.dll",  # Hexagon Tensor Processor (HTP)
                "htp_performance_mode": "burst",
                "enable_htp_fp16_precision": "1",
            }
            logger.info("Snapdragon Hexagon NPU detected via QNNExecutionProvider.")
            return "NPU (Snapdragon Hexagon)", "QNNExecutionProvider", qnn_options

        # 2. Check for DirectML (Windows acceleration fallback)
        if "DmlExecutionProvider" in self.available_providers and self.system_info["is_windows"]:
            logger.info("DirectML execution provider detected.")
            return "GPU (DirectML)", "DmlExecutionProvider", {}

        # 3. Universal CPU fallback
        logger.info("Using CPUExecutionProvider (universal fallback mode).")
        return "CPU", "CPUExecutionProvider", {}

    def _log_status(self):
        """Logs the chosen backend status."""
        logger.info(
            f"OfflineMind Hardware Detection: OS={self.system_info['os']} ({self.system_info['machine']}), "
            f"Active Backend={self.active_backend} ({self.provider_name})"
        )

    def is_npu_active(self) -> bool:
        """Returns True if running accelerated on Qualcomm NPU."""
        return "NPU" in self.active_backend

    def get_backend_badge_info(self) -> Dict[str, str]:
        """
        Returns display-ready data for UI status indicators.
        """
        if self.is_npu_active():
            return {
                "status": "active_npu",
                "label": "⚡ Snapdragon NPU (QNN)",
                "color": "#00A86B",  # Green
                "tooltip": "Running on Qualcomm Hexagon NPU via QNNExecutionProvider (Low Power, High Speed)",
                "details": f"{self.active_backend} | Provider: {self.provider_name}",
            }
        elif "GPU" in self.active_backend:
            return {
                "status": "active_gpu",
                "label": "🎮 GPU DirectML (Active)",
                "color": "#3B82F6",  # Blue
                "tooltip": "Running on Windows DirectML GPU acceleration",
                "details": f"{self.active_backend} | Provider: {self.provider_name}",
            }
        else:
            return {
                "status": "active_cpu",
                "label": "💻 CPU Fallback Mode",
                "color": "#F59E0B",  # Amber/Orange
                "tooltip": "Running on CPU. To enable Snapdragon NPU acceleration, install onnxruntime-qnn on Windows on ARM.",
                "details": f"{self.active_backend} | Provider: {self.provider_name}",
            }

    def get_providers_for_session(self) -> List[Any]:
        """
        Returns the providers list formatted for ort.InferenceSession.
        """
        if self.provider_name == "QNNExecutionProvider":
            return [(self.provider_name, self.provider_options), "CPUExecutionProvider"]
        return [self.provider_name]

    def create_inference_session(self, model_path: str):
        """
        Creates an ONNX Runtime InferenceSession with the selected provider,
        automatically handling fallback if initialization fails.
        """
        try:
            import onnxruntime as ort
        except ImportError:
            raise RuntimeError("onnxruntime is not installed. Please run: pip install onnxruntime")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        # Try primary provider
        try:
            providers = self.get_providers_for_session()
            session = ort.InferenceSession(model_path, sess_options=session_options, providers=providers)
            logger.info(f"Initialized ONNX Session with providers: {session.get_providers()}")
            return session
        except Exception as e:
            logger.warning(f"Failed to initialize session with {self.provider_name} ({e}). Falling back to CPUExecutionProvider...")
            return ort.InferenceSession(model_path, sess_options=session_options, providers=["CPUExecutionProvider"])


# Singleton instance
_backend_manager = None


def get_backend_manager() -> BackendManager:
    """Returns singleton instance of BackendManager."""
    global _backend_manager
    if _backend_manager is None:
        _backend_manager = BackendManager()
    return _backend_manager
