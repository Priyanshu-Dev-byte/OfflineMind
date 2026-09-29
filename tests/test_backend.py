"""
OfflineMind - Unit Tests: Hardware Backend & Provider Fallback
"""

from core.backend import BackendManager, get_backend_manager


def test_backend_manager_initialization():
    mgr = get_backend_manager()
    assert mgr is not None
    assert mgr.system_info is not None
    assert "os" in mgr.system_info
    assert "machine" in mgr.system_info
    assert mgr.active_backend in ["NPU (Snapdragon Hexagon)", "GPU (DirectML)", "CPU"]
    assert mgr.provider_name in ["QNNExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"]


def test_badge_info_generation():
    mgr = get_backend_manager()
    badge = mgr.get_backend_badge_info()
    assert "status" in badge
    assert "label" in badge
    assert "tooltip" in badge
    assert len(badge["label"]) > 0


def test_fallback_selection_logic():
    # Test custom mock manager without QNN
    class MockBackendManager(BackendManager):
        def _get_available_providers(self):
            return ["CPUExecutionProvider"]

    mock_mgr = MockBackendManager()
    assert mock_mgr.active_backend == "CPU"
    assert mock_mgr.provider_name == "CPUExecutionProvider"
    assert mock_mgr.is_npu_active() is False
