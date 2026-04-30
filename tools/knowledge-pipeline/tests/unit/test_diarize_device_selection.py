from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from kp.sources.voice_memo.diarize.whisperx_backend import (
    WhisperXBackend,
    _resolve_device,
)


# ---------------------------------------------------------------------------
# Helpers to monkeypatch torch and platform
# ---------------------------------------------------------------------------

def _make_torch_stub(mps_available: bool) -> types.ModuleType:
    """Return a minimal fake torch module with backends.mps.is_available()."""
    torch_mod = types.ModuleType("torch")
    backends = types.SimpleNamespace(
        mps=types.SimpleNamespace(is_available=lambda: mps_available)
    )
    torch_mod.backends = backends
    return torch_mod


# ---------------------------------------------------------------------------
# _resolve_device unit tests
# ---------------------------------------------------------------------------

class TestResolveDevice:
    def test_explicit_cpu_is_respected(self):
        """Passing device='cpu' directly bypasses resolution."""
        assert _resolve_device("cpu") == "cpu"

    def test_explicit_mps_is_respected(self):
        """Passing device='mps' directly bypasses resolution."""
        assert _resolve_device("mps") == "mps"

    def test_auto_resolves_to_mps_when_available(self, monkeypatch):
        """device='auto' → 'mps' when running on arm64 with MPS available."""
        monkeypatch.setattr("platform.machine", lambda: "arm64")
        torch_stub = _make_torch_stub(mps_available=True)
        monkeypatch.setitem(sys.modules, "torch", torch_stub)

        assert _resolve_device("auto") == "mps"

    def test_auto_resolves_to_cpu_when_mps_unavailable(self, monkeypatch):
        """device='auto' → 'cpu' when MPS is not available."""
        monkeypatch.setattr("platform.machine", lambda: "arm64")
        torch_stub = _make_torch_stub(mps_available=False)
        monkeypatch.setitem(sys.modules, "torch", torch_stub)

        assert _resolve_device("auto") == "cpu"

    def test_auto_resolves_to_cpu_on_non_arm(self, monkeypatch):
        """device='auto' → 'cpu' on non-Apple-Silicon machines."""
        monkeypatch.setattr("platform.machine", lambda: "x86_64")
        # torch not needed — arm check short-circuits first
        assert _resolve_device("auto") == "cpu"

    def test_auto_resolves_to_cpu_when_torch_missing(self, monkeypatch):
        """device='auto' falls back gracefully when torch is not installed."""
        monkeypatch.setattr("platform.machine", lambda: "arm64")
        # Remove torch from sys.modules so the import raises ImportError
        monkeypatch.setitem(sys.modules, "torch", None)  # None → ImportError on import

        assert _resolve_device("auto") == "cpu"


# ---------------------------------------------------------------------------
# WhisperXBackend device initialisation
# ---------------------------------------------------------------------------

class TestWhisperXBackendDeviceInit:
    def test_default_auto_mps_on_apple_silicon(self, monkeypatch):
        """WhisperXBackend() defaults to auto and resolves to mps on Apple Silicon."""
        monkeypatch.setattr("platform.machine", lambda: "arm64")
        torch_stub = _make_torch_stub(mps_available=True)
        monkeypatch.setitem(sys.modules, "torch", torch_stub)

        backend = WhisperXBackend()
        assert backend.device == "mps"

    def test_default_auto_cpu_when_mps_unavailable(self, monkeypatch):
        """WhisperXBackend() defaults to auto and resolves to cpu when MPS unavailable."""
        monkeypatch.setattr("platform.machine", lambda: "x86_64")

        backend = WhisperXBackend()
        assert backend.device == "cpu"

    def test_explicit_cpu_device(self, monkeypatch):
        """Explicit device='cpu' is always respected regardless of platform."""
        monkeypatch.setattr("platform.machine", lambda: "arm64")
        torch_stub = _make_torch_stub(mps_available=True)
        monkeypatch.setitem(sys.modules, "torch", torch_stub)

        backend = WhisperXBackend(device="cpu")
        assert backend.device == "cpu"
