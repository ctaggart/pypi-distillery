"""Tests for version conversion in build_wheels.py."""

import importlib.util
import sys
from pathlib import Path

import pytest

# Load only the to_pep440 function without triggering top-level 'requests' import.
_spec = importlib.util.spec_from_file_location(
    "build_wheels",
    Path(__file__).resolve().parent.parent / "scripts" / "build_wheels.py",
    submodule_search_locations=[],
)
# Provide a stub for 'requests' so the module can load without the real package.
if "requests" not in sys.modules:
    import types
    sys.modules["requests"] = types.ModuleType("requests")
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
to_pep440 = _mod.to_pep440


class TestToPep440:
    """Tests for to_pep440 version conversion."""

    # Stable versions pass through unchanged
    @pytest.mark.parametrize(
        "input_version, expected",
        [
            ("1.8.11", "1.8.11"),
            ("1.8.12", "1.8.12"),
            ("2.0.0", "2.0.0"),
            ("0.1.0", "0.1.0"),
        ],
    )
    def test_stable_versions(self, input_version: str, expected: str) -> None:
        assert to_pep440(input_version) == expected

    # Custom prerelease labels become .devN
    @pytest.mark.parametrize(
        "input_version, expected",
        [
            ("1.8.13-ct.1", "1.8.13.dev1"),
            ("1.8.13-ct.2", "1.8.13.dev2"),
            ("2.0.0-foo.5", "2.0.0.dev5"),
            ("1.0.0-test.99", "1.0.0.dev99"),
        ],
    )
    def test_custom_prerelease_becomes_dev(self, input_version: str, expected: str) -> None:
        assert to_pep440(input_version) == expected

    # PEP 440 recognised labels are preserved
    @pytest.mark.parametrize(
        "input_version, expected",
        [
            ("1.8.13-a.1", "1.8.13a1"),
            ("1.8.13-alpha.2", "1.8.13alpha2"),
            ("1.8.13-b.1", "1.8.13b1"),
            ("1.8.13-beta.3", "1.8.13beta3"),
            ("1.8.13-rc.1", "1.8.13rc1"),
            ("1.8.13-preview.1", "1.8.13preview1"),
            ("1.8.13-dev.1", "1.8.13.dev1"),
        ],
    )
    def test_pep440_labels_preserved(self, input_version: str, expected: str) -> None:
        assert to_pep440(input_version) == expected

    # Invalid versions raise ValueError
    @pytest.mark.parametrize(
        "input_version",
        [
            "",
            "not-a-version",
            "v1.8.13",
            "1.8.13-",
            "1.8.13-.1",
        ],
    )
    def test_invalid_versions_raise(self, input_version: str) -> None:
        with pytest.raises(ValueError, match="Cannot parse version"):
            to_pep440(input_version)
